"""比较 Resource Template 与 Tool 的订单查询示例。

这个 Server 复用 ``shop_order_analysis_server.py`` 中的样例数据库，
但拥有独立的 MCP Server 实例，不会改变其他脚本注册的能力。

通过 MCP Inspector 启动：

    npx -y @modelcontextprotocol/inspector \
      uv run labs/mcp/foundations/examples/shop_order_primitives_server.py
"""

from __future__ import annotations

import re
import sqlite3
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import BaseModel, ConfigDict, Field

from shop_order_analysis_server import DB_PATH, ensure_database, rows_to_dicts


mcp = FastMCP("shop-order-primitives")

ORDER_ID_PATTERN = re.compile(r"^O-\d{4}$")
OrderId = Annotated[
    str,
    Field(
        pattern=r"^O-\d{4}$",
        description="订单编号，格式为 O- 加四位数字，例如 O-1001",
    ),
]
OrderStatus = Literal["paid", "cancelled", "refunded"]


class Order(BaseModel):
    """一笔订单的稳定输出契约。"""

    model_config = ConfigDict(extra="forbid")

    order_id: OrderId
    order_date: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{2}-\d{2}$",
            description="下单日期，格式为 YYYY-MM-DD",
        ),
    ]
    status: OrderStatus
    amount: Annotated[float, Field(ge=0, description="订单金额，单位为元")]
    region: str
    product: str


class OrderFound(BaseModel):
    """查询成功且订单存在。"""

    found: Literal[True] = True
    order: Order


class OrderNotFound(BaseModel):
    """查询成功但订单不存在。"""

    found: Literal[False] = False
    order_id: OrderId
    message: str


# 这两个查询 Tool 只读取本地数据库。annotations 是给 Host 的行为提示，
# 方便它判断调用风险，但不能代替真正的权限校验。
READ_ONLY_LOCAL_QUERY = ToolAnnotations(
    readOnlyHint=True,
    destructiveHint=False,
    idempotentHint=True,
    openWorldHint=False,
)


def find_order(order_id: str) -> Order | None:
    """从数据库读取一笔订单，供 Resource 和 Tool 复用。"""
    ensure_database()
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


@mcp.resource(
    "shop://orders/{order_id}",
    name="订单详情",
    description="按订单编号读取一笔可寻址的订单上下文",
    mime_type="application/json",
)
def order_detail(order_id: str) -> str:
    """读取一笔订单；具体 URI 例如 shop://orders/O-1001。"""
    # Resource Template 的 URI 变量是字符串，所以在 Server 边界再次校验。
    if not ORDER_ID_PATTERN.fullmatch(order_id):
        raise ValueError("订单编号格式错误，应为 O- 加四位数字，例如 O-1001")

    order = find_order(order_id)
    if order is None:
        raise ValueError(f"订单 {order_id} 不存在")

    return order.model_dump_json(indent=2)


@mcp.tool(annotations=READ_ONLY_LOCAL_QUERY)
def get_order(order_id: OrderId) -> OrderFound | OrderNotFound:
    """按订单编号执行一次查询，用于与订单 Resource Template 对照。"""
    order = find_order(order_id)
    if order is None:
        # 参数格式合法，但业务对象不存在：返回可供 Host 判断的业务结果。
        return OrderNotFound(
            order_id=order_id,
            message=f"订单 {order_id} 不存在",
        )
    return OrderFound(order=order)


@mcp.tool(annotations=READ_ONLY_LOCAL_QUERY)
def search_orders(
    status: OrderStatus,
    min_amount: Annotated[
        float,
        Field(ge=0, description="订单金额下限，单位为元"),
    ] = 0,
    limit: Annotated[
        int,
        Field(ge=1, le=20, description="最多返回多少笔订单"),
    ] = 5,
) -> list[Order]:
    """按状态和金额筛选订单，展示为什么动态搜索更适合 Tool。"""
    ensure_database()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT order_id, order_date, status, amount, region, product
            FROM orders
            WHERE status = ? AND amount >= ?
            ORDER BY amount DESC, order_id
            LIMIT ?
            """,
            (status, min_amount, limit),
        )
        return [Order.model_validate(row) for row in rows_to_dicts(cursor)]


@mcp.prompt()
def analyze_one_order(order_id: str = "O-1001") -> str:
    """生成分析单笔订单的任务模板。"""
    return f"""请分析订单 {order_id}。

如果 Host 已经提供 `shop://orders/{order_id}` 的内容，直接基于该上下文分析；
否则调用 `get_order` 查询订单。

输出订单状态、金额、区域、商品，以及值得关注的信息。
不要编造查询结果中不存在的数据。
"""


def main() -> None:
    """通过 stdio 启动这个 MCP Server。"""
    ensure_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
