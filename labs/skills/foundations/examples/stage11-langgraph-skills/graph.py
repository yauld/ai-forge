"""阶段 11：把 Skills runtime 放进 LangGraph 状态图。"""

from __future__ import annotations

import re
import sqlite3
import json
from pathlib import Path
from typing import Any, Literal, cast

from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from runtime.loader import SkillLoader
from runtime.mcp_client import call_tool, list_tools
from runtime.registry import SkillRegistry
from runtime.report_writer import write_report
from runtime.router import route_skill
from runtime.types import SkillGraphState


HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE / "skills"
SERVER_PATH = HERE / "mcp_server.py"
DEFAULT_OUTPUT_PATH = HERE / "outputs" / "order-report-demo.md"
DEFAULT_CHECKPOINT_PATH = HERE / "outputs" / "stage11-checkpoints.sqlite"
DEFAULT_MODEL = "qwen3-coder:30b"


def scan_skills_node(state: SkillGraphState) -> SkillGraphState:
    """Registry 节点：只扫描 metadata，不加载 Skill 正文。"""

    registry = SkillRegistry(SKILLS_ROOT)
    skills = registry.scan()
    candidates = [
        {"name": skill.name, "description": skill.description}
        for skill in skills
    ]
    return {
        "skill_candidates": candidates,
        "trace": [
            {
                "node": "scan_skills",
                "skills": [candidate["name"] for candidate in candidates],
            }
        ],
    }


def route_skill_node(state: SkillGraphState) -> SkillGraphState:
    """Router 节点：根据 metadata 选择 Skill。"""

    registry = SkillRegistry(SKILLS_ROOT)
    skills = registry.scan()
    task = _require_str(state, "task")
    route_result = route_skill(
        task=task,
        skills=skills,
        model_name=state.get("model_name", DEFAULT_MODEL),
    )
    if route_result.skill_name is None:
        raise RuntimeError(route_result.reason)

    return {
        "selected_skill": route_result.skill_name,
        "route_reason": route_result.reason,
        "route_raw_response": route_result.raw_response,
        "trace": [
            {
                "node": "route_skill",
                "model": state.get("model_name", DEFAULT_MODEL),
                "selected_skill": route_result.skill_name,
                "reason": route_result.reason,
            }
        ],
    }


def load_skill_node(state: SkillGraphState) -> SkillGraphState:
    """Loader 节点：命中后才读取完整 `SKILL.md`。"""

    registry = SkillRegistry(SKILLS_ROOT)
    registry.scan()
    selected_skill = _require_str(state, "selected_skill")
    metadata = registry.get(selected_skill)
    if metadata is None:
        raise RuntimeError(f"找不到 Skill：{selected_skill}")

    loaded = SkillLoader().load(metadata)
    loaded_files = [str(path) for path in loaded.loaded_files]
    return {
        "skill_text": loaded.body,
        "loaded_files": loaded_files,
        "trace": [
            {
                "node": "load_skill",
                "loaded_files": loaded_files,
            }
        ],
    }


def discover_mcp_tools_node(state: SkillGraphState) -> SkillGraphState:
    """工具发现节点：Host 连接 MCP Server 并读取真实 Tool schema。"""

    tools = list_tools(server_path=SERVER_PATH, cwd=HERE)
    return {
        "mcp_tools": tools,
        "trace": [
            {
                "node": "discover_mcp_tools",
                "tools": [tool["name"] for tool in tools],
            }
        ],
    }


