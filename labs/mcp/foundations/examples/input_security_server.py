"""第 08 篇实验：MCP Tool 输入安全 Server。

本实验只研究一个问题：调用者传给 Tool 的参数和 Tool 返回的数据，
怎样被限制在明确范围内。

Server 提供一个只读订单查询 Tool：

- status 只能是 paid、cancelled、refunded；
- limit 只能是 1～10；
- SQL 结构固定，调用者不能传入 SQL；
- 返回值只包含客服查询需要的四个字段。

Server 还提供两个只服务实验观察的辅助 Tool：

- get_query_execution_count：证明非法输入没有进入查询函数；
- count_orders_for_status_text：隔离验证 SQL 参数绑定。

配套 Client：``input_security_client.py``。
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


mcp = FastMCP("shop-order-input-security")

OrderStatus = Literal["paid", "cancelled", "refunded"]

# 只统计 search_orders_for_support 真正进入函数体的次数。
# 参数若在 FastMCP schema 校验阶段失败，这个数字不会增加。
QUERY_EXECUTION_COUNT = 0

READ_ONLY_QUERY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


@mcp.tool(annotations=READ_ONLY_QUERY)
def search_orders_for_support(
    status: OrderStatus,
    limit: Annotated[
        int,
        Field(ge=1, le=10, description="最多返回 10 笔订单"),
    ] = 5,
) -> list[dict[str, object]]:
    """按订单状态查询客服需要的最小字段。

    Tool 不接受任意 SQL、字段名或排序表达式。status 和 limit 是调用者
    唯一能控制的内容，并且会先经过 FastMCP 生成的 input schema 校验。
    """
    global QUERY_EXECUTION_COUNT
    QUERY_EXECUTION_COUNT += 1

    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT order_id, status, amount, product
            FROM orders
            WHERE status = ?
            ORDER BY order_id
            LIMIT ?
            """,
            (status, limit),
        )
        return rows_to_dicts(cursor)


@mcp.tool(annotations=READ_ONLY_QUERY)
def get_query_execution_count() -> dict[str, int]:
    """返回主查询 Tool 进入函数体的次数，仅用于观察 schema 是否提前拦截。"""
    return {"execution_count": QUERY_EXECUTION_COUNT}


@mcp.tool(annotations=READ_ONLY_QUERY)
def count_orders_for_status_text(
    status_text: Annotated[
        str,
        Field(min_length=1, max_length=50, description="用于参数绑定对照的状态文本"),
    ],
) -> dict[str, object]:
    """用自由文本状态演示参数绑定不会改变 SQL 结构。

    正式查询仍应使用枚举。这个对照 Tool 刻意允许普通字符串进入 SQL 参数，
    用来单独验证 ``paid' OR 1=1 --`` 只会被当作一个值。
    """
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        matching_count = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE status = ?",
            (status_text,),
        ).fetchone()[0]
        total_count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]

    return {
        "submitted_status": status_text,
        "matching_count": matching_count,
        "total_order_count": total_count,
    }


def main() -> None:
    """初始化样例数据库并通过 stdio 启动 MCP Server。"""
    reset_security_orders()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
