"""第 11 篇实验：可调查且不泄密的 MCP 审计 Server。"""

from __future__ import annotations

import hashlib
import json
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


mcp = FastMCP("shop-order-audit-security")

OrderId = Annotated[str, Field(pattern=r"^O-\d{4}$")]
IdempotencyKey = Annotated[str, Field(pattern=r"^refund-[A-Za-z0-9]{8,32}$")]

READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)
DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False,
    destructiveHint=True,
    idempotentHint=True,
    openWorldHint=False,
)


def prepare_database() -> None:
    """重置订单，并创建退款操作与审计表。"""
    reset_security_orders()
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.executescript(
            """
            CREATE TABLE refund_operations (
                idempotency_digest TEXT PRIMARY KEY,
                order_id TEXT NOT NULL
            );
            CREATE TABLE audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                order_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            """
        )


def record_audit(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    outcome: str,
    detail: dict[str, object],
) -> None:
    """在当前业务事务中写入一条最小化退款审计记录。

    复用调用方传入的连接，可以让订单状态、幂等记录和审计事件一起提交；
    任一步骤失败时，它们也会一起回滚，避免业务结果与审计记录不一致。
    ``detail`` 只应包含事后调查所需的脱敏字段，不能放入完整请求或原始幂等键。
    """
    conn.execute(
        """
        INSERT INTO audit_events
            (created_at, action, order_id, outcome, detail)
        VALUES (?, 'refund', ?, ?, ?)
        """,
        (
            # 使用带 UTC 时区的 ISO 8601 时间，便于跨系统排序和关联事件。
            datetime.now(UTC).isoformat(timespec="seconds"),
            order_id,
            outcome,
            # detail 以 JSON 保存，以便按不同结果记录不同字段；固定键顺序让
            # 测试、日志对比和人工检查得到稳定、可读的序列化结果。
            json.dumps(detail, ensure_ascii=False, sort_keys=True),
        ),
    )


@mcp.tool(annotations=DESTRUCTIVE)
def refund_order(
    order_id: OrderId,
    reason: Literal["duplicate", "customer_request"],
    idempotency_key: IdempotencyKey,
) -> dict[str, object]:
    """执行幂等退款，并为成功或拒绝结果写入最小化审计记录。

    同一个幂等键只会产生一次退款结果。数据库保存键的完整摘要用于精确判重，
    对外响应和审计记录只暴露摘要前缀，既能关联一次调用，又不会泄露原始键。
    """
    # 原始幂等键相当于调用凭据，不应直接写入数据库或审计日志。完整 SHA-256
    # 摘要用于判重；它是固定长度值，也避免原始键出现在后续查询和排障过程中。
    digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
    # 短指纹只用于人工关联响应与审计事件，不承担唯一性或安全校验职责。
    fingerprint = digest[:12]

    # 连接上下文构成事务边界：正常离开（包括函数从 with 内 return）会提交，
    # 抛出异常则回滚。因此退款状态、幂等记录和审计事件不会只写入其中一部分。
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        # 首先检查幂等记录，防止客户端重试时再次执行退款。
        # 重复调用直接返回第一次操作关联的订单，不重复修改订单，也不制造重复审计事件。
        previous = conn.execute(
            "SELECT order_id FROM refund_operations WHERE idempotency_digest = ?",
            (digest,),
        ).fetchone()
        if previous is not None:
            return {"status": "already_applied", "order_id": previous[0]}

        # 只读取退款判断和审计所需字段，避免把无关订单信息带入处理流程。
        order = conn.execute(
            "SELECT status, amount FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        # 不存在的订单和非 paid 订单都使用同一拒绝原因，既简化调用方处理，
        # 也避免通过错误差异探测订单是否存在或处于何种具体状态。
        if order is None or order[0] != "paid":
            record_audit(
                conn,
                order_id=order_id,
                outcome="denied",
                detail={
                    "reason": "order_not_refundable",
                    "idempotency_fingerprint": fingerprint,
                },
            )
            return {"status": "denied", "reason": "order_not_refundable"}

        # 先落业务结果，再登记幂等摘要，最后记录审计事件；
        # 三步共享当前事务。
        # 幂等表的摘要主键还会阻止同一摘要被重复插入。
        conn.execute(
            "UPDATE orders SET status = 'refunded' WHERE order_id = ?",
            (order_id,),
        )
        conn.execute(
            "INSERT INTO refund_operations VALUES (?, ?)",
            (digest, order_id),
        )
        record_audit(
            conn,
            order_id=order_id,
            outcome="applied",
            detail={
                "amount": float(order[1]),
                "reason": reason,
                "idempotency_fingerprint": fingerprint,
            },
        )
    # 只有事务成功提交后才向调用方报告退款完成。
    return {
        "status": "refunded",
        "order_id": order_id,
        "idempotency_fingerprint": fingerprint,
    }


@mcp.tool(annotations=READ_ONLY)
def get_order_status(order_id: OrderId) -> dict[str, object]:
    """读取订单最终状态，用于验证审计事件对应的业务结果。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        row = conn.execute(
            "SELECT order_id, status FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
    if row is None:
        return {"found": False, "order_id": order_id}
    return {"found": True, "order_id": row[0], "status": row[1]}


@mcp.tool(annotations=READ_ONLY)
def list_security_audit() -> list[dict[str, object]]:
    """返回脱敏后的退款审计记录。"""
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT created_at, action, order_id, outcome, detail
            FROM audit_events
            ORDER BY event_id
            """
        )
        return rows_to_dicts(cursor)


def main() -> None:
    prepare_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
