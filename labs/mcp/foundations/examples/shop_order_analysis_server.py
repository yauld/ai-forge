# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp[cli]>=1.2.0,<2",
# ]
# ///
"""电商订单分析 MCP Server 示例。

这个文件用一个真实但足够小的业务场景，帮助理解
Resources、Prompts、Tools 如何一起协作。

通过 MCP Inspector 启动：

    npx -y @modelcontextprotocol/inspector \
      uv run --no-sync --script labs/mcp/foundations/examples/shop_order_analysis_server.py
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Literal

from mcp.server.fastmcp import FastMCP


# FastMCP 是 Python SDK 提供的便捷封装。
# 这里的名字会作为 Server 名称出现在 Inspector 的连接信息里。
mcp = FastMCP("shop-order-analysis")

# 这个实验用本地 SQLite 文件模拟“外部订单数据库”。
# 真实业务里，这一层可以替换成 MySQL、PostgreSQL、业务 API 等。
DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "shop_orders.sqlite"


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


def ensure_database() -> None:
    """初始化样例订单数据库。

    为了让实验可重复，每次启动 Server 都会重新写入同一批样例数据。
    这样你在 Inspector 里多次运行 tool，得到的结果是稳定的。
    """
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                amount REAL NOT NULL,
                region TEXT NOT NULL,
                product TEXT NOT NULL
            )
            """
        )

        # 清空旧数据再写入样例数据，避免上次实验结果影响这次学习。
        conn.execute("DELETE FROM orders")
        conn.executemany(
            """
            INSERT INTO orders
                (order_id, order_date, status, amount, region, product)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_ORDERS,
        )


def parse_date(value: str) -> str:
    """校验日期字符串，避免 tool 收到格式错误的参数。"""
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("日期必须使用 YYYY-MM-DD 格式，例如 2026-06-25") from exc
    return value


def rows_to_dicts(cursor: sqlite3.Cursor) -> list[dict[str, object]]:
    """把 SQLite 查询结果转换成更适合 MCP 返回的字典列表。"""
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


@mcp.resource("shop://database/schema")
def database_schema() -> str:
    """读取订单数据库的表结构和字段含义。"""
    return """# 订单数据库 Schema

这个 resource 模拟 MCP Server 暴露给 AI 应用的数据库上下文。

表名：orders

| 字段 | 含义 |
| --- | --- |
| order_id | 订单编号 |
| order_date | 下单日期，格式为 YYYY-MM-DD |
| status | 订单状态：paid 已支付，cancelled 已取消，refunded 已退款 |
| amount | 订单金额，单位：元 |
| region | 用户所在区域 |
| product | 商品名称 |

这个 resource 只提供上下文，不执行查询，也不改变数据库。
"""


@mcp.resource("shop://business/metrics")
def business_metrics() -> str:
    """读取订单分析里的业务指标口径。"""
    return """# 订单分析指标口径

这个 resource 模拟业务团队提前定义好的指标说明。

- 订单数：指定日期范围内的订单总数。
- 成交额：status = paid 的订单金额总和。
- 已支付订单数：status = paid 的订单数量。
- 取消订单数：status = cancelled 的订单数量。
- 退款订单数：status = refunded 的订单数量。
- 客单价：成交额 / 已支付订单数。

分析订单时，AI 应先理解这些口径，再决定是否调用查询工具。
"""


@mcp.tool()
def query_daily_order_summary(start_date: str, end_date: str) -> dict[str, object]:
    """按日期查询订单数、成交额、取消数和退款数。"""
    # tool 的入参来自 Host/Client，因此即使是学习实验也要做基本校验。
    start = parse_date(start_date)
    end = parse_date(end_date)
    ensure_database()

    # 这里是真正“执行动作”的地方：
    # MCP Server 代表 Host 去查询外部系统，也就是本例中的 SQLite 订单库。
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT
                order_date,
                COUNT(*) AS order_count,
                SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) AS paid_amount,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_count,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
                SUM(CASE WHEN status = 'refunded' THEN 1 ELSE 0 END) AS refunded_count
            FROM orders
            WHERE order_date BETWEEN ? AND ?
            GROUP BY order_date
            ORDER BY order_date
            """,
            (start, end),
        )
        rows = rows_to_dicts(cursor)

    # 汇总指标用于模拟真实日报里常见的“总成交额、支付订单数、客单价”。
    total_paid_amount = sum(float(row["paid_amount"] or 0) for row in rows)
    total_paid_count = sum(int(row["paid_count"] or 0) for row in rows)
    avg_order_value = (
        round(total_paid_amount / total_paid_count, 2) if total_paid_count else 0
    )

    # FastMCP 会把这个 Python dict 转成 MCP tool result。
    # 在 Inspector 里，你会同时看到结构化结果和文本化结果。
    return {
        "date_range": f"{start} 到 {end}",
        "daily_rows": rows,
        "summary": {
            "paid_amount": round(total_paid_amount, 2),
            "paid_count": total_paid_count,
            "cancelled_count": sum(int(row["cancelled_count"] or 0) for row in rows),
            "refunded_count": sum(int(row["refunded_count"] or 0) for row in rows),
            "avg_order_value": avg_order_value,
        },
    }


@mcp.tool()
def list_orders_by_status(
    status: Literal["paid", "cancelled", "refunded"],
    limit: int = 5,
) -> list[dict[str, object]]:
    """按订单状态查看明细，用于排查取消或退款订单。"""
    ensure_database()

    # 限制返回条数，模拟真实工具里常见的安全边界，避免一次返回过多数据。
    safe_limit = max(1, min(limit, 20))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT order_id, order_date, status, amount, region, product
            FROM orders
            WHERE status = ?
            ORDER BY order_date DESC, order_id DESC
            LIMIT ?
            """,
            (status, safe_limit),
        )
        return rows_to_dicts(cursor)


@mcp.prompt()
def daily_order_analysis_report(date_range: str = "2026-06-19 到 2026-06-25") -> str:
    """生成一份订单日报分析提示词模板。"""
    return f"""你是一名电商数据分析助手，请分析 {date_range} 的订单表现。

请按下面步骤完成：

1. 先读取 `shop://database/schema`，理解 orders 表字段。
2. 再读取 `shop://business/metrics`，理解订单数、成交额、取消数、退款数、客单价的计算口径。
3. 调用 `query_daily_order_summary` 查询日期范围内的每日汇总。
4. 如果取消或退款明显偏高，再调用 `list_orders_by_status` 查看明细。
5. 最后用中文输出一份简短日报：
   - 核心结论
   - 关键数据
   - 异常点
   - 建议下一步排查方向

注意：不要编造数据库里没有的数据。
"""


def main() -> None:
    """启动 MCP Server。

    Inspector 通过 stdio transport 和这个进程通信。
    """
    ensure_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
