"""第 11 篇实验：Prompt injection 防护与审计脱敏。

本实验只研究两件事：

1. Tool 返回的恶意备注能否绕过 Host 的危险操作确认；
2. Server 的审计是否既能证明操作发生，又不泄露原始幂等键。
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
SERVER = HERE / "content_security_server.py"


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


async def read_order(session: ClientSession, order_id: str) -> dict[str, object]:
    result = await session.call_tool("get_order_with_note", {"order_id": order_id})
    data = result.structuredContent
    if not isinstance(data, dict):
        raise AssertionError("订单 Tool 没有返回结构化结果")
    return data


async def read_refund_execution_count(session: ClientSession) -> int:
    """读取退款 Tool 执行次数，证明 Host 拦截后没有调用 Server 退款函数。"""
    result = await session.call_tool("get_refund_execution_count", {})
    data = result.structuredContent
    if not isinstance(data, dict):
        raise AssertionError("退款执行计数没有返回结构化结果")
    return int(data["execution_count"])


async def injection(session: ClientSession) -> None:
    """模拟模型服从恶意备注提出退款，但 Host 没有用户确认。"""
    source_order = await read_order(session, "O-1002")
    trust = source_order.get("content_trust")
    check(
        "订单备注被标记为不可信内容",
        isinstance(trust, dict)
        and trust.get("note") == "untrusted_external_content",
        source_order,
    )

    # 下面的字典模拟模型受到备注诱导后生成的 Tool 调用。
    model_proposed_arguments = {
        "order_id": "O-1007",
        "reason": "customer_request",
        "idempotency_key": "refund-inject01",
    }
    user_confirmed = False
    count_before = await read_refund_execution_count(session)

    # Host 不因为指令来自 Tool 结果就降低确认要求。
    if not user_confirmed:
        host_decision = {
            "host_status": "blocked_before_call",
            "reason": "explicit_user_confirmation_required",
            "proposed_arguments": model_proposed_arguments,
        }
    else:
        raise AssertionError("本场景不应该进入已确认分支")

    check(
        "注入诱导的退款在调用前被阻止",
        host_decision["host_status"] == "blocked_before_call",
        host_decision,
    )
    count_after = await read_refund_execution_count(session)
    check(
        "refund_order 没有进入函数体",
        count_after == count_before,
        {"before": count_before, "after": count_after},
    )

    target_order = await read_order(session, "O-1007")
    target = target_order.get("order")
    check(
        "攻击目标订单仍为 paid",
        isinstance(target, dict) and target.get("status") == "paid",
        target_order,
    )


async def audit_redaction(session: ClientSession) -> None:
    """执行一笔合法退款，检查审计证据和敏感字段。"""
    original_key = "refund-audit0001"
    refund_result = await session.call_tool(
        "refund_order",
        {
            "order_id": "O-1005",
            "reason": "duplicate",
            "idempotency_key": original_key,
        },
    )
    check(
        "退款执行成功",
        refund_result.isError is False,
        {
            "isError": refund_result.isError,
            "structuredContent": refund_result.structuredContent,
        },
    )

    audit_result = await session.call_tool("list_security_audit", {})
    audit_data = audit_result.structuredContent
    serialized_audit = str(audit_data)
    check("审计记录包含 applied", "applied" in serialized_audit, audit_data)
    check("审计没有原始幂等键", original_key not in serialized_audit, audit_data)
    check(
        "审计保留幂等键短指纹",
        "idempotency_fingerprint" in serialized_audit,
        audit_data,
    )


SCENARIOS: dict[str, Callable[[ClientSession], Awaitable[None]]] = {
    "injection": injection,
    "audit-redaction": audit_redaction,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="运行 MCP 内容安全实验")
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
