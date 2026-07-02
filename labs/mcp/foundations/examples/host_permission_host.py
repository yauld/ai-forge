"""第 09 篇实验：Host 如何控制 Tool 权限与危险操作确认。

本实验直接用字典模拟模型提出的 Tool 调用，不接入真实模型。这样可以清楚
观察下面的边界：

模型提出调用 → Host 检查白名单和参数 → Host 检查用户确认
→ MCP Client 决定是否发送 tools/call → MCP Server 执行 Tool

实验场景：

- discovery：发现 Tool 和风险 annotations；
- unknown-tool：Host 拒绝未审核 Tool，请求不发送给 Server；
- refund-unconfirmed：模型参数合法，但用户未确认；
- refund-forged-confirmation：模型伪造确认字段，Host 仍然拒绝。
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
SERVER = HERE / "host_permission_server.py"

# 这是 Host 自己审核后的 Tool 策略，不依赖 Server 的 annotations 自动放行。
HOST_TOOL_POLICY = {
    "get_order_for_support": "allow",
    "refund_order": "require_confirmation",
}

# 模型只能提供 Tool 契约中声明的参数。多出来的控制字段默认拒绝。
HOST_TOOL_ARGUMENTS = {
    "get_order_for_support": {"order_id"},
    "refund_order": {"order_id", "reason"},
}


async def connect(stack: AsyncExitStack) -> ClientSession:
    """启动 Server，建立 MCP ClientSession 并完成初始化。"""
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
    """打印检查结果；未满足预期时让实验立即失败。"""
    print({"check": description, "passed": passed, "evidence": evidence})
    if not passed:
        raise AssertionError(f"实验检查失败：{description}")


async def host_decides_whether_to_call(
    session: ClientSession,
    tool_name: str,
    model_proposed_arguments: dict[str, object],
    *,
    user_confirmed: bool,
) -> dict[str, object]:
    """Host 在 MCP Client 发送请求前执行三项明确检查。"""
    # 检查 1：Tool 是否经过 Host 审核。
    policy = HOST_TOOL_POLICY.get(tool_name)
    if policy is None:
        return {
            "host_status": "blocked_before_call",
            "tool": tool_name,
            "reason": "tool_not_allowed_by_host_policy",
        }

    # 检查 2：模型是否偷偷加入 Tool 契约外的参数。
    allowed_argument_names = HOST_TOOL_ARGUMENTS[tool_name]
    proposed_argument_names = set(model_proposed_arguments)
    unexpected_argument_names = sorted(
        proposed_argument_names - allowed_argument_names
    )
    if unexpected_argument_names:
        return {
            "host_status": "blocked_before_call",
            "tool": tool_name,
            "reason": "unexpected_tool_arguments",
            "unexpected_arguments": unexpected_argument_names,
        }

    # 检查 3：危险 Tool 是否已经得到用户明确确认。
    if policy == "require_confirmation" and not user_confirmed:
        return {
            "host_status": "blocked_before_call",
            "tool": tool_name,
            "reason": "explicit_user_confirmation_required",
            "proposed_arguments": model_proposed_arguments,
        }

    # 只有三项检查全部通过，MCP Client 才真正向 Server 发送 tools/call。
    tool_result = await session.call_tool(tool_name, model_proposed_arguments)
    return {
        "host_status": "called",
        "tool": tool_name,
        "result": tool_result.structuredContent or tool_result.content,
    }


async def read_order_status(session: ClientSession, order_id: str) -> str:
    """回查数据库中的真实状态，证明危险操作是否发生。"""
    result = await session.call_tool(
        "get_order_for_support",
        {"order_id": order_id},
    )
    data = result.structuredContent
    if not isinstance(data, dict) or not data.get("found"):
        raise AssertionError(f"无法读取订单 {order_id}")
    order = data["order"]
    if not isinstance(order, dict):
        raise AssertionError(f"订单 {order_id} 返回结构错误")
    return str(order["status"])


async def discovery(session: ClientSession) -> None:
    """列出 Tool，并单独检查退款 Tool 的风险 annotations。"""
    response = await session.list_tools()
    tools = response.tools
    tool_names = [tool.name for tool in tools]
    print({"discovered_tools": tool_names})

    for expected_name in HOST_TOOL_POLICY:
        check(f"能够发现 {expected_name}", expected_name in tool_names, tool_names)

    refund_tool = None
    for tool in tools:
        if tool.name == "refund_order":
            refund_tool = tool
            break
    check("找到 refund_order", refund_tool is not None, tool_names)
    if refund_tool is None:
        return

    annotations = refund_tool.annotations
    check("refund_order 提供 annotations", annotations is not None, annotations)
    if annotations is None:
        return
    check("refund_order 不是只读 Tool", annotations.readOnlyHint is False, annotations)
    check("refund_order 有破坏性", annotations.destructiveHint is True, annotations)


async def unknown_tool(session: ClientSession) -> None:
    """模型提出未审核 Tool，Host 在发送请求前直接拒绝。"""
    model_proposed_tool = "export_all_orders"
    host_decision = await host_decides_whether_to_call(
        session,
        model_proposed_tool,
        {},
        user_confirmed=True,
    )
    check(
        "未知 Tool 被 Host 拒绝",
        host_decision.get("reason") == "tool_not_allowed_by_host_policy",
        host_decision,
    )


async def unconfirmed_refund(session: ClientSession) -> None:
    """模拟模型提出合法退款，但用户尚未确认。"""
    # 真实应用中，这个字典来自模型 tool call；实验直接构造模型输出。
    model_proposed_arguments: dict[str, object] = {
        "order_id": "O-1001",
        "reason": "duplicate",
    }

    # False 是 Host 界面的真实确认状态，不是模型参数。
    host_decision = await host_decides_whether_to_call(
        session,
        "refund_order",
        model_proposed_arguments,
        user_confirmed=False,
    )
    check(
        "未确认退款在 tools/call 前被阻止",
        host_decision.get("reason") == "explicit_user_confirmation_required",
        host_decision,
    )

    current_status = await read_order_status(session, "O-1001")
    check("订单没有被退款", current_status == "paid", current_status)


async def forged_confirmation(session: ClientSession) -> None:
    """模型把 user_confirmed=true 塞进参数，Host 拒绝未知字段。"""
    model_proposed_arguments: dict[str, object] = {
        "order_id": "O-1002",
        "reason": "customer_request",
        "user_confirmed": True,
    }
    host_decision = await host_decides_whether_to_call(
        session,
        "refund_order",
        model_proposed_arguments,
        # 即使界面真的确认了，模型也不能擅自扩展 Tool 参数。
        user_confirmed=True,
    )
    check(
        "伪造确认字段被拒绝",
        host_decision.get("reason") == "unexpected_tool_arguments",
        host_decision,
    )
    current_status = await read_order_status(session, "O-1002")
    check("订单没有被退款", current_status == "paid", current_status)


SCENARIOS: dict[str, Callable[[ClientSession], Awaitable[None]]] = {
    "discovery": discovery,
    "unknown-tool": unknown_tool,
    "refund-unconfirmed": unconfirmed_refund,
    "refund-forged-confirmation": forged_confirmation,
}


async def main() -> None:
    parser = argparse.ArgumentParser(description="运行 MCP Host 权限实验")
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
