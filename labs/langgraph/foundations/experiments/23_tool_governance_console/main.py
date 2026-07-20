import operator
from typing import Annotated, Any, Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt


MODEL_NAME = "qwen3-coder:30b"
MAX_RETRIES = 1


# 这个实验把工具动作分成三类：
# - readonly：可以直接执行的查询类动作；
# - high_risk_write：必须先经过人工审批的写操作；
# - unknown：无法自动判断的请求，直接转人工处理。
ActionType = Literal["readonly", "high_risk_write", "unknown"]
ToolStatus = Literal[
    "pending",
    "success",
    "failed",
    "denied",
    "ticket_created",
]
NextStep = Literal["execute_tool", "append_audit_log"]


class ToolGovernanceState(TypedDict, total=False):
    # 输入和规划结果。
    user_request: str
    action_type: ActionType
    planned_tool: str
    tool_args: dict[str, Any]

    # 审批、执行、错误和降级结果都进入 State，方便后续审计。
    approval: dict[str, Any]
    tool_result: dict[str, Any]
    tool_error: dict[str, Any]
    retry_count: int
    tool_status: ToolStatus
    manual_ticket: dict[str, Any]
    next_step: NextStep
    audit_log: Annotated[list[dict[str, Any]], operator.add]
    final_answer: str


# 以下工具都是本地 mock，不连接真实安全系统。
# 实验重点是图如何治理工具调用，而不是工具本身的业务能力。
def lookup_asset(asset_id: str) -> dict[str, Any]:
    return {
        "asset_id": asset_id,
        "owner": "security-platform",
        "criticality": "medium",
        "tags": ["internet-facing", "linux"],
    }


def query_exposure(domain: str) -> dict[str, Any]:
    if domain == "unstable.example.com":
        raise RuntimeError("exposure scanner timeout")

    return {
        "domain": domain,
        "open_ports": [80, 443],
        "public_services": ["nginx", "api-gateway"],
    }


def check_ip_reputation(ip: str) -> dict[str, Any]:
    return {
        "ip": ip,
        "reputation": "suspicious",
        "seen_in_feeds": ["demo-threat-feed"],
    }


def block_ip(ip: str, reason: str) -> dict[str, Any]:
    return {
        "ip": ip,
        "action": "blocked",
        "reason": reason,
        "firewall_rule_id": "fw-demo-1001",
    }


def add_account_to_watchlist(account_id: str, reason: str) -> dict[str, Any]:
    return {
        "account_id": account_id,
        "action": "watchlisted",
        "reason": reason,
        "watchlist_id": "wl-demo-2001",
    }


# 只读工具和写操作工具分开维护，策略节点会按 action_type 检查。
READONLY_TOOLS = {
    "lookup_asset": lookup_asset,
    "query_exposure": query_exposure,
    "check_ip_reputation": check_ip_reputation,
}

WRITE_TOOLS = {
    "block_ip": block_ip,
    "add_account_to_watchlist": add_account_to_watchlist,
}

ALL_TOOLS = {
    **READONLY_TOOLS,
    **WRITE_TOOLS,
}

ALLOWED_TOOLS_BY_ACTION_TYPE = {
    "readonly": READONLY_TOOLS,
    "high_risk_write": WRITE_TOOLS,
}


def classify_request(state: ToolGovernanceState) -> dict[str, Any]:
    request = state.get("user_request", "")

    # 这里用简单关键词分类，方便读者把注意力放在 LangGraph 控制流上。
    if "封禁" in request or "加入观察名单" in request:
        action_type: ActionType = "high_risk_write"
    elif "查询" in request or "扫描" in request or "信誉" in request:
        action_type = "readonly"
    else:
        action_type = "unknown"

    print(f"[classify_request] action_type={action_type}")
    return {"action_type": action_type}