def plan_tool_call_node(state: SkillGraphState) -> SkillGraphState:
    """计划节点：模型基于 Skill 正文和 Tool schema 决定调用哪个工具。"""

    task = _require_str(state, "task")
    skill_text = _require_str(state, "skill_text")
    mcp_tools = _require_list(state, "mcp_tools")
    prompt = f"""你是一个 Skills runtime 的执行规划器。

请根据用户任务、已加载的 Skill 正文，以及 Host 从 MCP Server 发现的真实 Tool schema，
判断下一步应该调用哪个 MCP Tool，并生成工具参数。

约束：
- 只能选择 tool_schemas 中真实存在的工具。
- 参数必须符合对应工具的 input_schema。
- 只返回合法 JSON，不要输出 Markdown。

JSON 格式：
{{
  "tool": "<tool-name>",
  "arguments": {{}},
  "reason": "<简短原因>"
}}

用户任务：
{task}

Skill 正文：
{skill_text}

Tool schemas：
{json.dumps(mcp_tools, ensure_ascii=False, indent=2)}
"""
    model = ChatOllama(
        model=state.get("model_name", DEFAULT_MODEL),
        temperature=0,
    )
    response = model.invoke(prompt)
    raw_response = str(response.content)
    plan = _parse_json_response(raw_response)
    _validate_tool_call_plan(plan, mcp_tools)

    arguments = plan["arguments"]
    if not isinstance(arguments, dict):
        raise ValueError("tool call plan 的 arguments 必须是 JSON object")

    order_id = str(arguments.get("order_id", ""))
    return {
        "tool_call_plan": plan,
        "tool_call_raw_response": raw_response,
        "tool_name": str(plan["tool"]),
        "order_id": order_id,
        "trace": [
            {
                "node": "plan_tool_call",
                "model": state.get("model_name", DEFAULT_MODEL),
                "tool": plan["tool"],
                "arguments": arguments,
                "reason": plan.get("reason", ""),
            }
        ],
    }


def execute_mcp_tool_node(state: SkillGraphState) -> SkillGraphState:
    """执行节点：Host 只执行计划好的 MCP Tool call。"""

    plan = _require_dict(state, "tool_call_plan")
    tool_name = str(plan["tool"])
    arguments = plan["arguments"]
    if not isinstance(arguments, dict):
        raise ValueError("tool call plan 的 arguments 必须是 JSON object")

    tool_result = call_tool(
        server_path=SERVER_PATH,
        cwd=HERE,
        tool_name=tool_name,
        arguments=arguments,
    )

    return {
        "tool_name": tool_name,
        "tool_result": tool_result,
        "trace": [
            {
                "node": "execute_mcp_tool",
                "tool": tool_name,
                "arguments": arguments,
                "found": tool_result.get("found"),
            }
        ],
    }


def draft_report_node(state: SkillGraphState) -> SkillGraphState:
    """报告节点：把 MCP 结果整理成写入前草稿。"""

    tool_result = _require_dict(state, "tool_result")
    draft = _build_report_draft(tool_result)
    return {
        "report_draft": draft,
        "output_path": state.get("output_path", str(DEFAULT_OUTPUT_PATH)),
        "trace": [
            {
                "node": "draft_report",
                "chars": len(draft),
            }
        ],
    }


def wait_for_approval_node(state: SkillGraphState) -> SkillGraphState:
    """人工确认节点：写文件前暂停，让外部用 `Command(resume=...)` 恢复。"""

    selected_skill = _require_str(state, "selected_skill")
    output_path = _require_str(state, "output_path")
    report_draft = _require_str(state, "report_draft")
    decision = interrupt(
        {
            "question": "是否批准写入订单报告？回复批准/拒绝，并可附带原因。",
            "selected_skill": selected_skill,
            "output_path": output_path,
            "report_draft": report_draft,
        }
    )
    approval = str(decision)
    return {
        "approval": approval,
        "trace": [
            {
                "node": "wait_for_approval",
                "approval": approval,
            }
        ],
    }


def write_report_node(state: SkillGraphState) -> SkillGraphState:
    """写入节点：只有人工批准后才产生文件副作用。"""

    output_path = _require_str(state, "output_path")
    report_draft = _require_str(state, "report_draft")
    result = write_report(Path(output_path), report_draft)
    return {
        "write_result": result,
        "trace": [
            {
                "node": "write_report",
                "path": result["path"],
                "bytes": result["bytes"],
            }
        ],
    }


def final_answer_node(state: SkillGraphState) -> SkillGraphState:
    """收尾节点：把批准或拒绝路径整理成最终响应。"""

    write_result = state.get("write_result")
    if isinstance(write_result, dict) and write_result.get("written"):
        final_answer = f"已写入订单报告：{write_result['path']}"
    else:
        final_answer = f"已停止写入订单报告。人工意见：{state.get('approval', '未提供')}"

    return {
        "final_answer": final_answer,
        "trace": [
            {
                "node": "final_answer",
                "final_answer": final_answer,
            }
        ],
    }


def choose_after_approval(state: SkillGraphState) -> Literal["write_report", "final_answer"]:
    """根据人工意见决定是否执行写入节点。"""

    if _is_approved(state.get("approval", "")):
        return "write_report"
    return "final_answer"


