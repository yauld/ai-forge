"""Ollama 模型与高德 MCP 的最小适配层。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from mcp import ClientSession


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_MCP_ENDPOINT = "https://mcp.amap.com/mcp"
DEFAULT_OLLAMA_MODEL = "qwen3-coder:30b"


def load_amap_mcp_url() -> str:
    """从项目 `.env` 读取高德 Key，并拼出远程 MCP URL。"""
    load_dotenv(REPO_ROOT / ".env")
    key = os.getenv("AMAP_MCP_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "缺少 AMAP_MCP_KEY。请先在项目根目录 .env 中配置高德 Web 服务 Key。"
        )
    return f"{DEFAULT_MCP_ENDPOINT}?key={key}"


def to_jsonable(value: Any) -> Any:
    """把 MCP SDK、Pydantic 或消息对象转成适合 json.dumps 的普通对象。"""
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
        payload = to_jsonable(result.structuredContent)
        return payload if isinstance(payload, dict) else {"content": payload}

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
            return {"content": text}
        return parsed if isinstance(parsed, dict) else {"content": parsed}

    return {"content": content}


async def call_mcp_tool(
    session: ClientSession,
    allowed_tools: set[str],
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Host 侧执行模型请求的 MCP 工具。"""
    if tool_name not in allowed_tools:
        raise RuntimeError(f"模型请求了未放行的工具：{tool_name}")
    if not isinstance(arguments, dict):
        raise RuntimeError(f"工具参数必须是 JSON object：{arguments!r}")

    result = await session.call_tool(tool_name, arguments)
    return extract_tool_payload(result)


def build_model_tools(tools: list[Any], allowed_tool_names: set[str]) -> list[dict[str, Any]]:
    """把 MCP tools/list 结果转换成模型可见的 tool schema。"""
    model_tools: list[dict[str, Any]] = []
    for tool in tools:
        if tool.name not in allowed_tool_names:
            continue
        model_tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": to_jsonable(tool.inputSchema),
            }
        )
    return model_tools


def summarize_tools(model_tools: list[dict[str, Any]]) -> str:
    """生成紧凑工具目录，放进系统提示词。"""
    return "\n".join(
        f"- {tool['name']}: {str(tool.get('description') or '').strip()}"
        for tool in model_tools
    )


def build_bound_model(model_tools: list[dict[str, Any]]) -> Any:
    """创建绑定高德 MCP 工具定义的本地 Ollama 模型。"""
    return ChatOllama(model=DEFAULT_OLLAMA_MODEL, temperature=0).bind_tools(model_tools)
