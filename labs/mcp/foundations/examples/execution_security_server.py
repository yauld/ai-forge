"""第 10 篇实验：退款 Tool 的 Server 端执行边界。

本实验假设 Host 已经完成用户确认，请求已经到达 MCP Server。研究重点是：
Server 仍然必须根据业务对象、订单状态、金额和幂等键决定是否执行。

配套 Client：``execution_security_client.py``。
"""

from __future__ import annotations

import hashlib
import sqlite3
from datetime import UTC, datetime
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from security_order_data import (
    SECURITY_DB_PATH,
    reset_security_orders,
    rows_to_dicts,
)


mcp = FastMCP("shop-order-execution-security")
MAX_SELF_SERVICE_REFUND = 2_000.0

OrderId = Annotated[
    str,
    Field(pattern=r"^O-\d{4}$", description="订单编号，例如 O-1001"),
]
IdempotencyKey = Annotated[
    str,
    Field(
        pattern=r"^refund-[A-Za-z0-9]{8,32}$",
        description="一次退款业务意图使用的稳定幂等键",
    ),
]
RefundReason = Literal["duplicate", "not_received", "customer_request"]

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
IDEMPOTENT_REFUND = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def idempotency_digest(key: str) -> str:
    """用完整 SHA-256 摘要执行唯一约束，不在数据库保存原始键。"""
    return hashlib.sha256(key.encode()).hexdigest()


def prepare_database() -> None:
    """重置订单，并创建本篇实验需要的幂等记录表。"""
    reset_security_orders()
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE refund_operations (
                idempotency_digest TEXT PRIMARY KEY,
                order_id TEXT NOT NULL,
                amount REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


@mcp.tool(annotations=READ_ONLY)
def get_order_status(order_id: OrderId) -> dict[str, object]:
    """读取订单最终状态，作为副作用是否发生的证据。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        cursor = conn.execute(
            "SELECT order_id, status, amount FROM orders WHERE order_id = ?",
            (order_id,),
        )
        rows = rows_to_dicts(cursor)
    if not rows:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order": rows[0]}


@mcp.tool(annotations=READ_ONLY)
def get_refund_operation_count(order_id: OrderId) -> dict[str, object]:
    """返回指定订单写入了多少条退款操作记录，作为幂等性的直接证据。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM refund_operations WHERE order_id = ?",
            (order_id,),
        ).fetchone()[0]
    return {"order_id": order_id, "operation_count": count}


@mcp.tool(annotations=IDEMPOTENT_REFUND)
def refund_order(
    order_id: OrderId,
    reason: RefundReason,
    idempotency_key: IdempotencyKey,
) -> dict[str, object]:
    """按“幂等 → 对象 → 状态 → 金额”顺序检查后执行退款。"""
    digest = idempotency_digest(idempotency_key)
    visible_fingerprint = digest[:12]

    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # 第一道执行边界：相同幂等键只能代表同一笔订单。
        previous = conn.execute(
            """
            SELECT order_id, amount
            FROM refund_operations
            WHERE idempotency_digest = ?
            """,
            (digest,),
        ).fetchone()
        if previous is not None:
            if previous["order_id"] != order_id:
                return {
                    "status": "denied",
                    "reason": "idempotency_key_conflict",
                    "order_id": order_id,
                }
            return {
                "status": "already_applied",
                "order_id": order_id,
                "amount": previous["amount"],
                "idempotency_fingerprint": visible_fingerprint,
            }

        # 第二道执行边界：格式合法的订单编号也可能不存在。
        order = conn.execute(
            "SELECT status, amount FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order is None:
            return {
                "status": "denied",
                "reason": "order_not_found",
                "order_id": order_id,
            }

        # 第三道执行边界：只有 paid 订单允许进入退款。
        if order["status"] != "paid":
            return {
                "status": "denied",
                "reason": "order_not_paid",
                "order_id": order_id,
                "current_status": order["status"],
            }

        # 第四道执行边界：高金额订单必须进入人工审核。
        amount = float(order["amount"])
        if amount > MAX_SELF_SERVICE_REFUND:
            return {
                "status": "denied",
                "reason": "manual_review_required",
                "order_id": order_id,
                "policy_limit": MAX_SELF_SERVICE_REFUND,
            }

        conn.execute(
            "UPDATE orders SET status = 'refunded' WHERE order_id = ?",
            (order_id,),
        )
        conn.execute(
            """
            INSERT INTO refund_operations
                (idempotency_digest, order_id, amount, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (digest, order_id, amount, utc_now()),
        )

    return {
        "status": "refunded",
        "order_id": order_id,
        "reason": reason,
        "amount": amount,
        "idempotency_fingerprint": visible_fingerprint,
    }


def main() -> None:
    prepare_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
