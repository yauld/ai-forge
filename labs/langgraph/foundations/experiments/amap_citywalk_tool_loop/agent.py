"""用模型驱动 tool loop 实现最小 CityWalk Agent。"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from mcp import ClientSession

from .adapters import call_mcp_tool, summarize_tools


DEFAULT_QUESTION = "我想在杭州西湖附近 citywalk 3 小时，想找咖啡、书店或展览，请推荐一个轻量路线。"
ALLOWED_TOOL_NAMES = {"maps_geo", "maps_around_search"}
MAX_TOOL_ROUNDS = 5


class CityWalkToolLoopState(TypedDict):
    """LangGraph 在模型节点与工具节点之间传递的最小状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    trace: list[str]
    tool_rounds: int


def compact_json(value: Any, max_chars: int = 900) -> str:
    """把工具结果压成一行，方便终端观察。"""
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(已截断)"


def compact_text(value: Any, max_chars: int = 500) -> str:
    """把模型输出压成一行，方便观察每一轮决策。"""
    text = " ".join(str(value or "").strip().split())
    if not text:
        return "本轮未输出文本，只给出 tool call。"
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(已截断)"


def append_trace(state: CityWalkToolLoopState, *items: str) -> list[str]:
    """返回追加后的 trace 列表。"""
    return [*state["trace"], *items]


def build_system_prompt(model_tools: list[dict[str, Any]]) -> str:
    """构造系统提示词：让模型自己决定何时调用工具、何时回答。"""
    return (
        "你是一个 CityWalk 助手。\n"
        "需要地图事实时，请自己调用工具；不需要时直接回答。\n"
        "建议先用 maps_geo 获取目标区域坐标，再用 maps_around_search 搜附近 POI。\n"
        "最终回答给出 3 个左右地点和一个简短行程建议；地点名称和地址只使用工具观察中出现过的信息，"
        "不要补充未搜索到的地点，不需要生成地图链接。\n\n"
        "当前可用工具：\n"
        f"{summarize_tools(model_tools)}"
    )


def build_initial_state(
    question: str,
    model_tools: list[dict[str, Any]],
) -> CityWalkToolLoopState:
    """构造 Graph 初始状态。"""
    return {
        "messages": [
            SystemMessage(content=build_system_prompt(model_tools)),
            HumanMessage(content=question),
        ],
        "trace": [],
        "tool_rounds": 0,
    }


def make_agent_llm(model: Any):
    """创建模型节点。"""

    async def agent_llm(state: CityWalkToolLoopState) -> dict[str, Any]:
        """模型观察当前 messages，并自己决定调用工具或最终回答。"""
        response = await model.ainvoke(state["messages"])
        trace_items = [
            f"[模型观察 {state['tool_rounds'] + 1}] {compact_text(response.content)}",
        ]

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            trace_items.append(
                "[模型决策] Tool Calls："
                + json.dumps(tool_calls, ensure_ascii=False, default=str)
            )
        else:
            trace_items.append("[模型决策] 没有 tool call，模型认为可以回答。")

        return {"messages": [response], "trace": append_trace(state, *trace_items)}

    return agent_llm


def make_run_mcp_tools(mcp_session: ClientSession, allowed_tools: set[str]):
    """创建工具执行节点。"""

    async def run_mcp_tools(state: CityWalkToolLoopState) -> dict[str, Any]:
        """Host 执行模型刚刚选择的 MCP 工具，并把结果写回 ToolMessage。"""
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            raise RuntimeError("run_mcp_tools 期望最后一条消息是 AIMessage。")

        tool_messages: list[ToolMessage] = []
        trace_items: list[str] = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["args"]
            trace_items.append(
                f"[Host行动] 执行 {tool_name}({json.dumps(arguments, ensure_ascii=False)})"
            )
            tool_result = await call_mcp_tool(
                mcp_session,
                allowed_tools,
                tool_name,
                arguments,
            )
            trace_items.append(f"[工具观察] {compact_json(tool_result)}")
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=tool_call["id"],
                )
            )

        return {
            "messages": tool_messages,
            "tool_rounds": state["tool_rounds"] + 1,
            "trace": append_trace(state, *trace_items),
        }

    return run_mcp_tools


def ask_model_to_finish(state: CityWalkToolLoopState) -> dict[str, Any]:
    """达到工具轮数上限时，要求模型基于已有观察直接收束。"""
    reminder = (
        "工具调用轮数已达到实验上限。请停止调用工具，"
        "只基于已有工具观察给出一个简短 CityWalk 建议。"
    )
    return {
        "messages": [HumanMessage(content=reminder)],
        "trace": append_trace(state, f"[Host提醒] {reminder}"),
    }


def route_after_agent(
    state: CityWalkToolLoopState,
) -> Literal["run_mcp_tools", "ask_model_to_finish", "__end__"]:
    """根据模型是否发起 tool call 决定继续工具循环还是结束。"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return "__end__"
    if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return "ask_model_to_finish"
    return "run_mcp_tools"


def build_citywalk_tool_loop_graph(
    model: Any | None = None,
    mcp_session: ClientSession | None = None,
    allowed_tools: set[str] | None = None,
):
    """构建最小模型驱动 tool loop。"""
    if model is None or mcp_session is None or allowed_tools is None:
        async def graphviz_only_node(state: CityWalkToolLoopState) -> dict[str, Any]:
            return {}

        agent_node = graphviz_only_node
        tool_node = graphviz_only_node
    else:
        agent_node = make_agent_llm(model)
        tool_node = make_run_mcp_tools(mcp_session, allowed_tools)

    builder = StateGraph(CityWalkToolLoopState)
    builder.add_node("agent_llm", agent_node)
    builder.add_node("run_mcp_tools", tool_node)
    builder.add_node("ask_model_to_finish", ask_model_to_finish)

    builder.add_edge(START, "agent_llm")
    builder.add_conditional_edges(
        "agent_llm",
        route_after_agent,
        {
            "run_mcp_tools": "run_mcp_tools",
            "ask_model_to_finish": "ask_model_to_finish",
            "__end__": END,
        },
    )
    builder.add_edge("run_mcp_tools", "agent_llm")
    builder.add_edge("ask_model_to_finish", "agent_llm")

    return builder.compile(name="Amap CityWalk Tool Loop")
