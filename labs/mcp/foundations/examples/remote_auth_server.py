"""阶段 12 的本地 OAuth Authorization Server。

运行：
    uv run labs/mcp/foundations/examples/remote_auth_server.py

服务默认监听 http://127.0.0.1:9000。它是教学用内存实现，不可用于生产环境。
"""

from __future__ import annotations

import time

import uvicorn
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route

from mcp.server.auth.routes import cors_middleware, create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions

from remote_auth_provider import DemoOAuthProvider


AUTH_SERVER_URL = "http://127.0.0.1:9000"
provider = DemoOAuthProvider(AUTH_SERVER_URL)


async def approve(request: Request) -> Response:
    """模拟用户在浏览器中点击“允许”。"""
    approval_id = request.query_params.get("request")
    if approval_id is None:
        return JSONResponse({"error": "missing_request"}, status_code=400)
    try:
        callback_url = await provider.approve(approval_id)
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    return RedirectResponse(callback_url, status_code=302)


async def introspect(request: Request) -> Response:
    """让 MCP Resource Server 查询 opaque token 是否仍然有效。"""
    form = await request.form()
    token = form.get("token")
    if not isinstance(token, str):
        return JSONResponse({"active": False})

    access_token = await provider.load_access_token(token)
    if access_token is None:
        return JSONResponse({"active": False})

    return JSONResponse(
        {
            "active": True,
            "client_id": access_token.client_id,
            "scope": " ".join(access_token.scopes),
            "exp": access_token.expires_at,
            "iat": int(time.time()),
            "aud": access_token.resource,
            "sub": access_token.subject,
        }
    )


routes = create_auth_routes(
    provider=provider,
    issuer_url=AnyHttpUrl(AUTH_SERVER_URL),
    client_registration_options=ClientRegistrationOptions(
        enabled=True,
        valid_scopes=["orders:read"],
        default_scopes=["orders:read"],
    ),
)
routes.extend(
    [
        Route("/approve", endpoint=approve, methods=["GET"]),
        Route(
            "/introspect",
            endpoint=cors_middleware(introspect, ["POST", "OPTIONS"]),
            methods=["POST", "OPTIONS"],
        ),
    ]
)
app = Starlette(routes=routes)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9000)

