"""MCP Client：从 LangGraph 节点中调用 MCP Server。"""

from __future__ import annotations

import asyncio
import json
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


async def _call_tool_async(
    server_path: Path,
    cwd: Path,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        cwd=cwd,
    )

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(parameters))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.call_tool(tool_name, arguments)

    if result.structuredContent is not None:
        return dict(result.structuredContent)

    # 兼容没有 structuredContent 的返回形态，避免实验绑定到某个 SDK 小版本。
    if result.content:
        first = result.content[0]
        text = getattr(first, "text", "")
        if text:
            return json.loads(text)

    return {"content": [str(item) for item in result.content]}


async def _list_tools_async(server_path: Path, cwd: Path) -> list[dict[str, Any]]:
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(server_path)],
        cwd=cwd,
    )

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(parameters))
        session = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()
        result = await session.list_tools()

    return [
        {
            "name": tool.name,
            "description": tool.description or "",
            "input_schema": tool.inputSchema,
        }
        for tool in result.tools
    ]


def call_tool(
    server_path: Path,
    cwd: Path,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """同步包装，方便普通 LangGraph 节点直接调用。"""

    return asyncio.run(_call_tool_async(server_path, cwd, tool_name, arguments))


def list_tools(server_path: Path, cwd: Path) -> list[dict[str, Any]]:
    """连接 MCP Server 并读取真实 Tool schema。"""

    return asyncio.run(_list_tools_async(server_path, cwd))
