"""通过 Authorization Server 验证 Bearer Token 的远程 MCP Server。

运行：
    uv run labs/mcp/foundations/examples/remote_auth_resource_server.py
"""

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import AnyHttpUrl, Field

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

from shop_order_primitives_server import OrderFound, OrderNotFound, find_order


MCP_URL = "http://127.0.0.1:8001/mcp"
AUTH_SERVER_URL = "http://127.0.0.1:9000"
REQUIRED_SCOPE = "orders:read"
OrderId = Annotated[str, Field(pattern=r"^O-\d{4}$")]


class DemoTokenVerifier(TokenVerifier):
    """向演示授权服务确认 Token，而不是在本地比较固定字符串。

    get_order() 不会手动调用这个方法。FastMCP 创建 Streamable HTTP app 时，
    会把 token_verifier 接入认证中间件；每个进入 /mcp 的 Bearer Token
    都会先经过 verify_token()，通过后才进入 MCP initialize 和 tools/call。
    """

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    f"{AUTH_SERVER_URL}/introspect",
                    data={"token": token},
                )
        except httpx.HTTPError:
            return None
        if response.status_code != 200:
            return None
        token_info = response.json()
        scopes = token_info.get("scope", "").split()
        if (
            not token_info.get("active")
            or token_info.get("iss") != AUTH_SERVER_URL
            or token_info.get("aud") != MCP_URL
            or REQUIRED_SCOPE not in scopes
        ):
            return None
        return AccessToken(
            token=token,
            client_id=token_info["client_id"],
            scopes=scopes,
        )


mcp = FastMCP(
    "shop-order-remote-auth",
    host="127.0.0.1",
    port=8001,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    # FastMCP 会把这个 verifier 交给 HTTP 认证中间件：
    # Authorization: Bearer <token> -> verify_token(token) -> AccessToken | None。
    # 返回 None 时，请求会在进入 get_order() 之前被拒绝。
    token_verifier=DemoTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(AUTH_SERVER_URL),
        resource_server_url=AnyHttpUrl(MCP_URL),
        required_scopes=[REQUIRED_SCOPE],
    ),
)


@mcp.tool()
def get_order(order_id: OrderId) -> OrderFound | OrderNotFound:
    """查询一笔订单；只有通过入口认证的 Client 才能走到这里。"""
    order = find_order(order_id)
    if order is None:
        return OrderNotFound(order_id=order_id, message=f"订单 {order_id} 不存在")
    return OrderFound(order=order)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
