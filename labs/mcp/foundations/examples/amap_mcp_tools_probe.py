"""探测高德官方 MCP Server 暴露的工具目录。

这个脚本模拟真实项目接入远程 MCP Server 的第一步：不猜工具名，
先通过 Streamable HTTP 完成 initialize 和 tools/list，观察 Server
实际提供了哪些工具、每个工具需要什么参数。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
DEFAULT_MCP_ENDPOINT = "https://mcp.amap.com/mcp"


def load_amap_mcp_url() -> str:
    """从项目 .env 读取高德 Key，并拼出远程 MCP URL。"""
    load_dotenv(REPO_ROOT / ".env")
    key = os.getenv("AMAP_MCP_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "缺少 AMAP_MCP_KEY。请先在项目根目录 .env 中配置高德 Web 服务 Key。"
        )
    return f"{DEFAULT_MCP_ENDPOINT}?key={key}"


def to_jsonable(value: Any) -> Any:
    """把 MCP SDK / Pydantic 对象转成适合打印的普通 JSON 数据。"""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value


async def probe_tools(show_schema: bool) -> None:
    mcp_url = load_amap_mcp_url()

    # 不打印完整 URL，避免把 key 带进终端日志、文章截图或提交记录。
    print(f"连接地址：{DEFAULT_MCP_ENDPOINT}?key=***")

    async with streamable_http_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools_result = await session.list_tools()

    print(f"协议版本：{initialized.protocolVersion}")
    print(f"工具数量：{len(tools_result.tools)}")

    for index, tool in enumerate(tools_result.tools, start=1):
        print()
        print(f"{index}. {tool.name}")
        if tool.description:
            print(f"   描述：{tool.description}")
        if show_schema:
            print("   参数 Schema：")
            print(json.dumps(to_jsonable(tool.inputSchema), ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="通过 Streamable HTTP 探测高德官方 MCP Server 工具目录。"
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="同时打印每个工具的 inputSchema。",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(probe_tools(show_schema=args.schema))


if __name__ == "__main__":
    main()
