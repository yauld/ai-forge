"""通过 stdio 或 Streamable HTTP 执行相同的 MCP 调用。"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client


HERE = Path(__file__).resolve().parent
SERVER = HERE / "shop_order_transport_server.py"


def parse_args() -> argparse.Namespace:
    """读取命令行参数。

    transport 是必填参数：
    - stdio：Client 会自动启动一个 Server 子进程。
    - streamable-http：Client 会连接一个已经启动好的 HTTP Server。
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("transport", choices=("stdio", "streamable-http"))
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/mcp",
        help="streamable-http 模式连接的 MCP endpoint",
    )
    parser.add_argument(
        "--server",
        type=Path,
        default=SERVER,
        help="stdio 模式使用的 Server 文件",
    )
    return parser.parse_args()


async def call_order_tool(read, write, transport: str) -> None:
    """在已经建立好的连接上，执行一次 MCP 调用。

    read 和 write 是 MCP SDK 提供的“消息流”：
    - read：从 Server 读取 MCP 消息。
    - write：向 Server 发送 MCP 消息。

    这是一层抽象。不同 transport 下面，它们对应的底层通道不同：

    - stdio 模式：
      read  表示 Client 进程从 Server 子进程的 stdout 读取 MCP 消息。
      write 表示 Client 进程向 Server 子进程的 stdin 写入 MCP 消息。

    - streamable-http 模式：
      read/write 表示 SDK 包装出来的 HTTP 消息流。
      Client 不直接操作 Server 进程的 stdin/stdout，而是通过 HTTP endpoint
      发送和接收 MCP 消息。

    只要拿到了这两个对象，后面的 MCP 代码就不关心底层是 stdio
    还是 HTTP。这也是本实验最重要的观察。
    """
    async with ClientSession(read, write) as session:
        # 1. initialize：Client 和 Server 先互相确认协议版本和基础信息。
        initialized = await session.initialize()

        # 2. list_tools：询问 Server 提供了哪些 Tool。
        tools = await session.list_tools()

        # 3. call_tool：调用其中一个 Tool。
        result = await session.call_tool(
            "get_order",
            {"order_id": "O-1001"},
        )

    print(f"transport: {transport}")
    print(f"protocol: {initialized.protocolVersion}")
    print(f"tools: {[tool.name for tool in tools.tools]}")
    print(f"isError: {result.isError}")
    print(f"structuredContent: {result.structuredContent}")


async def run_stdio(server: Path) -> None:
    """用 stdio transport 调用 MCP Server。

    stdio 模式下，Client 负责启动 Server。
    这里不是先手动运行 Server，而是把 Server 启动命令交给 stdio_client。
    """
    if server == SERVER:
        server_args = [str(server), "--transport", "stdio"]
    else:
        # 这个分支用于 broken_stdout_server.py。
        # 它本身已经固定使用 stdio，不需要额外传 --transport。
        server_args = [str(server)]

    parameters = StdioServerParameters(
        command=sys.executable,
        args=server_args,
        cwd=HERE,
    )

    # stdio_client 会：
    # 1. 启动 Server 子进程；
    # 2. 把 Client 进程写出的 MCP 消息发到 Server 子进程的 stdin；
    # 3. 从 Server 子进程的 stdout 读取 MCP 消息；
    # 4. 在 async with 结束时关闭子进程。
    async with stdio_client(parameters) as (read, write):
        await call_order_tool(read, write, "stdio")


async def run_streamable_http(url: str) -> None:
    """用 Streamable HTTP transport 调用 MCP Server。

    HTTP 模式下，Client 不会启动 Server。
    运行这个函数前，需要先在另一个终端启动：

        uv run labs/mcp/foundations/examples/shop_order_transport_server.py \
          --transport streamable-http
    """
    # streamable_http_client 会连接 HTTP endpoint，并把 HTTP 通信包装成
    # ClientSession 能使用的 read/write 消息流。
    #
    # 第三个返回值用于获取 session id。本实验只观察一次调用，所以不用它。
    async with streamable_http_client(url) as (read, write, _):
        await call_order_tool(read, write, "streamable-http")


async def run(transport: str, url: str, server: Path) -> None:
    """根据命令行选择对应的 transport。"""
    if transport == "stdio":
        await run_stdio(server)
    else:
        await run_streamable_http(url)


def main() -> None:
    args = parse_args()

    # MCP Python SDK 使用异步 I/O；这里从同步命令行入口启动事件循环。
    asyncio.run(run(args.transport, args.url, args.server.resolve()))


if __name__ == "__main__":
    main()
