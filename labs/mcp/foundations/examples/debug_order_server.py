"""阶段 7：用于制造 Tool 调用故障的订单 MCP Server。

这个 Server 只服务调试实验。正常业务能力仍然放在已有的
``shop_order_primitives_server.py`` 中。
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from shop_order_analysis_server import DB_PATH, rows_to_dicts
from shop_order_primitives_server import Order


mcp = FastMCP("shop-order-debug")

OrderId = Annotated[
    str,
    Field(
        pattern=r"^O-\d{4}$",
        description="订单编号，格式为 O- 加四位数字，例如 O-1001",
    ),
]


def find_order_without_refresh(order_id: str) -> Order | None:
    """读取现有样例数据库，不在调试实验中刷新仓库数据文件。"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT order_id, order_date, status, amount, region, product
            FROM orders
            WHERE order_id = ?
            """,
            (order_id,),
        )
        rows = rows_to_dicts(cursor)
    return Order.model_validate(rows[0]) if rows else None


@mcp.tool()
def get_order_with_contract_bug(order_id: OrderId) -> dict[str, str]:
    """故意让实现违反 input schema，用来定位契约与实现不一致。"""
    # input schema 明确允许 O-1001，但实现却错误地把整个编号转成整数。
    # 合法输入会通过 schema 校验，然后在 Tool 实现内部失败。
    numeric_order_id = int(order_id)
    return {"numeric_order_id": str(numeric_order_id)}


@mcp.tool()
async def diagnose_order(
    order_id: OrderId,
    delay_seconds: Annotated[
        float,
        Field(ge=0, le=5, description="模拟数据库查询耗时，单位为秒"),
    ] = 0,
) -> dict[str, object]:
    """模拟订单查询，覆盖成功、不存在和 Host 超时三条路径。"""
    await asyncio.sleep(delay_seconds)
    order = find_order_without_refresh(order_id)

    if order is None:
        # 查询正常完成但对象不存在，不应伪装成协议故障。
        return {
            "status": "not_found",
            "order_id": order_id,
            "message": "订单不存在",
        }

    return {
        "status": "found",
        "order": order.model_dump(),
    }


@mcp.tool()
def simulate_database_failure(
    failure: Literal["connection", "query"],
) -> dict[str, str]:
    """模拟 Tool 执行期间的基础设施异常。"""
    if failure == "connection":
        raise ConnectionError("模拟数据库连接失败")
    raise RuntimeError("模拟数据库查询失败")


def main() -> None:
    """通过 stdio 启动调试 Server。"""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
