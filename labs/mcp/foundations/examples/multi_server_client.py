"""连接两个 MCP Server，并按来源路由 Tool 调用。

这个脚本故意写得偏教学化：不用复杂封装，只保留理解 MCP Client
最需要的流程。

你可以把它想象成一个很小的 Host：

1. Host 启动并连接订单分析 Server。
2. Host 启动并连接订单详情 Server。
3. Host 分别发现两个 Server 提供的能力。
4. Host 调用其中一个 Server 的 Tool、Resource 和 Prompt。
5. Host 根据调用意图里的 server 字段，把 Tool 调用发给正确 Server。
"""

from __future__ import annotations

import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import AnyUrl


HERE = Path(__file__).resolve().parent

ANALYSIS_SERVER = HERE / "shop_order_analysis_server.py"
PRIMITIVES_SERVER = HERE / "shop_order_primitives_server.py"


async def start_stdio_session(
    stack: AsyncExitStack,
    server_script: Path,
) -> ClientSession:
    """启动一个 stdio MCP Server，并返回它对应的 ClientSession。"""
    # stdio 模式下，Client 负责启动 Server 子进程。
    # sys.executable 表示使用当前 uv 环境里的 Python 来运行 Server 脚本。
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        cwd=HERE,
    )

    # stdio_client 返回两个消息流：
    # - read：Client 从 Server 读取 MCP 消息。
    # - write：Client 向 Server 写入 MCP 消息。
    read, write = await stack.enter_async_context(stdio_client(parameters))

    # ClientSession 把 read/write 包装成更好用的方法：
    # initialize、list_tools、call_tool、read_resource、get_prompt 等。
    session = await stack.enter_async_context(ClientSession(read, write))

    # initialize 是 MCP Client 连接 Server 后必须先做的握手。
    # 完成 initialize 后，才能继续发现和调用能力。
    await session.initialize()
    return session


async def discover_capabilities(session: ClientSession) -> dict[str, list[str]]:
    """发现一个 Server 提供的 Tool、Resource、Resource Template 和 Prompt。"""
    tools = await session.list_tools()
    resources = await session.list_resources()
    resource_templates = await session.list_resource_templates()
    prompts = await session.list_prompts()

    # 这是 Host 自己保存的“能力目录”。
    # MCP Server 只返回能力列表；Host 要自己记住这些能力来自哪个 Server。
    return {
        "tools": [tool.name for tool in tools.tools],
        "resources": [str(resource.uri) for resource in resources.resources],
        "resource_templates": [
            str(template.uriTemplate)
            for template in resource_templates.resourceTemplates
        ],
        "prompts": [prompt.name for prompt in prompts.prompts],
    }


def print_capabilities(
    server_id: str,
    capabilities: dict[str, list[str]],
) -> None:
    """打印某个 Server 的能力目录。"""
    print(f"\n[{server_id}]")
    print(f"tools: {capabilities['tools']}")
    print(f"resources: {capabilities['resources']}")
    print(f"resource_templates: {capabilities['resource_templates']}")
    print(f"prompts: {capabilities['prompts']}")


async def call_analysis_server(session: ClientSession) -> None:
    """在订单分析 Server 上分别调用 Tool、Resource 和 Prompt。"""
    print("\n=== Call analysis server ===")

    # Tool 表达“执行动作”。
    # 这里让 Server 查询 SQLite，返回一段日期内的订单汇总。
    summary_result = await session.call_tool(
        "query_daily_order_summary",
        {
            "start_date": "2026-06-19",
            "end_date": "2026-06-25",
        },
    )
    print("tool query_daily_order_summary:")
    print(summary_result.structuredContent["summary"])  # type: ignore[index]

    # Resource 表达“读取上下文”。
    # 这里读取订单数据库 schema，它不会执行查询动作。
    schema_result = await session.read_resource(AnyUrl("shop://database/schema"))
    schema_text = schema_result.contents[0].text  # type: ignore[attr-defined]
    print("\nresource shop://database/schema:")
    print(schema_text.splitlines()[0])

    # Prompt 表达“获取任务模板”。
    # 获取 Prompt 不会自动读取 Resource，也不会自动调用 Tool。
    prompt_result = await session.get_prompt(
        "daily_order_analysis_report",
        {"date_range": "2026-06-19 到 2026-06-25"},
    )
    prompt_text = prompt_result.messages[0].content.text # type: ignore
    print("\nprompt daily_order_analysis_report:")
    print(prompt_text.splitlines()[0])


async def route_tool_call(
    sessions: dict[str, ClientSession],
    capability_directory: dict[str, dict[str, list[str]]],
    intent: dict[str, Any],
) -> Any:
    """根据调用意图里的 server 字段，把 Tool 调用发给正确 Server。"""
    server_id = intent["server"]
    tool_name = intent["tool"]
    arguments = intent.get("arguments", {})

    # 先确认 Host 认识这个 Server。
    if server_id not in sessions:
        raise ValueError(f"Unknown MCP server: {server_id}")

    # 再确认这个 Tool 确实属于这个 Server。
    tools = capability_directory[server_id]["tools"]
    if tool_name not in tools:
        raise ValueError(f"Server {server_id} does not provide tool {tool_name}")

    # 最后才用这个 Server 对应的 ClientSession 发起 call_tool。
    return await sessions[server_id].call_tool(tool_name, arguments)


async def main() -> None:
    """运行多 Server Client 实验。"""
    # AsyncExitStack 用来统一管理多个异步资源。
    # 离开 async with 后，它会关闭所有 ClientSession 和 stdio 子进程。
    async with AsyncExitStack() as stack:
        # 第一步：分别连接两个 Server。
        analysis_session = await start_stdio_session(stack, ANALYSIS_SERVER)
        primitives_session = await start_stdio_session(stack, PRIMITIVES_SERVER)

        # 第二步：Host 保存每个 Server 对应的 ClientSession。
        # 多 Server 场景下，不要把所有 Server 混成一个连接。
        sessions = {
            "shop-order-analysis": analysis_session,
            "shop-order-primitives": primitives_session,
        }

        # 第三步：Host 发现并保存每个 Server 的能力目录。
        capability_directory = {
            "shop-order-analysis": await discover_capabilities(analysis_session),
            "shop-order-primitives": await discover_capabilities(primitives_session),
        }

        print("=== Host capability directory ===")
        for server_id, capabilities in capability_directory.items():
            print_capabilities(server_id, capabilities)

        # 第四步：在一个 Server 上调用 Tool、Resource 和 Prompt。
        await call_analysis_server(analysis_session)

        # 第五步：模拟一次 Host 已经决定好的 Tool 调用意图。
        # 真实应用里，这个意图可能来自模型、用户操作或固定工作流。
        intent = {
            "server": "shop-order-primitives",
            "tool": "get_order",
            "arguments": {"order_id": "O-1001"},
        }

        print("\n=== Routed tool call ===")
        result = await route_tool_call(sessions, capability_directory, intent)
        print(f"intent: {intent}")
        print(f"result: {result.structuredContent}")

    print("\nAll ClientSession objects and stdio subprocesses are closed.")


if __name__ == "__main__":
    asyncio.run(main())
