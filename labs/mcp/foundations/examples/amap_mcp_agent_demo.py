"""自研 AI 应用接入高德官方 MCP Server 的最小闭环。

脚本里的 Python 进程扮演 Host：

1. 从 .env 读取高德 Key；
2. 用 MCP Python SDK 通过 Streamable HTTP 连接高德官方 MCP Server；
3. 通过 tools/list 动态发现工具；
4. 把 MCP 工具定义交给本地 Ollama/qwen3-coder:30b；
5. 校验模型提出的 tool call，再由 Host 调用 MCP Server；
6. 把工具结果交回模型生成最终回答。

这更接近真实 AI 应用：模型不直接持有 Key，也不直接拼 HTTP 请求；
外部能力调用始终由 Host 控制。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
DEFAULT_MCP_ENDPOINT = "https://mcp.amap.com/mcp"
DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_QUESTION = "明天去杭州西湖适合出门吗？请结合天气给出建议。"
MAX_TOOL_ROUNDS = 4


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
    """把 MCP SDK、Pydantic 或消息对象转成普通 JSON 数据。"""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [to_jsonable(item) for item in value]
    return value


def extract_tool_payload(result: Any) -> dict[str, Any]:
    """提取 MCP Tool 结果，并兼容高德把 JSON 放在 TextContent.text 的情况。"""
    if result.structuredContent is not None:
        return to_jsonable(result.structuredContent)

    content = to_jsonable(result.content)
    if (
        isinstance(content, list)
        and len(content) == 1
        and isinstance(content[0], dict)
        and isinstance(content[0].get("text"), str)
    ):
        text = content[0]["text"].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"content": content}
        if isinstance(parsed, dict):
            return parsed
        return {"content": parsed}

    return {"content": content}


def build_model_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """把 MCP tools/list 的结果转换为 LangChain/Ollama 可见的工具定义。"""
    model_tools: list[dict[str, Any]] = []
    for tool in tools:
        model_tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": to_jsonable(tool.inputSchema),
            }
        )
    return model_tools


def summarize_tools(model_tools: list[dict[str, Any]]) -> str:
    """生成一份紧凑工具目录，放进 SystemMessage 帮模型理解可用能力。"""
    lines = []
    for tool in model_tools:
        description = str(tool.get("description") or "").strip()
        lines.append(f"- {tool['name']}: {description}")
    return "\n".join(lines)


async def call_mcp_tool(
    session: ClientSession,
    allowed_tools: set[str],
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Host 校验工具名后，才把调用发送给远程 MCP Server。"""
    if tool_name not in allowed_tools:
        raise RuntimeError(f"模型请求了未发现的工具：{tool_name}")
    if not isinstance(arguments, dict):
        raise RuntimeError(f"工具参数必须是 JSON object：{arguments!r}")

    result = await session.call_tool(tool_name, arguments)
    return extract_tool_payload(result)


async def run_agent(question: str, model_name: str) -> None:
    mcp_url = load_amap_mcp_url()
    print(f"连接地址：{DEFAULT_MCP_ENDPOINT}?key=***")
    print(f"本地模型：{model_name}")
    print(f"用户问题：{question}")

    async with streamable_http_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools_result = await session.list_tools()

            model_tools = build_model_tools(tools_result.tools)
            allowed_tools = {tool["name"] for tool in model_tools}
            print(f"协议版本：{initialized.protocolVersion}")
            print(f"发现工具：{json.dumps(sorted(allowed_tools), ensure_ascii=False)}")

            model = ChatOllama(model=model_name, temperature=0).bind_tools(model_tools)
            messages = [
                SystemMessage(
                    content=(
                        "你是一个地图与出行助手，运行在用户自研 AI 应用的后端中。\n"
                        f"今天是 {date.today().isoformat()}。\n"
                        "你不能编造实时天气、地点或路线信息；需要外部信息时，"
                        "必须使用 Host 提供的 MCP 工具。\n"
                        "工具调用由 Host 执行，你只负责选择工具和参数。\n"
                        "拿到工具结果后，请用中文给出简洁、实用的回答。\n\n"
                        "当前可用 MCP 工具：\n"
                        f"{summarize_tools(model_tools)}"
                    )
                ),
                HumanMessage(content=question),
            ]

            for round_index in range(1, MAX_TOOL_ROUNDS + 1):
                response = await model.ainvoke(messages)
                messages.append(response)

                tool_calls = response.tool_calls
                print()
                print(f"模型回合 {round_index}：")
                print(f"  文本：{response.content}")
                print(f"  Tool Calls：{json.dumps(tool_calls, ensure_ascii=False)}")

                if not tool_calls:
                    print()
                    print(f"最终回答：{response.content}")
                    return

                for tool_call in tool_calls:
                    tool_name = tool_call["name"]
                    arguments = tool_call["args"]
                    print(f"  执行 MCP Tool：{tool_name}")
                    print(f"  参数：{json.dumps(arguments, ensure_ascii=False)}")

                    tool_result = await call_mcp_tool(
                        session=session,
                        allowed_tools=allowed_tools,
                        tool_name=tool_name,
                        arguments=arguments,
                    )
                    print(
                        "  结果："
                        + json.dumps(tool_result, ensure_ascii=False, indent=2)[:1600]
                    )

                    messages.append(
                        ToolMessage(
                            content=json.dumps(tool_result, ensure_ascii=False),
                            tool_call_id=tool_call["id"],
                        )
                    )

            raise RuntimeError(f"超过最大工具调用轮数：{MAX_TOOL_ROUNDS}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行一个本地 Ollama + 高德远程 MCP Server 的最小 AI 应用闭环。"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_agent(question=args.question, model_name=args.model))


if __name__ == "__main__":
    main()
