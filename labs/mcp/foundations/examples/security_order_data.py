"""本地安全系列实验共用的独立订单数据。

这个文件只负责两件事：

1. 定义安全实验使用的 SQLite 路径；
2. 每次 Server 启动时把订单恢复到同一组初始状态。

它不包含 MCP Tool、安全策略或实验场景。把数据初始化集中在这里，是为了
避免四篇实验重复大段建表代码，同时保证它们不会修改前序实验使用的
``shop_orders.sqlite``。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from shop_order_analysis_server import SAMPLE_ORDERS


DATA_DIR = Path(__file__).with_name("data")
SECURITY_DB_PATH = DATA_DIR / "shop_order_security.sqlite"


def reset_security_orders() -> None:
    """删除旧实验状态，并写入固定的样例订单。"""
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS audit_events;
            DROP TABLE IF EXISTS refund_operations;
            DROP TABLE IF EXISTS support_notes;
            DROP TABLE IF EXISTS orders;

            CREATE TABLE orders (
                order_id TEXT PRIMARY KEY,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                amount REAL NOT NULL,
                region TEXT NOT NULL,
                product TEXT NOT NULL
            );
            """
        )
        conn.executemany(
            """
            INSERT INTO orders
                (order_id, order_date, status, amount, region, product)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_ORDERS,
        )


def rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict[str, object]]:
    """把 SQLite 查询结果转换成容易阅读和返回的字典列表。"""
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
