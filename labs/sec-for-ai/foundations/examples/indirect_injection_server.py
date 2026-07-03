"""第 01 篇实验：间接 Prompt injection MCP Server。

Server 读取由外部售后入口写入的客户问题描述。退款 Tool 只用于验证模型受诱导后，
Host 放行时是否会产生真实副作用，以及关闭确认后能否在调用前拦截。
"""

from __future__ import annotations

import sqlite3
import logging
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from security_order_data import (
    SECURITY_DB_PATH,
    reset_security_orders,
)


mcp = FastMCP("shop-order-indirect-injection")

logging.basicConfig(level=logging.WARNING, force=True)

# 只统计 refund_order 真正进入函数体的次数，用于区分“模型提出退款”
# 与“Server 退款函数真的被调用”。
REFUND_EXECUTION_COUNT = 0

OrderId = Annotated[str, Field(pattern=r"^O-\d{4}$")]

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


def prepare_database() -> None:
    """重置订单并创建空的售后工单表，等待外部业务入口写入。"""
    reset_security_orders()
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE support_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT NOT NULL,
                request_text TEXT NOT NULL,
                submission_source TEXT NOT NULL,
                submitted_at TEXT NOT NULL
            );
            """
        )


@mcp.tool(annotations=READ_ONLY)
def get_order_with_support_request(order_id: OrderId) -> dict[str, object]:
    """读取订单和客户提交的售后问题描述。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        order = conn.execute(
            """
            SELECT order_id, status, amount, product
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()
        if order is None:
            return {"found": False, "order_id": order_id}

        # 本实验只提交一条售后内容；分开查询比 JOIN 子查询更贴近教学主线：
        # 订单数据和外部客户文本被 MCP Tool 一起返回给 Host。
        support_request = conn.execute(
            """
            SELECT request_text, submission_source, submitted_at
            FROM support_requests
            WHERE order_id = ?
            """,
            (order_id,),
        ).fetchone()

    result: dict[str, object] = {
        "order_id": order[0],
        "status": order[1],
        "amount": order[2],
        "product": order[3],
        "support_request": None,
        "submission_source": None,
        "request_submitted_at": None,
    }
    if support_request is not None:
        result.update(
            {
                "support_request": support_request[0],
                "submission_source": support_request[1],
                "request_submitted_at": support_request[2],
            }
        )
    return {"found": True, "order": result}


@mcp.tool(annotations=DESTRUCTIVE)
def refund_order(
    order_id: OrderId,
    reason: Literal["duplicate", "customer_request"],
) -> dict[str, object]:
    """执行退款；正常情况下必须先经过 Host 的用户确认。"""
    global REFUND_EXECUTION_COUNT
    REFUND_EXECUTION_COUNT += 1

    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        order = conn.execute(
            "SELECT status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order is None or order[0] != "paid":
            return {"status": "denied", "reason": "order_not_refundable"}

        conn.execute(
            "UPDATE orders SET status = 'refunded' WHERE order_id = ?",
            (order_id,),
        )
    return {
        "status": "refunded",
        "order_id": order_id,
        "reason": reason,
    }


@mcp.tool(annotations=READ_ONLY)
def get_refund_execution_count() -> dict[str, int]:
    """返回退款 Tool 进入函数体的次数，只用于实验观察。"""
    return {"execution_count": REFUND_EXECUTION_COUNT}


def main() -> None:
    prepare_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
