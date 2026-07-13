"""阶段 11 最小 MCP Server：提供订单查询工具和一个无关工具。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=logging.WARNING, force=True)

HERE = Path(__file__).resolve().parent
ORDERS_PATH = HERE / "data" / "orders.json"

mcp = FastMCP("stage11-order-report")


def _load_orders() -> dict[str, dict[str, object]]:
    return json.loads(ORDERS_PATH.read_text(encoding="utf-8"))


@mcp.tool()
def get_order(order_id: str) -> dict[str, object]:
    """根据订单号查询订单状态、金额和商品名称。"""

    order = _load_orders().get(order_id)
    if order is None:
        return {
            "found": False,
            "order_id": order_id,
        }
    return {
        "found": True,
        "order": order,
    }


@mcp.tool()
def get_shipping_policy(region: str = "CN") -> dict[str, object]:
    """查询指定地区的通用物流政策，不返回具体订单状态。"""

    return {
        "region": region,
        "policy": "标准物流通常 3-5 个工作日送达，偏远地区可能延迟。",
        "scope": "shipping_policy",
    }


if __name__ == "__main__":
    mcp.run()
