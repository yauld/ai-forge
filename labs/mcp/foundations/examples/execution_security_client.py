"""第 10 篇实验：攻击退款 Tool 的 Server 端执行边界。

本篇不再研究 Host 是否确认。所有调用都假设已经通过 Host，专门验证：

- 对象不存在；
- 订单状态不允许；
- 金额超过自助上限；
- 同一业务意图发生重试；
- 幂等键被换绑到另一笔订单。

每次拒绝后都会读取订单最终状态，避免只根据返回文案判断安全性。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Awaitable, Callable

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


HERE = Path(__file__).resolve().parent
SERVER = HERE / "execution_security_server.py"


async def connect(stack: AsyncExitStack) -> ClientSession:
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
    print({"check": description, "passed": passed, "evidence": evidence})
    if not passed:
        raise AssertionError(f"实验检查失败：{description}")


async def call_refund(
    session: ClientSession,
    *,
    order_id: str,
    idempotency_key: str,
) -> dict[str, object]:
    """调用退款 Tool，并提取结构化业务结果。"""
    result = await session.call_tool(
        "refund_order",
        {
            "order_id": order_id,
            "reason": "customer_request",
            "idempotency_key": idempotency_key,
        },
    )
    data = result.structuredContent
    if not isinstance(data, dict):
        raise AssertionError("refund_order 没有返回结构化结果")
    return data


async def read_status(session: ClientSession, order_id: str) -> str:
    result = await session.call_tool("get_order_status", {"order_id": order_id})
    data = result.structuredContent
    if not isinstance(data, dict) or not data.get("found"):
        raise AssertionError(f"无法读取订单 {order_id}")
    order = data["order"]
    if not isinstance(order, dict):
        raise AssertionError("订单结果结构错误")
    return str(order["status"])


async def read_operation_count(session: ClientSession, order_id: str) -> int:
    """读取退款操作记录数，验证重试没有产生第二条副作用记录。"""
    result = await session.call_tool(
        "get_refund_operation_count",
        {"order_id": order_id},
    )
    data = result.structuredContent
    if not isinstance(data, dict):
        raise AssertionError("退款操作计数没有返回结构化结果")
    return int(data["operation_count"])


async def missing_order(session: ClientSession) -> None:
    """O-9999 格式合法但不存在，应返回业务拒绝而不是执行异常。"""
    result = await call_refund(
        session,
        order_id="O-9999",
        idempotency_key="refund-missing01",
    )
    check("不存在订单被拒绝", result.get("reason") == "order_not_found", result)


async def invalid_state(session: ClientSession) -> None:
    """O-1003 已取消，不满足退款必须为 paid 的前置条件。"""
    result = await call_refund(
        session,
        order_id="O-1003",
        idempotency_key="refund-state001",
    )
    check("取消订单被拒绝", result.get("reason") == "order_not_paid", result)
    status = await read_status(session, "O-1003")
    check("拒绝后仍为 cancelled", status == "cancelled", status)


async def amount_limit(session: ClientSession) -> None:
    """O-1011 金额 2699 元，超过 2000 元自助退款上限。"""
    result = await call_refund(
        session,
        order_id="O-1011",
        idempotency_key="refund-high0001",
    )
    check(
        "超额退款转人工审核",
        result.get("reason") == "manual_review_required",
        result,
    )
    status = await read_status(session, "O-1011")
    check("拒绝后仍为 paid", status == "paid", status)


async def idempotent_retry(session: ClientSession) -> None:
    """第一次退款成功；同键重试只返回旧结果，不重复执行。"""
    first = await call_refund(
        session,
        order_id="O-1001",
        idempotency_key="refund-demo0001",
    )
    retry = await call_refund(
        session,
        order_id="O-1001",
        idempotency_key="refund-demo0001",
    )
    check("首次退款成功", first.get("status") == "refunded", first)
    check("重试没有重复退款", retry.get("status") == "already_applied", retry)
    status = await read_status(session, "O-1001")
    check("最终状态为 refunded", status == "refunded", status)
    operation_count = await read_operation_count(session, "O-1001")
    check("数据库只记录一次退款操作", operation_count == 1, operation_count)


async def idempotency_conflict(session: ClientSession) -> None:
    """先绑定幂等键，再尝试把它用于另一笔订单。"""
    established = await call_refund(
        session,
        order_id="O-1004",
        idempotency_key="refund-conflict1",
    )
    check(
        "幂等键已绑定 O-1004",
        established.get("status") in {"refunded", "already_applied"},
        established,
    )
    conflict = await call_refund(
        session,
        order_id="O-1002",
        idempotency_key="refund-conflict1",
    )
    check(
        "幂等键不能换绑 O-1002",
        conflict.get("reason") == "idempotency_key_conflict",
        conflict,
    )
    status = await read_status(session, "O-1002")
    check("冲突后 O-1002 仍为 paid", status == "paid", status)


SCENARIOS: dict[str, Callable[[ClientSession], Awaitable[None]]] = {
    "refund-missing-order": missing_order,
    "refund-invalid-state": invalid_state,
    "refund-amount-limit": amount_limit,
    "refund-idempotency": idempotent_retry,
    "refund-key-conflict": idempotency_conflict,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="运行 MCP 执行安全实验")
    parser.add_argument("scenario", choices=["all", *SCENARIOS])
    args = parser.parse_args()

    async with AsyncExitStack() as stack:
        session = await connect(stack)
        names = SCENARIOS if args.scenario == "all" else [args.scenario]
        for name in names:
            print(f"\n=== {name} ===")
            await SCENARIOS[name](session)


if __name__ == "__main__":
    asyncio.run(main())