def plan_action(state: ToolGovernanceState) -> dict[str, Any]:
    request = state.get("user_request", "")

    # planner 把自然语言请求变成 planned_tool + tool_args。
    # 真实项目里这里可以替换成模型规划、规则引擎或表单解析。
    if "错误示例" in request:
        planned_tool = "block_ip"
        tool_args = {"ip": "203.0.113.77", "reason": "演示策略节点拒绝越权工具"}
    elif "unstable.example.com" in request:
        planned_tool = "query_exposure"
        tool_args = {"domain": "unstable.example.com"}
    elif "example.com" in request:
        planned_tool = "query_exposure"
        tool_args = {"domain": "example.com"}
    elif "资产" in request:
        planned_tool = "lookup_asset"
        tool_args = {"asset_id": "asset-001"}
    elif "IP" in request or "ip" in request:
        planned_tool = "block_ip"
        tool_args = {"ip": "192.0.2.10", "reason": "用户请求封禁可疑来源"}
    elif "账号" in request or "account" in request:
        planned_tool = "add_account_to_watchlist"
        tool_args = {"account_id": "user-123", "reason": "疑似撞库风险"}
    else:
        planned_tool = "manual_review"
        tool_args = {"summary": request}

    print(f"[plan_action] planned_tool={planned_tool} args={tool_args}")
    return {
        "planned_tool": planned_tool,
        "tool_args": tool_args,
        "retry_count": 0,
        "tool_status": "pending",
        "tool_result": {},
        "tool_error": {},
        "manual_ticket": {},
    }


def create_manual_ticket(state: ToolGovernanceState) -> dict[str, Any]:
    # 降级路径：不继续硬跑工具，而是把上下文整理成人工处理工单。
    return {
        "ticket_id": "SEC-MANUAL-001",
        "summary": state.get("user_request", ""),
        "planned_tool": state.get("planned_tool"),
        "tool_args": state.get("tool_args", {}),
        "last_error": state.get("tool_error", {}),
    }


def enforce_tool_policy(state: ToolGovernanceState) -> dict[str, Any]:
    action_type = state.get("action_type", "unknown")
    planned_tool = state.get("planned_tool", "")
    allowed_tools = ALLOWED_TOOLS_BY_ACTION_TYPE.get(action_type, {})

    # 工具治理的第一道闸：规划出的工具必须属于当前动作类型允许的集合。
    if planned_tool in allowed_tools:
        print(f"[enforce_tool_policy] allowed: {planned_tool}")
        return {"tool_status": "pending", "tool_error": {}}

    if action_type == "unknown":
        ticket = create_manual_ticket(state)
        print("[enforce_tool_policy] unknown request, create manual ticket")
        return {
            "tool_status": "ticket_created",
            "manual_ticket": ticket,
            "tool_error": {
                "type": "unknown_action_type",
                "tool": planned_tool,
            },
        }

    print(f"[enforce_tool_policy] tool_not_allowed: {planned_tool}")
    return {
        "tool_status": "failed",
        "tool_error": {
            "type": "tool_not_allowed",
            "tool": planned_tool,
            "action_type": action_type,
            "allowed_tools": sorted(allowed_tools),
        },
    }


def approval_gate(state: ToolGovernanceState) -> dict[str, Any]:
    # 策略节点已经拒绝或转人工的请求，不再进入审批和执行。
    tool_status = state.get("tool_status", "pending")
    if tool_status != "pending":
        print(f"[approval_gate] skip because status={tool_status}")
        return {}

    # 只读动作不需要人工审批，但仍记录一次 skipped，方便审计链完整。
    if state.get("action_type") == "readonly":
        print("[approval_gate] readonly action, no approval needed")
        return {"approval": {"decision": "skipped", "reason": "readonly_action"}}

    # 高风险写操作在这里真正暂停图，等待外部用 Command(resume=...) 恢复。
    approval_result = interrupt(
        {
            "question": "这个高风险工具动作是否允许执行？",
            "planned_tool": state.get("planned_tool", ""),
            "tool_args": state.get("tool_args", {}),
            "expected_resume_shape": {
                "decision": "approved 或 denied",
                "operator": "审批人",
                "reason": "审批原因",
            },
        }
    )

    # approval_result 是外部 Command(resume=...) 传回来的审批结果。
    print(f"[approval_gate] approval_result={approval_result}")
    if approval_result.get("decision") == "approved":
        return {"approval": approval_result}

    return {
        "approval": approval_result,
        "tool_status": "denied",
        "tool_result": {},
        "tool_error": {},
    }


def route_after_approval(state: ToolGovernanceState) -> str:
    # pending 表示策略通过且审批通过/跳过，可以进入工具执行。
    if state.get("tool_status") == "pending":
        return "execute_tool"
    return "append_audit_log"


def execute_tool(state: ToolGovernanceState) -> dict[str, Any]:
    planned_tool = state.get("planned_tool", "")
    tool_args = state.get("tool_args", {})

    try:
        # 工具异常在节点内捕获并写入 State，避免整张图直接崩掉。
        print(f"[execute_tool] run {planned_tool}({tool_args})")
        result = ALL_TOOLS[planned_tool](**tool_args)
        return {
            "tool_status": "success",
            "tool_result": result,
            "tool_error": {},
        }
    except Exception as exc:
        print(f"[execute_tool] tool_failed: {exc}")
        return {
            "tool_status": "failed",
            "tool_error": {
                "type": "tool_runtime_error",
                "tool": planned_tool,
                "message": str(exc),
            },
        }


