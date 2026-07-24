"""用受约束的 Handoff 处理一个客服工单。

实验重点：没有中心 Supervisor 时，当前 Agent 根据自己的职责边界提出移交意图，
程序校验合法目标和循环次数后，再用 Command 执行控制权移交。
"""

from __future__ import annotations

import operator
from typing import Annotated, Literal

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


HandoffTarget = Literal[
    "refund_agent",
    "technical_agent",
    "human_agent",
    "finish",
    "failed",
]

MAX_HANDOFF_COUNT = 6
MODEL_NAME = "qwen3-coder:30b"

# 多个 Agent 共用同一个模型客户端；各节点只绑定自己的结构化输出格式。
model = ChatOllama(model=MODEL_NAME, temperature=0)


class HandoffDecision(BaseModel):
    """Agent 提出的移交意图；它还不是可以直接执行的图跳转。"""

    target: HandoffTarget
    reason: str = Field(min_length=1)


class RefundResult(BaseModel):
    """退款 Agent 的业务判断和移交意图。"""

    summary: str = Field(min_length=10)  # 对用户退款诉求和当前处理背景的简短概括。
    policy_status: Literal[
        "needs_technical_evidence",
        "needs_human_approval",
        "approved",
        "rejected",
    ]  # 退款政策状态，用来说明当前是缺证据、需人工审批、已批准还是已拒绝。
    decision: str = Field(min_length=10)  # 退款 Agent 给出的政策判断说明。
    handoff: HandoffDecision  # 退款 Agent 建议把控制权交给谁，以及为什么。


class TechnicalResult(BaseModel):
    """技术 Agent 的故障判断和移交意图。"""

    diagnosis: str = Field(min_length=10)  # 技术 Agent 对故障现象的诊断结论。
    solved_by_troubleshooting: bool  # 是否已经通过重启、重配网等常规排障解决。
    defect_likely: bool  # 是否疑似商品自身故障；会影响退款 Agent 是否进入例外审批。
    evidence: list[str] = Field(min_length=1)  # 支撑技术判断的关键证据列表。
    handoff: HandoffDecision  # 技术 Agent 建议把控制权交给谁，以及为什么。


class HumanReviewResult(BaseModel):
    """人工升级 Agent 的最终处理意见和移交意图。"""

    final_decision: Literal["approve_refund", "reject_refund", "need_more_info"]  # 人工审批的最终结论。
    explanation: str = Field(min_length=10)  # 给出最终结论的业务理由。
    handoff: HandoffDecision  # 人工升级 Agent 建议把控制权交给谁，以及为什么。


class SupportState(TypedDict, total=False):
    customer_message: str  # 用户提交的原始客服诉求。
    order_days: int  # 下单距今天数，用于退款政策判断。
    product_name: str  # 涉及的商品名称，方便各 Agent 保持上下文一致。
    amount: int  # 订单金额，人工升级时用于评估处理风险。
    refund_case: dict  # 退款 Agent 写入的政策判断。
    technical_diagnosis: dict  # 技术 Agent 写入的故障诊断结果。
    human_review: dict  # 人工升级 Agent 写入的最终审核结果。
    current_agent: str  # 当前获得控制权的 Agent 或收尾节点名称。
    handoff_count: int  # 已经发生的移交次数，用于限制无限循环。
    max_handoff_count: int  # 本次运行允许的最大移交次数。
    handoff_reason: str  # 最近一次移交的原因。
    handoff_history: Annotated[list[dict], operator.add]  # 所有移交记录。
    trace: Annotated[list[str], operator.add]  # 简短执行轨迹。
    final_status: str  # 流程最终状态，例如 success 或 handoff_rejected。


# 程序定义的移交白名单：Agent 可以提出目标，但只能移交给这里允许的节点。
ALLOWED_HANDOFFS: dict[str, set[HandoffTarget]] = {
    # 退款 Agent 不能诊断故障；缺少故障证据时交给技术 Agent。
    # 如果已经具备证据，它可以直接结束，或把政策例外交给人工升级 Agent。
    "refund_agent": {"technical_agent", "human_agent", "finish"},
    # 技术 Agent 只负责诊断，不负责退款；诊断完成后交回退款 Agent。
    "technical_agent": {"refund_agent"},
    # 人工升级 Agent 负责最终例外审批，审批后结束。
    "human_agent": {"finish"},
}


