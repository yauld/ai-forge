"""Sec for AI 安全实验共用的独立订单数据。

这个文件只负责两件事：

1. 定义安全实验使用的 SQLite 路径；
2. 每次 Server 启动时把订单恢复到同一组初始状态。

它不包含 MCP Tool、安全策略或实验场景。把数据初始化集中在这里，是为了
让间接 Prompt Injection 实验可以独立复现，并且不会修改其它专题使用的
``shop_orders.sqlite``。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


DATA_DIR = Path(__file__).with_name("data")
SECURITY_DB_PATH = DATA_DIR / "shop_order_security.sqlite"


# 样例订单数据。每一行对应 orders 表的一条订单记录：
# order_id, order_date, status, amount, region, product。
SAMPLE_ORDERS = [
    ("O-1001", "2026-06-19", "paid", 199.0, "华东", "耳机"),
    ("O-1002", "2026-06-19", "paid", 88.0, "华南", "数据线"),
    ("O-1003", "2026-06-20", "cancelled", 299.0, "华北", "键盘"),
    ("O-1004", "2026-06-20", "paid", 699.0, "华东", "显示器"),
    ("O-1005", "2026-06-21", "paid", 129.0, "西南", "鼠标"),
    ("O-1006", "2026-06-21", "refunded", 399.0, "华南", "机械键盘"),
    ("O-1007", "2026-06-22", "paid", 1599.0, "华东", "手机"),
    ("O-1008", "2026-06-22", "paid", 59.0, "华北", "手机壳"),
    ("O-1009", "2026-06-23", "cancelled", 799.0, "西北", "平板"),
    ("O-1010", "2026-06-23", "paid", 1099.0, "华南", "手表"),
    ("O-1011", "2026-06-24", "paid", 2699.0, "华东", "笔记本电脑"),
    ("O-1012", "2026-06-24", "paid", 39.0, "华中", "贴膜"),
    ("O-1013", "2026-06-25", "paid", 499.0, "华北", "路由器"),
    ("O-1014", "2026-06-25", "refunded", 1299.0, "华东", "相机"),
]


def reset_security_orders() -> None:
    """删除旧实验状态，并写入固定的样例订单。"""
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(SECURITY_DB_PATH) as conn:
        conn.executescript(
            """
            DROP TABLE IF EXISTS audit_events;
            DROP TABLE IF EXISTS refund_operations;
            DROP TABLE IF EXISTS support_requests;
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