def handle_tool_error(state: ToolGovernanceState) -> dict[str, Any]:
    # 这个节点不修复错误，只把“错误已进入 State”这件事显式呈现出来。
    tool_status = state.get("tool_status", "pending")
    if tool_status == "success":
        print("[handle_tool_error] no error")
    else:
        print(f"[handle_tool_error] captured error: {state.get('tool_error', {})}")

    return {"tool_status": tool_status}


def retry_or_fallback(state: ToolGovernanceState) -> dict[str, Any]:
    if state.get("tool_status") == "success":
        print("[retry_or_fallback] success, go audit")
        return {"next_step": "append_audit_log"}

    # 本实验只重试一次，避免教学代码陷入复杂的退避、限流和熔断策略。
    retry_count = state.get("retry_count", 0)
    if retry_count < MAX_RETRIES:
        next_retry_count = retry_count + 1
        print(f"[retry_or_fallback] retry_count={next_retry_count}")
        return {
            "retry_count": next_retry_count,
            "next_step": "execute_tool",
        }

    ticket = create_manual_ticket(state)
    print(f"[retry_or_fallback] fallback ticket_id={ticket['ticket_id']}")
    return {
        "tool_status": "ticket_created",
        "manual_ticket": ticket,
        "next_step": "append_audit_log",
    }


def route_after_retry_or_fallback(state: ToolGovernanceState) -> str:
    # 只有 retry 回到 execute_tool，其余成功/降级路径都进入审计。
    return state.get("next_step", "append_audit_log")


def append_audit_log(state: ToolGovernanceState) -> dict[str, Any]:
    # 每条路径最终都汇入审计日志：成功、拒绝、越权、失败降级都可追踪。
    audit_item = {
        "request": state.get("user_request", ""),
        "action_type": state.get("action_type"),
        "planned_tool": state.get("planned_tool"),
        "tool_args": state.get("tool_args", {}),
        "approval": state.get("approval", {}),
        "tool_status": state.get("tool_status"),
        "tool_result": state.get("tool_result", {}),
        "tool_error": state.get("tool_error", {}),
        "manual_ticket": state.get("manual_ticket", {}),
        "retry_count": state.get("retry_count", 0),
    }

    print(f"[append_audit_log] status={audit_item['tool_status']}")
    return {"audit_log": [audit_item]}


def final_response(state: ToolGovernanceState) -> dict[str, Any]:
    print(f"[final_response] call local Ollama: {MODEL_NAME}")

    # 模型只负责基于最终 State 写回复，不参与工具选择和权限判断。
    model = ChatOllama(model=MODEL_NAME, temperature=0)
    prompt = f"""
你是安全运维助手。请根据下面的 LangGraph State 写一段简短中文回复。

要求：
- 只基于 State，不要编造真实系统动作。
- 如果 tool_status=denied，明确说明未执行写操作。
- 如果 tool_status=ticket_created，说明已转人工处理。
- 如果 tool_error.type=tool_not_allowed，明确说明这是策略节点拦截，工具没有被执行，不要说“尝试执行失败”。
- 如果有 tool_error，说明错误已被记录，没有让流程崩溃。
- 控制在 100 字以内。

State:
user_request: {state.get("user_request")}
action_type: {state.get("action_type")}
planned_tool: {state.get("planned_tool")}
tool_args: {state.get("tool_args")}
approval: {state.get("approval", {})}
tool_status: {state.get("tool_status")}
tool_result: {state.get("tool_result", {})}
tool_error: {state.get("tool_error", {})}
manual_ticket: {state.get("manual_ticket", {})}
retry_count: {state.get("retry_count", 0)}
"""

    response = model.invoke(prompt)
    return {"final_answer": str(response.content).strip()}


