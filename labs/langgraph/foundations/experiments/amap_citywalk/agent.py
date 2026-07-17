"""CityWalk Agent 的 LangGraph 主线。"""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_core.messages import ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from mcp import ClientSession

from .adapters import call_mcp_tool, summarize_tools
from .audit import collect_verified_poi_coordinates, collect_verified_pois
from .audit import find_unverified_final_claims
from .audit import summarize_verified_pois, validate_personal_map_pois


DEFAULT_QUESTION = "明天下午想在杭州西湖附近玩 3 小时，尽量少走路，最好有咖啡、展览或书店；如果下雨就安排室内为主，最后给我一个能打开高德地图的路线。"

# 这个实验只暴露少量工具给模型，避免工具目录太大干扰观察。
ALLOWED_TOOL_NAMES = {
    "maps_weather",
    "maps_geo",
    "maps_around_search",
    "maps_schema_personal_map",
}
MAX_TOOL_ROUNDS = 8
MAX_FINAL_REVIEW_ROUNDS = 2


class CityWalkAgentState(TypedDict):
    """LangGraph 在节点之间传递的状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    trace: list[str]
    tool_rounds: int
    has_target_location: bool
    has_searched_pois: bool
    has_map_link: bool
    weather_summary: str | None
    accepted_map_arguments: dict[str, Any] | None
    map_link: str | None
    verified_pois: dict[str, dict[str, Any]]
    verified_poi_coordinates: dict[str, list[dict[str, float]]]
    final_review_rounds: int
    final_ready: bool


def compact_json(value: Any, max_chars: int = 900) -> str:
    """把工具结果压成一行，方便终端观察。"""
    text = json.dumps(value, ensure_ascii=False)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(已截断)"


def compact_text(value: Any, max_chars: int = 500) -> str:
    """把模型文本压成一行，方便观察每轮模型自己的文字输出。"""
    text = str(value or "").strip()
    if not text:
        return "本轮未输出文本，只给出 tool call。"
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "...(已截断)"


def append_trace(state: CityWalkAgentState, *items: str) -> list[str]:
    """返回追加后的 trace 列表。"""
    return [*state["trace"], *items]


def build_system_prompt(model_tools: list[dict[str, Any]]) -> str:
    """构造系统提示词：让模型自己选择工具，Host 不替它规划下一步。"""
    return (
        "你是一个地图与出行助手，运行在用户自研 AI 应用的后端中。\n"
        f"今天是 {date.today().isoformat()}。\n"
        "请自己决定何时调用工具、何时最终回答；需要外部事实时不能凭记忆补全。\n"
        "规则：先查天气再判断下雨策略；路线链接必须来自 maps_schema_personal_map；"
        "地图点必须先来自 maps_around_search，再用包含该 POI 精确 name 的 maps_geo 补坐标；"
        "maps_schema_personal_map 的 name/poiId/lon/lat 必须与工具结果一致，lineList.title 必须包含建议停留时间；"
        "最终回答只写工具可证明的信息，不写楼层、一层大堂、步行距离、品牌背景或氛围评价。\n\n"
        "当前可用工具：\n"
        f"{summarize_tools(model_tools)}"
    )


def build_initial_state(question: str, model_tools: list[dict[str, Any]]) -> CityWalkAgentState:
    """构造 Graph 初始状态。"""
    return {
        "messages": [
            SystemMessage(content=build_system_prompt(model_tools)),
            HumanMessage(content=question),
        ],
        "trace": [],
        "tool_rounds": 0,
        "has_target_location": False,
        "has_searched_pois": False,
        "has_map_link": False,
        "weather_summary": None,
        "accepted_map_arguments": None,
        "map_link": None,
        "verified_pois": {},
        "verified_poi_coordinates": {},
        "final_review_rounds": 0,
        "final_ready": False,
    }


def make_agent_llm(model: Any):
    """创建模型节点。"""

    async def agent_llm(state: CityWalkAgentState) -> dict[str, Any]:
        """模型观察当前 messages，并自己决定调用工具或给最终答案。"""
        response = await model.ainvoke(state["messages"])
        trace_items = [
            f"[模型观察 {state['tool_rounds'] + 1}] 模型读取当前 messages 后生成回复 | {compact_text(response.content)}",
        ]

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            trace_items.append(
                "[模型决策] Tool Calls："
                + json.dumps(tool_calls, ensure_ascii=False, default=str)
            )
        else:
            trace_items.append("[模型决策] 没有 tool call，模型认为可以直接回答。")

        return {"messages": [response], "trace": append_trace(state, *trace_items)}

    return agent_llm


def summarize_weather_result(tool_result: dict[str, Any]) -> str | None:
    """提取明天天气摘要，避免最终回答再靠模型复述。"""
    target_date = (date.today() + timedelta(days=1)).isoformat()
    forecasts = tool_result.get("forecasts")
    if not isinstance(forecasts, list):
        return None

    for forecast in forecasts:
        if not isinstance(forecast, dict) or forecast.get("date") != target_date:
            continue
        return (
            f"{target_date}：白天{forecast.get('dayweather')}，"
            f"夜间{forecast.get('nightweather')}，"
            f"{forecast.get('nighttemp')}~{forecast.get('daytemp')}°C，"
            f"{forecast.get('daywind')}风{forecast.get('daypower')}级"
        )
    return None


def extract_map_link(tool_result: dict[str, Any]) -> str | None:
    """从 maps_schema_personal_map 结果中提取高德地图链接。"""
    content = tool_result.get("content")
    if isinstance(content, str) and content.startswith("amapuri://"):
        return content
    return None


def build_safe_final_answer(state: CityWalkAgentState) -> str:
    """模型最终回答仍不可靠时，由 Host 用已验证事实生成兜底回答。"""
    lines = ["## 明天天气", ""]
    if state["weather_summary"]:
        lines.append(f"- {state['weather_summary']}")
    else:
        lines.append("- 已调用天气工具，但未提取到可用的明日天气摘要。")

    lines.extend(["", "## 行程", ""])
    map_arguments = state["accepted_map_arguments"] or {}
    line_list = map_arguments.get("lineList")
    if isinstance(line_list, list):
        for index, route_line in enumerate(line_list, start=1):
            if not isinstance(route_line, dict):
                continue
            title = str(route_line.get("title") or "").strip()
            point_info_list = route_line.get("pointInfoList")
            if not isinstance(point_info_list, list):
                continue
            for point in point_info_list:
                if not isinstance(point, dict):
                    continue
                poi_id = str(point.get("poiId") or "").strip()
                verified = state["verified_pois"].get(poi_id, {})
                name = verified.get("name") or point.get("name") or "<未命名>"
                address = verified.get("address") or "<地址缺失>"
                lines.append(f"{index}. {name}")
                lines.append(f"   - 地址：{address}")
                lines.append(f"   - 建议停留：{title}")

    lines.extend(["", "## 高德地图路线", "", state["map_link"] or "<地图链接缺失>"])
    return "\n".join(lines)


def make_run_mcp_tools(mcp_session: ClientSession, allowed_tools: set[str]):
    """创建工具执行节点。"""

    async def run_mcp_tools(state: CityWalkAgentState) -> dict[str, Any]:
        """Host 执行模型刚刚选择的 MCP 工具，并把结果写回 ToolMessage。"""
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            raise RuntimeError("run_mcp_tools 期望最后一条消息是 AIMessage。")

        tool_messages: list[ToolMessage] = []
        trace_items: list[str] = []
        has_target_location = state["has_target_location"]
        has_searched_pois = state["has_searched_pois"]
        has_map_link = state["has_map_link"]
        weather_summary = state["weather_summary"]
        accepted_map_arguments = state["accepted_map_arguments"]
        map_link = state["map_link"]
        verified_pois = dict(state["verified_pois"])
        verified_poi_coordinates = {
            poi_id: list(coordinates)
            for poi_id, coordinates in state["verified_poi_coordinates"].items()
        }

        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["args"]

            if tool_name == "maps_around_search" and not has_target_location:
                error = (
                    "Host校验失败：调用 maps_around_search 前，必须先用 maps_geo "
                    "获取用户目标区域的真实经纬度；不能使用模型记忆中的坐标。"
                )
                trace_items.append(f"[Host拒绝] {error}")
                tool_messages.append(
                    ToolMessage(content=error, tool_call_id=tool_call["id"])
                )
                continue

            if tool_name == "maps_schema_personal_map" and not has_searched_pois:
                error = (
                    "Host校验失败：调用 maps_schema_personal_map 前，必须先用 "
                    "maps_around_search 获取真实 POI，并使用搜索结果里的 poiId。"
                )
                trace_items.append(f"[Host拒绝] {error}")
                tool_messages.append(
                    ToolMessage(content=error, tool_call_id=tool_call["id"])
                )
                continue

            if tool_name == "maps_schema_personal_map":
                error = validate_personal_map_pois(
                    arguments,
                    verified_pois,
                    verified_poi_coordinates,
                )
                if error is not None:
                    allowed = summarize_verified_pois(verified_pois)
                    if allowed:
                        error = f"{error} 当前可用 POI：{allowed}"
                    trace_items.append(f"[Host拒绝] {error}")
                    tool_messages.append(
                        ToolMessage(content=error, tool_call_id=tool_call["id"])
                    )
                    continue

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

            # 搜索 POI 前的 maps_geo 用来定位目标区域；搜索 POI 后的 maps_geo 用来补 POI 坐标。
            if tool_name == "maps_weather":
                weather_summary = summarize_weather_result(tool_result)
            if tool_name == "maps_geo" and not has_searched_pois:
                has_target_location = True
            if tool_name == "maps_around_search":
                has_searched_pois = True
                verified_pois.update(collect_verified_pois(tool_result))
            if tool_name == "maps_geo":
                for poi_id, coordinates in collect_verified_poi_coordinates(
                    arguments,
                    tool_result,
                    verified_pois,
                ).items():
                    verified_poi_coordinates.setdefault(poi_id, []).extend(coordinates)
            if tool_name == "maps_schema_personal_map":
                has_map_link = True
                accepted_map_arguments = arguments
                map_link = extract_map_link(tool_result)
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=tool_call["id"],
                )
            )

        return {
            "messages": tool_messages,
            "tool_rounds": state["tool_rounds"] + 1,
            "has_target_location": has_target_location,
            "has_searched_pois": has_searched_pois,
            "has_map_link": has_map_link,
            "weather_summary": weather_summary,
            "accepted_map_arguments": accepted_map_arguments,
            "map_link": map_link,
            "verified_pois": verified_pois,
            "verified_poi_coordinates": verified_poi_coordinates,
            "trace": append_trace(state, *trace_items),
        }

    return run_mcp_tools


async def validate_final_answer(state: CityWalkAgentState) -> dict[str, Any]:
    """Host 校验模型是否可以结束。"""
    if state["has_map_link"]:
        last_message = state["messages"][-1]
        final_text = str(getattr(last_message, "content", "") or "")
        unverified_claims = find_unverified_final_claims(final_text)
        if unverified_claims and state["final_review_rounds"] < MAX_FINAL_REVIEW_ROUNDS:
            reminder = (
                "Host校验：最终回答不符合可审计输出要求。"
                f"未经工具证明的描述：{'、'.join(unverified_claims)}。"
                "请重新给出最终回答，只保留工具可证明的信息：日期天气、POI 名称、"
                "地址、建议停留时间，以及 maps_schema_personal_map 返回的原始地图链接。"
                "不要写楼层、一层大堂、内设、全程室内、步行距离、路线顺直、品牌背景、"
                "氛围评价或其他推断。"
            )
            return {
                "messages": [HumanMessage(content=reminder)],
                "final_review_rounds": state["final_review_rounds"] + 1,
                "final_ready": False,
                "trace": append_trace(state, f"[Host校验] {reminder}"),
            }
        if unverified_claims:
            safe_answer = build_safe_final_answer(state)
            return {
                "messages": [AIMessage(content=safe_answer)],
                "final_ready": True,
                "trace": append_trace(
                    state,
                    "[Host校验] 模型多次未去除未经证明描述，改用 Host 兜底事实回答。",
                ),
            }

        return {
            "final_ready": True,
            "trace": append_trace(state, "[Host校验] 已获得真实地图链接，可以结束。"),
        }

    if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return {
            "final_ready": True,
            "trace": append_trace(
                state,
                f"[Host校验] 已达到最大工具轮数 {MAX_TOOL_ROUNDS}，停止继续重试。",
            ),
        }

    reminder = (
        "Host校验：你还不能最终回答。用户要求地图路线，但你还没有调用 "
        "maps_schema_personal_map 获取真实高德地图链接。请继续观察已有工具结果，"
        "如果信息不足就继续调用工具；最终链接必须来自 maps_schema_personal_map。"
    )
    return {
        "messages": [HumanMessage(content=reminder)],
        "final_ready": False,
        "trace": append_trace(state, f"[Host校验] {reminder}"),
    }


def route_after_agent(
    state: CityWalkAgentState,
) -> Literal["run_mcp_tools", "validate_final_answer"]:
    """根据模型是否发起 tool call 决定继续行动还是结束。"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    return "run_mcp_tools" if tool_calls else "validate_final_answer"


