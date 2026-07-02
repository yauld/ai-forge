"""第 08 篇实验：主动攻击订单查询 Tool 的输入边界。

实验问题：

1. 合法边界值 ``limit=10`` 能否正常工作？
2. status 传入枚举外内容会发生什么？
3. limit 传入 0 或 10000 会发生什么？
4. 查询结果是否只暴露允许的字段？
5. 如果自由文本真的进入 SQL 参数，注入式文本会不会改变 SQL 结构？

每个场景都会执行明确断言。若 SDK 或 Server 意外接受危险输入，
脚本会抛出 AssertionError，而不是只打印一段容易被忽略的输出。

运行全部场景：

    uv run labs/mcp/foundations/examples/input_security_client.py all
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any, Awaitable, Callable

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


HERE = Path(__file__).resolve().parent
SERVER = HERE / "input_security_server.py"


async def connect(stack: AsyncExitStack) -> ClientSession:
    """启动输入安全 Server，建立 stdio 连接并完成初始化。"""
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=HERE,
    )
    read, write = await stack.enter_async_context(stdio_client(parameters))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


def check(description: str, passed: bool, evidence: object) -> None:
    """打印实验检查结果；检查失败时立即终止。"""
    print({"check": description, "passed": passed, "evidence": evidence})
    if not passed:
        raise AssertionError(f"实验检查失败：{description}")


def error_text(result: Any) -> str:
    """把 Tool 参数校验错误整理成一段便于检查的文字。"""
    return "\n".join(str(getattr(item, "text", item)) for item in result.content)


async def read_query_execution_count(session: ClientSession) -> int:
    """读取主查询函数实际执行次数，给“没有进入 Tool”提供直接证据。"""
    result = await session.call_tool("get_query_execution_count", {})
    data = result.structuredContent
    if not isinstance(data, dict):
        raise AssertionError("执行计数 Tool 没有返回结构化结果")
    return int(data["execution_count"])


async def allowed_query(session: ClientSession) -> None:
    """使用合法 status 和最大允许 limit，建立成功基线。"""
    # limit=10 是允许范围的上边界。边界测试不能只测常用值 5，
    # 还要证明最大合法值能够成功。
    call_result = await session.call_tool(
        "search_orders_for_support",
        {"status": "paid", "limit": 10},
    )
    check(
        "合法查询没有返回 Tool 错误",
        call_result.isError is False,
        {"isError": call_result.isError},
    )

    # 返回类型是 list 时，FastMCP 将列表包装在 structuredContent["result"]。
    structured_result = call_result.structuredContent
    check(
        "Tool 返回结构化对象",
        isinstance(structured_result, dict),
        {"type": type(structured_result).__name__},
    )
    if not isinstance(structured_result, dict):
        return

    orders = structured_result.get("result")
    check(
        "结构化结果中包含订单列表",
        isinstance(orders, list),
        {"type": type(orders).__name__},
    )
    if not isinstance(orders, list):
        return

    check("返回订单不超过 10 笔", len(orders) <= 10, {"count": len(orders)})

    # 数据最小化不仅限制条数，也限制每条记录能暴露哪些字段。
    allowed_fields = {"order_id", "status", "amount", "product"}
    invalid_order = None
    for order in orders:
        if not isinstance(order, dict) or set(order) != allowed_fields:
            invalid_order = order
            break
    check(
        "所有订单都只包含允许字段",
        invalid_order is None,
        {
            "allowed_fields": sorted(allowed_fields),
            "invalid_order": invalid_order,
        },
    )


async def invalid_status_query(session: ClientSession) -> None:
    """提交普通非法状态和 SQL 注入式文本，验证枚举边界。"""
    hostile_status_values = [
        "pending",
        "paid' OR 1=1 --",
    ]

    for hostile_status in hostile_status_values:
        count_before = await read_query_execution_count(session)
        call_result = await session.call_tool(
            "search_orders_for_support",
            {"status": hostile_status, "limit": 5},
        )
        count_after = await read_query_execution_count(session)
        validation_error = error_text(call_result)
        check(
            f"拒绝非法 status={hostile_status!r}",
            call_result.isError is True and "literal_error" in validation_error,
            validation_error,
        )
        check(
            "非法 status 没有进入查询函数",
            count_after == count_before,
            {"before": count_before, "after": count_after},
        )


async def extreme_limit_query(session: ClientSession) -> None:
    """分别攻击 limit 的下界和上界。"""
    hostile_limits = [
        (0, "greater_than_equal"),
        (10_000, "less_than_equal"),
    ]

    for hostile_limit, expected_error in hostile_limits:
        count_before = await read_query_execution_count(session)
        call_result = await session.call_tool(
            "search_orders_for_support",
            {"status": "paid", "limit": hostile_limit},
        )
        count_after = await read_query_execution_count(session)
        validation_error = error_text(call_result)
        check(
            f"拒绝 limit={hostile_limit}",
            call_result.isError is True and expected_error in validation_error,
            validation_error,
        )
        check(
            "越界 limit 没有进入查询函数",
            count_after == count_before,
            {"before": count_before, "after": count_after},
        )


async def parameterized_sql_query(session: ClientSession) -> None:
    """让注入式文本进入 SQL 参数，证明它只被当作普通值。"""
    injection_text = "paid' OR 1=1 --"

    injection_result = await session.call_tool(
        "count_orders_for_status_text",
        {"status_text": injection_text},
    )
    injection_data = injection_result.structuredContent
    check("参数绑定对照返回结构化结果", isinstance(injection_data, dict), injection_data)
    if not isinstance(injection_data, dict):
        return
    check(
        "注入式文本没有匹配全部订单",
        injection_data.get("matching_count") == 0,
        injection_data,
    )
    check(
        "orders 表仍保留 14 笔样例数据",
        injection_data.get("total_order_count") == 14,
        injection_data,
    )

    # 再用正常值查询，证明对照 Tool 和数据库仍能正常工作。
    paid_result = await session.call_tool(
        "count_orders_for_status_text",
        {"status_text": "paid"},
    )
    paid_data = paid_result.structuredContent
    check(
        "正常 paid 状态仍能匹配订单",
        isinstance(paid_data, dict) and int(paid_data["matching_count"]) > 0,
        paid_data,
    )


SCENARIOS: dict[str, Callable[[ClientSession], Awaitable[None]]] = {
    "query-allowed": allowed_query,
    "query-invalid-status": invalid_status_query,
    "query-extreme-limit": extreme_limit_query,
    "query-parameter-binding": parameterized_sql_query,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="运行 MCP 输入安全实验")
    parser.add_argument("scenario", choices=["all", *SCENARIOS])
    args = parser.parse_args()

    async with AsyncExitStack() as stack:
        session = await connect(stack)
        scenario_names = SCENARIOS if args.scenario == "all" else [args.scenario]
        for scenario_name in scenario_names:
            print(f"\n=== {scenario_name} ===")
            await SCENARIOS[scenario_name](session)


if __name__ == "__main__":
    asyncio.run(main())
