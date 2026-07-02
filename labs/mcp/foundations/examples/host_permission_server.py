"""第 09 篇实验：供 Host 权限与用户确认实验连接的 MCP Server。

Server 只提供两项能力：

- ``get_order_for_support``：读取订单当前状态；
- ``refund_order``：把已支付订单改为已退款。

本篇重点不在复杂退款规则，而在请求到达 Server 之前，Host 是否允许
MCP Client 发送 ``tools/call``。复杂业务执行边界放在独立实验中。
"""

from __future__ import annotations

import sqlite3
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from security_order_data import (
    SECURITY_DB_PATH,
    reset_security_orders,
    rows_to_dicts,
)


mcp = FastMCP("shop-order-host-permission")

OrderId = Annotated[
    str,
    Field(pattern=r"^O-\d{4}$", description="订单编号，例如 O-1001"),
]

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=False,
    openWorldHint=False,
)


@mcp.tool(annotations=READ_ONLY)
def get_order_for_support(order_id: OrderId) -> dict[str, object]:
    """读取单笔订单状态，用于验证退款是否真正发生。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT order_id, status, amount, product FROM orders WHERE order_id = ?",
            (order_id,),
        )
        rows = rows_to_dicts(cursor)
    if not rows:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order": rows[0]}


@mcp.tool(annotations=DESTRUCTIVE)
def refund_order(
    order_id: OrderId,
    reason: Literal["duplicate", "not_received", "customer_request"],
) -> dict[str, object]:
    """执行最小退款动作；只有 Host 放行后，调用才应该到达这里。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        order = conn.execute(
            "SELECT status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order is None:
            return {"status": "denied", "reason": "order_not_found"}
        if order[0] != "paid":
            return {"status": "denied", "reason": "order_not_paid"}
        conn.execute(
            "UPDATE orders SET status = 'refunded' WHERE order_id = ?",
            (order_id,),
        )
    return {"status": "refunded", "order_id": order_id, "reason": reason}


def main() -> None:
    """重置样例订单后启动 Server，保证每次实验结果一致。"""
    reset_security_orders()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