def route_after_validation(state: CityWalkAgentState) -> Literal["agent_llm", "__end__"]:
    """最终回答未通过校验时，回到模型继续观察和决策。"""
    return "__end__" if state["final_ready"] else "agent_llm"


def build_citywalk_graph(
    model: Any | None = None,
    mcp_session: ClientSession | None = None,
    allowed_tools: set[str] | None = None,
):
    """构建模型驱动的 Agent tool-calling loop。"""
    if model is None or mcp_session is None or allowed_tools is None:
        async def graphviz_only_node(state: CityWalkAgentState) -> dict[str, Any]:
            return {}

        agent_node = graphviz_only_node
        tool_node = graphviz_only_node
    else:
        agent_node = make_agent_llm(model)
        tool_node = make_run_mcp_tools(mcp_session, allowed_tools)

    builder = StateGraph(CityWalkAgentState)
    builder.add_node("agent_llm", agent_node)
    builder.add_node("run_mcp_tools", tool_node)
    builder.add_node("validate_final_answer", validate_final_answer)

    builder.add_edge(START, "agent_llm")
    builder.add_conditional_edges(
        "agent_llm",
        route_after_agent,
        {
            "run_mcp_tools": "run_mcp_tools",
            "validate_final_answer": "validate_final_answer",
        },
    )
    builder.add_edge("run_mcp_tools", "agent_llm")
    builder.add_conditional_edges(
        "validate_final_answer",
        route_after_validation,
        {
            "agent_llm": "agent_llm",
            "__end__": END,
        },
    )

    return builder.compile(name="Amap CityWalk Agent Tool Loop")