def build_graph() -> StateGraph:
    """构造未编译的状态图，方便测试和复用。"""

    builder = StateGraph(SkillGraphState)
    builder.add_node("scan_skills", scan_skills_node)
    builder.add_node("route_skill", route_skill_node)
    builder.add_node("load_skill", load_skill_node)
    builder.add_node("discover_mcp_tools", discover_mcp_tools_node)
    builder.add_node("plan_tool_call", plan_tool_call_node)
    builder.add_node("execute_mcp_tool", execute_mcp_tool_node)
    builder.add_node("draft_report", draft_report_node)
    builder.add_node("wait_for_approval", wait_for_approval_node)
    builder.add_node("write_report", write_report_node)
    builder.add_node("final_answer", final_answer_node)

    builder.add_edge(START, "scan_skills")
    builder.add_edge("scan_skills", "route_skill")
    builder.add_edge("route_skill", "load_skill")
    builder.add_edge("load_skill", "discover_mcp_tools")
    builder.add_edge("discover_mcp_tools", "plan_tool_call")
    builder.add_edge("plan_tool_call", "execute_mcp_tool")
    builder.add_edge("execute_mcp_tool", "draft_report")
    builder.add_edge("draft_report", "wait_for_approval")
    builder.add_conditional_edges(
        "wait_for_approval",
        choose_after_approval,
        {
            "write_report": "write_report",
            "final_answer": "final_answer",
        },
    )
    builder.add_edge("write_report", "final_answer")
    builder.add_edge("final_answer", END)
    return builder


def compile_graph(checkpoint_path: Path = DEFAULT_CHECKPOINT_PATH):
    """编译状态图，并返回保持打开的 SQLite 连接。"""

    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    checkpointer = SqliteSaver(connection)
    graph = build_graph().compile(checkpointer=checkpointer)
    return graph, connection


def _build_report_draft(tool_result: dict[str, object]) -> str:
    if not tool_result.get("found"):
        return (
            "# 订单报告\n\n"
            f"- 订单号：{tool_result.get('order_id', '未知')}\n"
            "- 查询结果：未找到\n"
            "- 数据来源：stage11-order-report MCP get_order\n"
        )

    order = tool_result["order"]
    if not isinstance(order, dict):
        raise TypeError("MCP 工具返回的 order 字段不是对象")

    return (
        "# 订单报告\n\n"
        f"- 订单号：{order['order_id']}\n"
        f"- 状态：{order['status']}\n"
        f"- 商品：{order['product']}\n"
        f"- 金额：{order['amount']} {order['currency']}\n"
        "- 数据来源：stage11-order-report MCP get_order\n"
    )


def _is_approved(approval: str) -> bool:
    normalized = approval.strip().lower()
    reject_words = ("拒绝", "不批准", "不同意", "reject", "no")
    approve_words = ("批准", "同意", "approve", "yes", "y")

    if any(word in normalized for word in reject_words):
        return False
    return any(word in normalized for word in approve_words)


def _parse_json_response(text: str) -> dict[str, object]:
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("模型返回的工具调用计划必须是 JSON object")
    return parsed


def _validate_tool_call_plan(
    plan: dict[str, object],
    tools: list[dict[str, object]],
) -> None:
    tool_name = plan.get("tool")
    if not isinstance(tool_name, str) or not tool_name:
        raise ValueError("tool call plan 缺少 tool")

    known_tool_names = {str(tool["name"]) for tool in tools}
    if tool_name not in known_tool_names:
        raise ValueError(f"模型选择了不存在的 MCP Tool：{tool_name}")

    if not isinstance(plan.get("arguments"), dict):
        raise ValueError("tool call plan 缺少 arguments object")


def _require_str(state: SkillGraphState, key: str) -> str:
    value = state.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"State 缺少必需字符串字段：{key}")
    return value


def _require_dict(state: SkillGraphState, key: str) -> dict[str, Any]:
    value = state.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"State 缺少必需对象字段：{key}")
    return cast(dict[str, Any], value)


def _require_list(state: SkillGraphState, key: str) -> list[dict[str, Any]]:
    value = state.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"State 缺少必需列表字段：{key}")
    return cast(list[dict[str, Any]], value)
