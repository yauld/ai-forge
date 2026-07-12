"""阶段 10 最小 MCP Server：只提供一个订单查询 Tool。"""

from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.WARNING, force=True)

mcp = FastMCP("stage10-order-query")


ORDERS: dict[str, dict[str, object]] = {
    "O-1001": {
        "order_id": "O-1001",
        "status": "paid",
        "amount": 199,
        "currency": "CNY",
        "product": "耳机",
    },
    "O-1002": {
        "order_id": "O-1002",
        "status": "paid",
        "amount": 88,
        "currency": "CNY",
        "product": "数据线",
    },
}


@mcp.tool()
def get_order(order_id: str) -> dict[str, object]:
    """根据订单号查询订单状态、金额和商品名称。"""
    order = ORDERS.get(order_id)
    if order is None:
        return {
            "found": False,
            "order_id": order_id,
        }
    return {
        "found": True,
        "order": order,
    }


if __name__ == "__main__":
    mcp.run()