def validate_and_execute_handoff(
    state: SupportState,
    current_agent: str,
    decision: HandoffDecision,
    update: dict,
) -> Command[HandoffTarget]:
    """校验移交目标、记录移交过程，并构造下一步 Command。

    Agent 负责提出 decision；这个函数负责把模型意图放进程序规定的业务边界内。
    """

    # 每次调用这个函数都代表一次新的控制权移交，先把次数加一。
    # 这里从 State 读取上限，允许调用方针对某一次工单覆盖默认配置。
    next_count = state.get("handoff_count", 0) + 1
    max_count = state.get("max_handoff_count", MAX_HANDOFF_COUNT)

    # 当前 Agent 能移交给哪些节点由程序白名单决定，而不是由模型自由决定。
    allowed = ALLOWED_HANDOFFS.get(current_agent, set())

    # 先检查目标是否合法，再检查是否超过最大移交次数。
    # 任一检查失败都不能让模型直接控制图跳转，而要进入统一的失败节点。
    violation = None
    if decision.target not in allowed:
        violation = f"{current_agent} 不允许移交给 {decision.target}"
    elif next_count > max_count:
        violation = f"Handoff 次数 {next_count} 超过上限 {max_count}"

    # 默认沿用模型提出的目标；如果校验失败，则把目标改写为 failed。
    # 这样既保留失败原因，又确保后续 Command 不会执行越权跳转。
    target: HandoffTarget = decision.target
    if violation:
        target = "failed"
        update["final_status"] = "handoff_rejected"
        update["handoff_reason"] = violation

    # 将本次移交整理成可审计记录，后续通过 handoff_history 查看完整过程。
    record = {
        "from": current_agent,
        "to": target,
        "reason": decision.reason if not violation else violation,
        "count": next_count,
    }
    print(f"[{current_agent}] handoff -> {target}: {record['reason']}")

    # Command 同时完成两件事：更新共享 State，并把控制权交给目标节点。
    # goto 使用经过校验后的 target，而不是未经检查的 decision.target。
    return Command(
        update={
            **update,
            "current_agent": target,
            "handoff_count": next_count,
            "handoff_reason": record["reason"],
            "handoff_history": [record],
            "trace": [f"{current_agent} -> {target}"],
        },
        goto=target,
    )


def refund_agent(state: SupportState) -> Command[HandoffTarget]:
    """处理退款政策；需要故障证据或人工审批时主动移交。"""

    technical_diagnosis = state.get("technical_diagnosis")
    refund_model = model.with_structured_output(RefundResult)
    result = RefundResult.model_validate(
        refund_model.invoke([
            (
                "system",
                "你是退款 Agent，只负责退款政策判断，不负责技术故障诊断。"
                "如果还没有 technical_diagnosis，handoff.target 必须是 technical_agent。"
                "如果 technical_diagnosis.defect_likely 为 true 且 order_days 大于 7，说明是政策例外，handoff.target 必须是 human_agent。"
                "如果可以直接按政策处理，handoff.target 才能是 finish。只返回结构化结果。",
            ),
            (
                "human",
                f"用户诉求：{state.get('customer_message', '')}\n"
                f"商品：{state.get('product_name', '')}\n"
                f"订单天数：{state.get('order_days', 0)}\n"
                f"订单金额：{state.get('amount', 0)}\n"
                f"技术诊断：{technical_diagnosis}\n"
                "请给出退款政策判断和下一步移交意图。",
            ),
        ])
    )

    refund_case = result.model_dump(exclude={"handoff"})
    # 关键业务边界由程序兜底：没有技术诊断时，退款 Agent 不能跳过技术 Agent。
    # 如果已确认疑似故障但超过普通退货期，也不能直接批准，必须交给人工升级。
    decision = result.handoff
    if not isinstance(technical_diagnosis, dict):
        refund_case["policy_status"] = "needs_technical_evidence"
        decision = HandoffDecision(
            target="technical_agent",
            reason="退款判断缺少故障证据，需要技术 Agent 先确认问题性质",
        )
    elif technical_diagnosis.get("defect_likely") and state.get("order_days", 0) > 7:
        refund_case["policy_status"] = "needs_human_approval"
        decision = HandoffDecision(
            target="human_agent",
            reason="技术诊断确认疑似商品故障，但订单已超过普通退货期，需要人工审批",
        )

    print("\n--- refund_agent 退款判断 ---")
    print(f"用户诉求：{state.get('customer_message', '')}")
    print(f"订单天数：{state.get('order_days', 0)}")
    print(f"已有技术诊断：{technical_diagnosis}")
    print(f"政策状态：{refund_case['policy_status']}")
    print(f"退款判断：{refund_case['decision']}")
    print(f"下一步移交：{decision.target}，原因：{decision.reason}")
    print("--- refund_agent 判断结束 ---\n")

    return validate_and_execute_handoff(
        state,
        "refund_agent",
        decision,
        {"refund_case": refund_case},
    )

