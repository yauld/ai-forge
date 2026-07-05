"""不带授权的远程 MCP Server，用于理解最基本的 HTTP 连接方式。"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from shop_order_primitives_server import OrderFound, OrderNotFound, find_order


# Server 独立监听 8001 端口，MCP endpoint 默认是 /mcp。
mcp = FastMCP("shop-order-remote", host="127.0.0.1", port=8001)


@mcp.tool(
    annotations=ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )
)
def get_order(order_id: str) -> OrderFound | OrderNotFound:
    """按订单编号查询一笔订单。"""
    order = find_order(order_id)
    if order is None:
        return OrderNotFound(order_id=order_id, message=f"订单 {order_id} 不存在")
    return OrderFound(order=order)


if __name__ == "__main__":
    # Server 会一直运行，等待 Client 通过 http://127.0.0.1:8001/mcp 连接。
    mcp.run(transport="streamable-http")

