"""最小 OAuth 风格授权服务：登录、同意、签发授权码和 access token。

运行：
    uv run labs/mcp/foundations/examples/remote_auth_server.py
"""

from __future__ import annotations

from secrets import token_urlsafe
from time import time
from typing import Annotated

import uvicorn
from fastapi import FastAPI, Form, HTTPException
from pydantic import BaseModel


CLIENT_ACCESS_KEY = "ai-forge-demo-client"
CLIENT_SECRET_KEY = "ai-forge-demo-secret"
DEMO_USER = "reader@example.com"
DEMO_PASSWORD = "letmein"
ISSUER_URL = "http://127.0.0.1:9000"
MCP_RESOURCE = "http://127.0.0.1:8001/mcp"
SCOPE = "orders:read"
CODE_TTL_SECONDS = 60
TOKEN_TTL_SECONDS = 300

app = FastAPI(title="AI Forge Demo Authorization Server")
# 教学版把授权码和 Token 放在内存里，方便读者观察完整流程。
# 真实系统应使用数据库或专门的授权服务存储，并支持撤销、刷新和审计。
authorization_codes: dict[str, dict[str, object]] = {}
access_tokens: dict[str, dict[str, object]] = {}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = TOKEN_TTL_SECONDS
    scope: str = SCOPE


class IntrospectionResponse(BaseModel):
    active: bool
    client_id: str | None = None
    username: str | None = None
    scope: str | None = None
    aud: str | None = None
    iss: str | None = None
    exp: int | None = None


def _require_demo_client(client_id: str, client_secret: str | None = None) -> None:
    """确认请求来自这个实验注册过的 OAuth Client。"""
    # /authorize 阶段只需要识别 client_id；/token 阶段还要校验 client_secret。
    # 在很多开放平台里，它们对应 AccessKey 和 SecretKey 这一组应用身份凭据。
    if client_id != CLIENT_ACCESS_KEY:
        raise HTTPException(status_code=400, detail="unknown_client")
    if client_secret is not None and client_secret != CLIENT_SECRET_KEY:
        raise HTTPException(status_code=401, detail="invalid_client")


@app.get("/authorize")
def authorization_hint(
    client_id: str,
    redirect_uri: str,
    scope: str,
    state: str = "demo-state",
) -> dict[str, str]:
    """返回教学用登录提示；真实系统通常在这里渲染登录和授权页面。"""
    _require_demo_client(client_id)
    if scope != SCOPE:
        raise HTTPException(status_code=400, detail="unsupported_scope")
    # 真实 OAuth 中，/authorize 通常是“浏览器打开的授权页”。
    # 本实验为了避免引入页面，只返回提示信息；client 随后会把演示用户的
    # 登录和同意结果提交到 /authorize/approve，模拟用户点击“同意”。
    return {
        "message": "用演示账号登录并同意授权后，POST /authorize/approve 会返回授权码。",
        "demo_user": DEMO_USER,
        "requested_scope": scope,
        "redirect_uri": redirect_uri,
        "state": state,
    }


@app.post("/authorize/approve")
def approve_authorization(
    client_id: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    scope: Annotated[str, Form()],
    state: Annotated[str, Form()],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    consent: Annotated[str, Form(pattern=r"^yes$")],
) -> dict[str, str]:
    """验证用户登录和授权同意，签发一次性 authorization code。"""
    _require_demo_client(client_id)
    if scope != SCOPE:
        raise HTTPException(status_code=400, detail="unsupported_scope")
    if username != DEMO_USER or password != DEMO_PASSWORD:
        raise HTTPException(status_code=401, detail="invalid_user")
    if consent != "yes":
        raise HTTPException(status_code=403, detail="consent_required")

    # 授权码代表“用户刚刚同意过”，但它还不是 access token。
    # 它被绑定到 client、redirect_uri、用户和 scope，并且很快过期。
    # Client 后面必须拿这个 code 去 /token，才能换到真正访问 MCP Server 的凭据。
    code = token_urlsafe(24)
    authorization_codes[code] = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "username": username,
        "scope": scope,
        "expires_at": time() + CODE_TTL_SECONDS,
    }
    print("1===>",authorization_codes)
    return {
        "redirect_to": f"{redirect_uri}?code={code}&state={state}",
        "code": code,
        "state": state,
    }


@app.post("/token")
def exchange_token(
    grant_type: Annotated[str, Form()],
    code: Annotated[str, Form()],
    redirect_uri: Annotated[str, Form()],
    client_id: Annotated[str, Form()],
    client_secret: Annotated[str, Form()],
) -> TokenResponse:
    """把一次性 authorization code 换成短期 access token。"""
    if grant_type != "authorization_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
    _require_demo_client(client_id, client_secret)

    # /token 是“换票”环节：Authorization Server 再次确认 code、redirect_uri
    # 和 Client 身份都匹配，才签发 access token。
    # pop 让授权码只能使用一次；重复提交同一个 code 会得到 invalid_code。
    code_record = authorization_codes.pop(code, None)
    print("2===>",authorization_codes)
    print("3===>",code_record)
    if code_record is None:
        raise HTTPException(status_code=400, detail="invalid_code")
    if code_record["expires_at"] < time(): # type: ignore
        raise HTTPException(status_code=400, detail="expired_code")
    if code_record["client_id"] != client_id or code_record["redirect_uri"] != redirect_uri:
        raise HTTPException(status_code=400, detail="invalid_grant")

    # access token 才是 Resource Server 接受的 Bearer 凭据。这里存下 issuer、
    # audience 和 scope，后续 /introspect 会把这些信息交给 MCP Server 校验。
    access_token = token_urlsafe(32)
    access_tokens[access_token] = {
        "client_id": client_id,
        "username": code_record["username"],
        "scope": code_record["scope"],
        "aud": MCP_RESOURCE,
        "iss": ISSUER_URL,
        "expires_at": time() + TOKEN_TTL_SECONDS,
    }
    print("4===>",access_tokens)
    return TokenResponse(access_token=access_token)


@app.post("/introspect")
def introspect_token(token: Annotated[str, Form()]) -> IntrospectionResponse:
    """Resource Server 用这个端点确认 token 是否仍然有效。"""
    # Resource Server 不直接共享本进程里的 token 数据；它只通过这个端点询问
    # “这个 token 还活着吗，它是谁签发的、给谁用、有什么 scope”。
    token_record = access_tokens.get(token)
    if token_record is None or token_record["expires_at"] < time(): # type: ignore
        return IntrospectionResponse(active=False)
    return IntrospectionResponse(
        active=True,
        client_id=str(token_record["client_id"]),
        username=str(token_record["username"]),
        scope=str(token_record["scope"]),
        aud=str(token_record["aud"]),
        iss=str(token_record["iss"]),
        exp=int(token_record["expires_at"]), # type: ignore
    )


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)
