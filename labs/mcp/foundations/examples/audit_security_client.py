"""第 11 篇实验：验证 MCP 审计的可调查性与敏感信息最小化。"""

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
    """运行审计安全实验，并逐项验证业务结果与审计证据。

    实验故意提交一次可执行的退款和一次应被拒绝的退款，然后检查审计记录是否
    同时满足可调查性与数据最小化要求，最后回查订单状态以确认日志与业务结果一致。
    """
    # 两次调用使用不同的原始幂等键，便于分别验证成功和拒绝事件。后续还会直接
    # 搜索这两个值，确保 Server 没有把原始键写入审计记录。
    applied_key = "refund-audit0001"
    denied_key = "refund-audit0002"

    # AsyncExitStack 统一管理 stdio 连接和 ClientSession 的异步生命周期。
    # 离开代码块时，即使中途断言失败，也会按相反顺序关闭会话并终止 Server。
    async with AsyncExitStack() as stack:
        # connect() 会启动 audit_security_server.py、完成 MCP 初始化并返回
        # 可用于调用 Tool 的会话；Server 启动时也会重建本实验的 SQLite 数据库。
        session = await connect(stack)

        # O-1005 是初始数据中的已支付订单，应当完成退款并产生 applied 审计事件。
        applied = await session.call_tool(
            "refund_order",
            {
                "order_id": "O-1005",
                "reason": "duplicate",
                "idempotency_key": applied_key,
            },
        )
        # O-9999 不存在，应被统一拒绝并产生 denied 审计事件。使用不存在的订单
        # 还能验证拒绝结果不会泄露更多订单状态信息。
        denied = await session.call_tool(
            "refund_order",
            {
                "order_id": "O-9999",
                "reason": "customer_request",
                "idempotency_key": denied_key,
            },
        )
        # 先验证两个业务分支确实按预期执行，否则后续审计检查将失去前提。
        # evidence 同时输出两个 Tool 响应，便于失败时定位是哪一个分支异常。
        check(
            "合法退款成功，非法对象被拒绝",
            applied.structuredContent.get("status") == "refunded" # type: ignore
            and denied.structuredContent.get("status") == "denied", # type: ignore
            {
                "applied": applied.structuredContent,
                "denied": denied.structuredContent,
            },
        )

        # 一次性读取 Server 暴露的脱敏审计数据。这里检查的是客户端实际可见的
        # Tool 返回值，而不是绕过 MCP 直接查询数据库。
        audit_result = await session.call_tool("list_security_audit", {})
        audit_data = audit_result.structuredContent
        # 将嵌套结构转成字符串，足以完成本实验的包含性检查：结果类型、敏感原值
        # 和短指纹字段无论位于哪条审计记录中，都能被统一搜索。
        serialized_audit = str(audit_data)
        # 成功操作和失败尝试都必须留下证据；只记录其中一类会造成调查盲区。
        check(
            "审计同时保留 applied 与 denied",
            "applied" in serialized_audit and "denied" in serialized_audit,
            audit_data,
        )
        # 原始幂等键具有凭据属性，审计中只能保存其不可逆摘要产生的短指纹。
        check(
            "审计没有保存原始幂等键",
            applied_key not in serialized_audit and denied_key not in serialized_audit,
            audit_data,
        )
        # 两次退款尝试都应各自保留一个短指纹，供响应、审计事件和排障信息关联；
        # 该指纹仅用于关联，不应被当作唯一标识或认证凭据。
        check(
            "审计保留可关联的幂等键短指纹",
            serialized_audit.count("idempotency_fingerprint") == 2,
            audit_data,
        )

        # 审计记录声称 applied 还不够，需要回查真实业务状态，确认订单确实退款。
        status_result = await session.call_tool(
            "get_order_status",
            {"order_id": "O-1005"},
        )
        # 这一断言把“审计证据”与“数据库中的最终业务结果”对应起来，避免只有
        # 成功日志、却没有实际完成状态变更的假阳性。
        check(
            "成功审计对应的订单最终为 refunded",
            status_result.structuredContent.get("status") == "refunded", # type: ignore
            status_result.structuredContent,
        )


if __name__ == "__main__":
    asyncio.run(main())
