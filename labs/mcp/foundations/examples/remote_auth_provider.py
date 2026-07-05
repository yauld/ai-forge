"""阶段 12 使用的最小 OAuth 授权服务状态。

这个实现只用于本地教学：所有状态都保存在内存中，并用自动批准页面代替真实的
登录和同意界面。OAuth 路由、PKCE 校验和动态客户端注册仍由 MCP Python SDK
提供，避免在实验里重新实现协议处理器。
"""

from __future__ import annotations

import secrets
import time
from urllib.parse import urlencode

from pydantic import AnyHttpUrl

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken


class DemoOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """保存动态注册客户端、授权码和 access token 的内存 Provider。"""

    def __init__(self, issuer_url: str) -> None:
        self.issuer_url = issuer_url.rstrip("/")
        self.clients: dict[str, OAuthClientInformationFull] = {}
        self.authorization_requests: dict[str, tuple[OAuthClientInformationFull, AuthorizationParams]] = {}
        self.authorization_codes: dict[str, AuthorizationCode] = {}
        self.access_tokens: dict[str, AccessToken] = {}

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self.clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        if client_info.client_id is None:
            raise ValueError("动态注册结果缺少 client_id")
        self.clients[client_info.client_id] = client_info

    async def authorize(
        self,
        client: OAuthClientInformationFull,
        params: AuthorizationParams,
    ) -> str:
        """暂存授权请求，并把用户代理引向本地批准页面。"""
        approval_id = secrets.token_urlsafe(24)
        self.authorization_requests[approval_id] = (client, params)
        return f"{self.issuer_url}/approve?{urlencode({'request': approval_id})}"

    async def approve(self, approval_id: str) -> str:
        """模拟用户批准，并返回携带授权码的 Client callback URL。"""
        pending = self.authorization_requests.pop(approval_id, None)
        if pending is None:
            raise ValueError("授权请求不存在或已经使用")

        client, params = pending
        if client.client_id is None:
            raise ValueError("授权请求缺少 client_id")

        code_value = f"code_{secrets.token_urlsafe(24)}"
        scopes = params.scopes or ["orders:read"]
        code = AuthorizationCode(
            code=code_value,
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            expires_at=time.time() + 300,
            scopes=scopes,
            code_challenge=params.code_challenge,
            resource=params.resource,
            subject="demo-user",
        )
        self.authorization_codes[code_value] = code

        query = {"code": code_value}
        if params.state is not None:
            query["state"] = params.state
        return f"{params.redirect_uri}?{urlencode(query)}"

    async def load_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: str,
    ) -> AuthorizationCode | None:
        code = self.authorization_codes.get(authorization_code)
        if code is None or code.client_id != client.client_id or code.expires_at < time.time():
            return None
        return code

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        """PKCE 通过 SDK 校验后，签发一个小时有效的 opaque token。"""
        stored_code = self.authorization_codes.pop(authorization_code.code, None)
        if stored_code is None or client.client_id is None:
            raise ValueError("授权码无效或已经使用")

        token_value = f"token_{secrets.token_urlsafe(32)}"
        access_token = AccessToken(
            token=token_value,
            client_id=client.client_id,
            scopes=stored_code.scopes,
            expires_at=int(time.time()) + 3600,
            resource=stored_code.resource,
            subject=stored_code.subject,
        )
        self.access_tokens[token_value] = access_token
        return OAuthToken(
            access_token=token_value,
            token_type="Bearer",
            expires_in=3600,
            scope=" ".join(stored_code.scopes),
        )

    async def load_access_token(self, token: str) -> AccessToken | None:
        access_token = self.access_tokens.get(token)
        if access_token is None:
            return None
        if access_token.expires_at is not None and access_token.expires_at < time.time():
            self.access_tokens.pop(token, None)
            return None
        return access_token

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> RefreshToken | None:
        return None

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        raise NotImplementedError("阶段 12 不演示 refresh token")

    async def revoke_token(self, token: str, token_type_hint: str | None = None) -> None:
        self.access_tokens.pop(token, None)

