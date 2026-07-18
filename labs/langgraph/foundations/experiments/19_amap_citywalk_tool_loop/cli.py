"""最小 CityWalk tool loop 实验命令行入口。"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .adapters import DEFAULT_MCP_ENDPOINT, DEFAULT_OLLAMA_MODEL, REPO_ROOT
from .adapters import build_bound_model, build_model_tools, load_amap_mcp_url
from .agent import ALLOWED_TOOL_NAMES, DEFAULT_QUESTION
from .agent import build_citywalk_tool_loop_graph, build_initial_state


DEFAULT_GRAPHVIZ_OUTPUT = (
    REPO_ROOT / "labs/langgraph/foundations/assets/amap_citywalk_tool_loop_graph.png"
)


def render_graphviz(output_path: Path) -> None:
    """使用 Graphviz 把当前 LangGraph 结构导出成 PNG。"""
    graph = build_citywalk_tool_loop_graph()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    png = graph.get_graph().draw_png(None)
    output_path.write_bytes(png)
    print(f"Graphviz 图已生成：{output_path}")


async def run_experiment(question: str) -> None:
    """连接高德 MCP，运行模型驱动的 LangGraph tool loop，并打印 trace。"""
    mcp_url = load_amap_mcp_url()

    print(f"连接地址：{DEFAULT_MCP_ENDPOINT}?key=***")
    print("模型提供方：ollama")
    print(f"模型：{DEFAULT_OLLAMA_MODEL}")
    print(f"用户问题：{question}")
    print()

    async with streamable_http_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            tools_result = await session.list_tools()

            model_tools = build_model_tools(tools_result.tools, ALLOWED_TOOL_NAMES)
            allowed_tools = {tool["name"] for tool in model_tools}
            if missing_tools := sorted(ALLOWED_TOOL_NAMES - allowed_tools):
                raise RuntimeError(f"高德 MCP 缺少实验所需工具：{missing_tools}")

            model = build_bound_model(model_tools)
            graph = build_citywalk_tool_loop_graph(model, session, allowed_tools)
            initial_state = build_initial_state(question, model_tools)

            print(f"协议版本：{initialized.protocolVersion}")
            print(f"模型可见工具：{json.dumps(sorted(allowed_tools), ensure_ascii=False)}")
            print()

            final_state = await graph.ainvoke(initial_state)

    print("========== LangGraph Trace ==========")
    for item in final_state["trace"]:
        print(item)

    print()
    print("========== 最终回答 ==========")
    final_message = final_state["messages"][-1]
    print(final_message.content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行 LangGraph + Ollama + 高德 MCP 的最小 CityWalk tool loop。"
    )
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument(
        "--graphviz",
        nargs="?",
        const=str(DEFAULT_GRAPHVIZ_OUTPUT),
        metavar="PNG_PATH",
        help=(
            "只用 Graphviz 导出当前 LangGraph 结构图，不运行 Agent。"
            f"不传路径时默认输出到 {DEFAULT_GRAPHVIZ_OUTPUT}。"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.graphviz:
        render_graphviz(Path(args.graphviz).expanduser())
        return

    asyncio.run(run_experiment(question=args.question))
