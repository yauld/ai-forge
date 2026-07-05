"""阶段 12 的 OAuth MCP Client。

运行前先启动 remote_auth_server.py 和 remote_auth_resource_server.py，然后执行：
    uv run labs/mcp/foundations/examples/remote_auth_client.py
"""

from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urljoin, urlparse

import httpx
from pydantic import AnyUrl

from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


MCP_URL = "http://127.0.0.1:8001/mcp"
CALLBACK_URL = "http://127.0.0.1:3030/callback"


class InMemoryTokenStorage(TokenStorage):
    """保存本次运行取得的客户端注册信息和 token。"""

    def __init__(self) -> None:
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info


async def observe_unauthorized_request() -> None:
    """先不带 token 请求 MCP endpoint，保留授权发现的第一段证据。"""
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(MCP_URL, json={})
        challenge = response.headers.get("www-authenticate")
        print(f"1. no token -> HTTP {response.status_code}")
        print(f"   WWW-Authenticate: {challenge}")

        if challenge is None or "resource_metadata=" not in challenge:
            raise AssertionError("401 响应没有提供 resource_metadata")

        metadata_url = challenge.split('resource_metadata="', 1)[1].split('"', 1)[0]
        metadata = (await http_client.get(metadata_url)).json()
        print(f"2. protected resource: {metadata['resource']}")
        print(f"   authorization servers: {metadata['authorization_servers']}")


def create_automated_user_agent() -> tuple:
    """返回 OAuthClientProvider 需要的重定向与回调处理器。

    正常桌面 Client 会打开浏览器让用户登录和确认。本实验用 HTTP 请求自动访问
    本地批准页，再把 callback 中的 code 和 state 交还给 SDK。
    """
    callback_queue: asyncio.Queue[tuple[str, str | None]] = asyncio.Queue(maxsize=1)

    async def handle_redirect(authorization_url: str) -> None:
        print("3. authorization request includes PKCE and resource")
        parsed_authorization = urlparse(authorization_url)
        authorization_query = parse_qs(parsed_authorization.query)
        assert authorization_query["code_challenge_method"] == ["S256"]
        assert authorization_query["resource"] == [MCP_URL]

        async with httpx.AsyncClient(follow_redirects=False) as client:
            authorize_response = await client.get(authorization_url)
            approval_url = urljoin(authorization_url, authorize_response.headers["location"])
            approval_response = await client.get(approval_url)
            callback_url = approval_response.headers["location"]

        callback_query = parse_qs(urlparse(callback_url).query)
        await callback_queue.put(
            (
                callback_query["code"][0],
                callback_query.get("state", [None])[0],
            )
        )

    async def handle_callback() -> tuple[str, str | None]:
        return await callback_queue.get()

    return handle_redirect, handle_callback


async def run() -> None:
    await observe_unauthorized_request()

    storage = InMemoryTokenStorage()
    redirect_handler, callback_handler = create_automated_user_agent()
    oauth = OAuthClientProvider(
        server_url=MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name="AI Forge Stage 12 Client",
            redirect_uris=[AnyUrl(CALLBACK_URL)],
            # SDK 的动态注册端点要求同时声明 refresh_token；本阶段只执行
            # authorization_code，Provider 不会实际签发 refresh token。
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="orders:read",
        ),
        storage=storage,
        redirect_handler=redirect_handler,
        callback_handler=callback_handler,
    )

    async with httpx.AsyncClient(auth=oauth, follow_redirects=True) as http_client:
        async with streamable_http_client(MCP_URL, http_client=http_client) as (read, write, _):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                result = await session.call_tool("get_order", {"order_id": "O-1001"})

    if storage.tokens is None:
        raise AssertionError("OAuth 流程结束后没有保存 access token")
    if result.isError:
        raise AssertionError("携带 access token 的 Tool 调用不应失败")

    print(f"4. access token: {storage.tokens.access_token[:12]}... (redacted)")
    print(f"5. protocol: {initialized.protocolVersion}")
    print(f"   protected tool result: {result.structuredContent}")


if __name__ == "__main__":
    asyncio.run(run())
