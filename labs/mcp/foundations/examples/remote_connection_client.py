"""通过 URL 连接远程 MCP Server，并完成一次 Tool 调用。"""

from __future__ import annotations

import asyncio
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


# 不传参数时连接本地实验 Server；也可以在命令行传入其他 MCP URL。
MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"


async def main() -> None:
    print(f"连接地址：{MCP_URL}")

    # 1. 根据 URL 建立 Streamable HTTP 通道。
    async with streamable_http_client(MCP_URL) as (read, write, _):
        # 2. 在这条通道上创建标准 MCP Client Session。
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("get_order", {"order_id": "O-1001"})

    print(f"协议版本：{initialized.protocolVersion}")
    print(f"发现 Tools：{[tool.name for tool in tools.tools]}")
    print(f"调用结果：{result.structuredContent}")


if __name__ == "__main__":
    asyncio.run(main())
