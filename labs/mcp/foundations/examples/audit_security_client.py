"""第 12 篇实验：验证 MCP 审计的可调查性与敏感信息最小化。"""

from __future__ import annotations

import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


HERE = Path(__file__).resolve().parent
SERVER = HERE / "audit_security_server.py"


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


async def main() -> None:
    applied_key = "refund-audit0001"
    denied_key = "refund-audit0002"

    async with AsyncExitStack() as stack:
        session = await connect(stack)

        applied = await session.call_tool(
            "refund_order",
            {
                "order_id": "O-1005",
                "reason": "duplicate",
                "idempotency_key": applied_key,
            },
        )
        denied = await session.call_tool(
            "refund_order",
            {
                "order_id": "O-9999",
                "reason": "customer_request",
                "idempotency_key": denied_key,
            },
        )
        check(
            "合法退款成功，非法对象被拒绝",
            applied.structuredContent.get("status") == "refunded"
            and denied.structuredContent.get("status") == "denied",
            {
                "applied": applied.structuredContent,
                "denied": denied.structuredContent,
            },
        )

        audit_result = await session.call_tool("list_security_audit", {})
        audit_data = audit_result.structuredContent
        serialized_audit = str(audit_data)
        check(
            "审计同时保留 applied 与 denied",
            "applied" in serialized_audit and "denied" in serialized_audit,
            audit_data,
        )
        check(
            "审计没有保存原始幂等键",
            applied_key not in serialized_audit and denied_key not in serialized_audit,
            audit_data,
        )
        check(
            "审计保留可关联的幂等键短指纹",
            serialized_audit.count("idempotency_fingerprint") == 2,
            audit_data,
        )

        status_result = await session.call_tool(
            "get_order_status",
            {"order_id": "O-1005"},
        )
        check(
            "成功审计对应的订单最终为 refunded",
            status_result.structuredContent.get("status") == "refunded",
            status_result.structuredContent,
        )


if __name__ == "__main__":
    asyncio.run(main())