def technical_agent(state: SupportState) -> Command[HandoffTarget]:
    """处理设备故障诊断；诊断完成后交回退款 Agent。"""

    refund_case = state.get("refund_case")
    if not isinstance(refund_case, dict):
        reason = "缺少 refund_case，技术诊断无法开始"
        print(f"[technical_agent] failed: {reason}")
        return Command(
            update={
                "current_agent": "failed",
                "handoff_reason": reason,
                "trace": ["technical_agent -> failed"],
                "final_status": "missing_prerequisite",
            },
            goto="failed",
        )

    tech_model = model.with_structured_output(TechnicalResult)
    result = TechnicalResult.model_validate(
        tech_model.invoke([
            (
                "system",
                "你是技术 Agent，只负责判断商品是否存在故障，不负责退款审批。"
                "诊断完成后 handoff.target 必须是 refund_agent，把故障证据交回退款 Agent。"
                "只返回结构化结果。",
            ),
            (
                "human",
                f"用户诉求：{state.get('customer_message', '')}\n"
                f"商品：{state.get('product_name', '')}\n"
                f"退款判断：{refund_case}\n"
                "请判断是否疑似商品故障，并说明证据。",
            ),
        ])
    )

    print("\n--- technical_agent 技术诊断 ---")
    print(f"诊断商品：{state.get('product_name', '')}")
    print(f"诊断结论：{result.diagnosis}")
    print(f"是否已通过排障解决：{result.solved_by_troubleshooting}")
    print(f"是否疑似商品故障：{result.defect_likely}")
    print(f"故障证据：{result.evidence}")
    print(f"下一步移交：{result.handoff.target}，原因：{result.handoff.reason}")
    print("--- technical_agent 诊断结束 ---\n")

    return validate_and_execute_handoff(
        state,
        "technical_agent",
        result.handoff,
        {"technical_diagnosis": result.model_dump(exclude={"handoff"})},
    )


def human_agent(state: SupportState) -> Command[HandoffTarget]:
    """处理超过普通政策范围的人工升级审批。"""

    refund_case = state.get("refund_case")
    technical_diagnosis = state.get("technical_diagnosis")
    if not isinstance(refund_case, dict) or not isinstance(technical_diagnosis, dict):
        reason = "缺少退款判断或技术诊断，人工审批无法开始"
        print(f"[human_agent] failed: {reason}")
        return Command(
            update={
                "current_agent": "failed",
                "handoff_reason": reason,
                "trace": ["human_agent -> failed"],
                "final_status": "missing_prerequisite",
            },
            goto="failed",
        )

    human_model = model.with_structured_output(HumanReviewResult)
    result = HumanReviewResult.model_validate(
        human_model.invoke([
            (
                "system",
                "你是人工升级 Agent，负责处理普通退款政策之外的例外审批。"
                "如果技术诊断显示疑似商品故障，且用户诉求合理，倾向批准退款。"
                "审批完成后 handoff.target 必须是 finish。只返回结构化结果。",
            ),
            (
                "human",
                f"用户诉求：{state.get('customer_message', '')}\n"
                f"订单天数：{state.get('order_days', 0)}\n"
                f"订单金额：{state.get('amount', 0)}\n"
                f"退款判断：{refund_case}\n"
                f"技术诊断：{technical_diagnosis}\n"
                "请给出最终处理意见。",
            ),
        ])
    )

    print("\n--- human_agent 人工升级审批 ---")
    print(f"升级原因：{state.get('handoff_reason', '')}")
    print(f"退款判断：{refund_case.get('decision', '')}")
    print(f"技术证据：{technical_diagnosis.get('evidence', [])}")
    print(f"最终决定：{result.final_decision}")
    print(f"处理说明：{result.explanation}")
    print(f"下一步移交：{result.handoff.target}，原因：{result.handoff.reason}")
    print("--- human_agent 审批结束 ---\n")

    update = {
        "human_review": result.model_dump(exclude={"handoff"}),
        "final_status": "success",
    }
    return validate_and_execute_handoff(
        state,
        "human_agent",
        result.handoff,
        update,
    )


def finish(state: SupportState) -> SupportState:
    print("[finish] Handoff 流程正常结束")
    return {"trace": ["finish"], "final_status": "success"}


def failed(state: SupportState) -> SupportState:
    print(f"[failed] Handoff 流程终止：{state.get('handoff_reason', '未知原因')}")
    return {"trace": ["failed"]}


def build_graph():
    builder = StateGraph(SupportState)
    builder.add_node("refund_agent", refund_agent)
    builder.add_node("technical_agent", technical_agent)
    builder.add_node("human_agent", human_agent)
    builder.add_node("finish", finish)
    builder.add_node("failed", failed)
    builder.add_edge(START, "refund_agent")
    builder.add_edge("finish", END)
    builder.add_edge("failed", END)
    return builder.compile(name="Handoff Support Ticket")


def main() -> None:
    graph = build_graph()
    initial_state: SupportState = {
        "customer_message": (
            "我买的智能门锁第15天开始无法连接App，重启和重新配网都失败。"
            "我现在想退货退款，但普通退货期好像已经过了。"
        ),
        "product_name": "智能门锁",
        "order_days": 15,
        "amount": 1299,
        "max_handoff_count": MAX_HANDOFF_COUNT,
    }
    result = graph.invoke(initial_state)

    print("\n=== Handoff 历史 ===")
    for item in result.get("handoff_history", []):
        print(item)

    print("\n=== 最终状态 ===")
    print(result.get("final_status"))
    print(result.get("human_review", result.get("refund_case", {})))


if __name__ == "__main__":
    main()