def build_graph(use_checkpointer: bool = True):
    builder = StateGraph(ToolGovernanceState)

    # 顶层图保持为一条治理流水线：
    # 分类 -> 规划 -> 策略 -> 审批 -> 执行 -> 错误处理 -> 重试/降级 -> 审计 -> 回复。
    builder.add_node("classify_request", classify_request)
    builder.add_node("plan_action", plan_action)
    builder.add_node("enforce_tool_policy", enforce_tool_policy)
    builder.add_node("approval_gate", approval_gate)
    builder.add_node("execute_tool", execute_tool)
    builder.add_node("handle_tool_error", handle_tool_error)
    builder.add_node("retry_or_fallback", retry_or_fallback)
    builder.add_node("append_audit_log", append_audit_log)
    builder.add_node("final_response", final_response)

    builder.add_edge(START, "classify_request")
    builder.add_edge("classify_request", "plan_action")
    builder.add_edge("plan_action", "enforce_tool_policy")
    builder.add_edge("enforce_tool_policy", "approval_gate")

    # 审批节点只有两个出口：可以执行，或直接进入审计。
    builder.add_conditional_edges(
        "approval_gate",
        route_after_approval,
        {
            "execute_tool": "execute_tool",
            "append_audit_log": "append_audit_log",
        },
    )
    builder.add_edge("execute_tool", "handle_tool_error")
    builder.add_edge("handle_tool_error", "retry_or_fallback")

    # 重试/降级节点也只有两个出口：重试执行，或进入审计。
    builder.add_conditional_edges(
        "retry_or_fallback",
        route_after_retry_or_fallback,
        {
            "execute_tool": "execute_tool",
            "append_audit_log": "append_audit_log",
        },
    )
    builder.add_edge("append_audit_log", "final_response")
    builder.add_edge("final_response", END)

    # 命令行实验需要 MemorySaver 才能演示 interrupt 后用 Command(resume=...) 恢复。
    if use_checkpointer:
        return builder.compile(checkpointer=MemorySaver())

    return builder.compile()


def print_case_header(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def print_case_result(state: ToolGovernanceState) -> None:
    print("\n--- 最终 State 摘要 ---")
    print(f"tool_status: {state.get('tool_status')}")
    print(f"planned_tool: {state.get('planned_tool')}")
    print(f"tool_result: {state.get('tool_result', {})}")
    print(f"tool_error: {state.get('tool_error', {})}")
    print(f"manual_ticket: {state.get('manual_ticket', {})}")
    print(f"audit_log: {state.get('audit_log', [])}")
    print(f"final_answer: {state.get('final_answer')}")


def run_normal_case(graph: Any, title: str, request: str, thread_id: str) -> None:
    print_case_header(title)
    state = graph.invoke(
        {"user_request": request},
        config={"configurable": {"thread_id": thread_id}},
    )
    print_case_result(state)


def start_approval_case(
    graph: Any,
    title: str,
    request: str,
    thread_id: str,
) -> None:
    config = {"configurable": {"thread_id": thread_id}}

    print_case_header(title)
    print("--- 第一次 invoke：运行到 interrupt，等待人工审批 ---")
    first_result = graph.invoke({"user_request": request}, config=config)
    print("__interrupt__:", first_result.get("__interrupt__"))


def resume_approval_case(
    graph: Any,
    title: str,
    approval: dict[str, Any],
    thread_id: str,
) -> None:
    config = {"configurable": {"thread_id": thread_id}}

    print_case_header(title)
    print("--- 第二次 invoke：Command(resume=...) 恢复执行 ---")
    print("resume:", approval)
    final_state = graph.invoke(Command(resume=approval), config=config)
    print_case_result(final_state)


def main() -> None:
    graph = build_graph()

    run_normal_case(
        graph,
        "路径 1：只读查询成功",
        "请查询 example.com 的暴露服务",
        "case-readonly-success",
    )

    start_approval_case(
        graph,
        "路径 2A：高风险写操作，先暂停等待审批",
        "请封禁这个 IP",
        "case-write-approved",
    )
    resume_approval_case(
        graph,
        "路径 2B：人工批准，恢复后执行工具",
        {"decision": "approved", "operator": "alice", "reason": "已确认恶意来源"},
        "case-write-approved",
    )

    start_approval_case(
        graph,
        "路径 3A：高风险写操作，先暂停等待审批",
        "请把这个账号加入观察名单",
        "case-write-denied",
    )
    resume_approval_case(
        graph,
        "路径 3B：人工拒绝，恢复后不执行工具",
        {"decision": "denied", "operator": "alice", "reason": "证据不足"},
        "case-write-denied",
    )

    run_normal_case(
        graph,
        "路径 4：工具失败，重试后降级到人工工单",
        "请查询 unstable.example.com 的暴露服务",
        "case-failure-fallback",
    )

    run_normal_case(
        graph,
        "路径 5：工具不属于当前动作允许集合，被图拒绝执行",
        "请查询错误示例",
        "case-tool-not-allowed",
    )


if __name__ == "__main__":
    main()
