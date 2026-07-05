"""阶段 12 的受保护远程 MCP Resource Server。

运行：
    uv run labs/mcp/foundations/examples/remote_auth_resource_server.py

Server 使用 Streamable HTTP，在 http://127.0.0.1:8001/mcp 暴露 MCP endpoint。
"""

from __future__ import annotations

from typing import Annotated

import httpx
from pydantic import AnyHttpUrl, Field

from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from shop_order_primitives_server import OrderFound, OrderNotFound, find_order


RESOURCE_SERVER_URL = "http://127.0.0.1:8001/mcp"
AUTH_SERVER_URL = "http://127.0.0.1:9000"
OrderId = Annotated[
    str,
    Field(pattern=r"^O-\d{4}$", description="订单编号，例如 O-1001"),
]


class IntrospectionTokenVerifier(TokenVerifier):
    """通过授权服务的 introspection endpoint 验证 opaque token。"""

    async def verify_token(self, token: str) -> AccessToken | None:
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.post(
                    f"{AUTH_SERVER_URL}/introspect",
                    data={"token": token},
                )
                response.raise_for_status()
            except httpx.HTTPError:
                return None

        data = response.json()
        if not data.get("active"):
            return None
        return AccessToken(
            token=token,
            client_id=data["client_id"],
            scopes=data.get("scope", "").split(),
            expires_at=data.get("exp"),
            resource=data.get("aud"),
            subject=data.get("sub"),
        )


mcp = FastMCP(
    "shop-order-remote-auth",
    host="127.0.0.1",
    port=8001,
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
    token_verifier=IntrospectionTokenVerifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(AUTH_SERVER_URL),
        resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
        required_scopes=["orders:read"],
    ),
)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def get_order(order_id: OrderId) -> OrderFound | OrderNotFound:
    """查询一笔订单；只有通过远程授权的 Client 才能调用。"""
    order = find_order(order_id)
    if order is None:
        return OrderNotFound(order_id=order_id, message=f"订单 {order_id} 不存在")
    return OrderFound(order=order)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

