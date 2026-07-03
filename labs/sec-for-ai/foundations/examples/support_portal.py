"""模拟面向客户的售后问题提交入口。

这个模块代表 MCP Server 之外的普通业务系统。外部客户提交的自由文本会先通过
这个入口写入数据库，之后订单支持 Agent 才可能通过 MCP Tool 读取它。
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from security_order_data import SECURITY_DB_PATH


def submit_support_request(order_id: str, request_text: str) -> dict[str, str]:
    """模拟客户通过公开售后表单提交问题描述。"""
    submitted_at = datetime.now(UTC).isoformat(timespec="seconds")
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        order_exists = conn.execute(
            "SELECT 1 FROM orders WHERE order_id = ?",
            (order_id,),
        ).fetchone()
        if order_exists is None:
            raise ValueError(f"订单不存在：{order_id}")
        conn.execute(
            """
            INSERT INTO support_requests
                (order_id, request_text, submission_source, submitted_at)
            VALUES (?, ?, 'customer_support_form', ?)
            """,
            (order_id, request_text, submitted_at),
        )
    return {
        "order_id": order_id,
        "submission_source": "customer_support_form",
        "submitted_at": submitted_at,
    }
