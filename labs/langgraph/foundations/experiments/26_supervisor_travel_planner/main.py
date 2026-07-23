"""用 Supervisor 多 Agent 完成一个最小旅行规划任务。

实验重点：三个专业子Agent 不直接互相跳转，所有下一步都由 Supervisor 决定。
"""

from __future__ import annotations

import argparse
import json
import operator
from collections.abc import Mapping
from typing import Annotated, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field
from typing_extensions import TypedDict


MODEL_NAME = "qwen3-coder:30b"

NextStep = Literal[
    "attractions_agent",
    "budget_constraint_agent",
    "optimizer_agent",
    "finish",
]


class AttractionPlan(BaseModel):
    """景点规划子Agent的结构化输出。"""

    places: list[str] = Field(
        min_length=3,
        description="至少 3 个推荐的主要景点",
    )
    daily_plan: list[str] = Field(
        min_length=5,
        description="覆盖完整 5 天的每日行程，每天一条",
    )
    estimated_cost: int = Field(
        ge=1,
        description="当前方案的预计总花费，单位为人民币，必须大于 0",
    )


class BudgetConstraints(BaseModel):
    """预算约束提取子Agent的结构化输出。"""

    budget_limit: int = Field(description="用户给出的预算上限，单位为人民币")
    pace: str = Field(description="用户希望的行程节奏")
    constraints: list[str] = Field(description="从需求中提取的预算和舒适度约束")


class OptimizedPlan(BaseModel):
    """行程优化子Agent的结构化输出。"""

    final_plan: str = Field(
        min_length=100,
        description="完整的最终旅行方案，必须包含 5 天每日安排、预算说明和老人出行建议",
    )
    changes: list[str] = Field(
        min_length=1,
        description="至少 1 条相对原方案做出的关键调整",
    )


class SupervisorDecision(BaseModel):
    """Supervisor 每次只能选择一个下一步。"""

    next_step: NextStep
    reason: str = Field(description="选择下一步的简短原因")


class TravelState(TypedDict, total=False):
    request: str  # 用户的原始旅行需求，所有专业子Agent都可以读取。
    attraction_plan: dict  # 景点规划子Agent产出的初步景点和每日行程。
    budget_constraints: dict  # 预算约束子Agent提取出的预算与舒适度约束。
    optimized_plan: dict  # 行程优化子Agent生成的最终旅行方案。
    completed_agents: Annotated[list[str], operator.add]  # 已完成的子Agent名称，用 reducer累积记录。
    decisions: Annotated[list[str], operator.add]  # Supervisor的调度决定，用于回看控制过程。
    trace: Annotated[list[str], operator.add]  # 实验运行轨迹，用 reducer按执行顺序保留记录。
    next_step: str  # Supervisor选择的下一个图节点，由条件边读取。


model = ChatOllama(model=MODEL_NAME, temperature=0)


def require_request(state: Mapping[str, object]) -> str:
    """读取所有专业子Agent都依赖的用户需求。"""
    request = state.get("request")
    if not isinstance(request, str):
        raise RuntimeError("TravelState缺少 request，无法继续执行旅行规划。")
    return request


def require_state_dict(
    state: Mapping[str, object],
    field: Literal["attraction_plan", "budget_constraints", "optimized_plan"],
) -> dict[str, object]:
    """读取已经由前置子Agent写入的结构化结果。"""
    value = state.get(field)
    if not isinstance(value, dict):
        raise RuntimeError(f"TravelState缺少 {field}，无法执行当前节点。")
    return {key: item for key, item in value.items() if isinstance(key, str)}


def supervisor(state: TravelState) -> TravelState:
    """由中心 Agent 根据当前 State 选择下一个专业子Agent。

    这个节点不负责规划景点、分析预算或编写最终方案，它只做一件事：
    根据当前已经完成的工作，决定下一步把任务交给谁。

    一次调用的完整过程是：

    1. 读取 completed_agents，了解哪些专业子Agent已经完成。
    2. 根据前置条件生成合法候选，防止跳过必要步骤。
    3. 把用户需求、当前 State和候选列表交给模型。
    4. 把模型输出解析成 SupervisorDecision，并检查选择是否在候选列表中。
    5. 把 next_step写回 State，条件边会根据它跳转到下一个节点。

    所以，Supervisor的“调度权”体现为：专业子Agent不直接连接彼此，
    它们完成工作后都回到这里，由这个节点决定下一步。
    """

    # completed_agents由各个专业子Agent写入，并通过列表 reducer不断累积。
    # 第一次进入 Supervisor时这个字段还不存在，因此使用空列表。
    completed = state.get("completed_agents", [])

    # 这里先由程序确定“哪些 Agent现在可以被调用”，再让模型在合法候选中选择。
    # 这不是替代 Supervisor，而是给模型划定流程边界：
    # - 景点规划和预算约束提取彼此独立，可以先后执行；
    # - 行程优化必须等前两个结果都准备好；
    # - 所有专业子Agent完成后才能进入 finish。
    if "attractions_agent" not in completed and "budget_constraint_agent" not in completed:
        candidates = ["attractions_agent", "budget_constraint_agent"]
    elif "attractions_agent" not in completed:
        candidates = ["attractions_agent"]
    elif "budget_constraint_agent" not in completed:
        candidates = ["budget_constraint_agent"]
    elif "optimizer_agent" not in completed:
        candidates = ["optimizer_agent"]
    else:
        candidates = ["finish"]

    # 所有 Supervisor决策都必须带着原始用户需求，避免模型只根据局部结果做判断。
    request = require_request(state)

    # SystemMessage定义 Supervisor的职责；HumanMessage提供这一次调度所需的数据。
    # 候选列表会明确告诉模型：它只能从当前合法的下一步中选择。
    prompt = [
        SystemMessage(
            content=(
                "你是旅行规划 Supervisor，负责统一调度三个专业子Agent。"
                "你不负责亲自规划行程，只负责根据当前状态选择下一步。"
                "角色职责必须严格区分："
                "attractions_agent只负责规划景点和初步行程；"
                "budget_constraint_agent只负责从用户需求提取预算、节奏和舒适度约束，"
                "不负责计算实际费用，也不负责判断是否超预算；"
                "optimizer_agent负责综合前两个结果生成最终方案。"
                "必须从候选列表中选择一个 next_step。景点规划和预算约束提取可以先后执行，"
                "但只有两个都完成后才能调用行程优化子Agent。"
            )
        ),
        HumanMessage(
            content=(
                f"用户需求：{request}\n"
                f"已经完成的子Agent：{completed}\n"
                f"当前状态：{json.dumps(state, ensure_ascii=False, default=str)}\n"
                f"候选 next_step：{candidates}\n"
                "请只根据当前 State和上述职责选择下一步，并用一句话说明原因。"
                "不要声称尚未执行的预算计算或超预算判断已经完成。"
            )
        ),
    ]

    # 第一步：得到一个仍然可以调用模型的对象，
    # 但它被要求按照SupervisorDecision的字段格式返回结果。
    # 此时还没有真正调用模型。
    decision_model = model.with_structured_output(SupervisorDecision)

    # 第二步：把提示词发送给模型，得到模型返回的结果。
    decision_result = decision_model.invoke(prompt)

    # 第三步：把结果转换成 SupervisorDecision对象，后面可以直接读取它的字段。
    decision = SupervisorDecision.model_validate(decision_result)

    # 模型即使收到候选列表，也可能返回不在候选范围内的节点。
    # 因此这里做一次白名单检查：合法选择照常使用，非法选择采用当前候选的
    # 第一个值，并把修正原因记录下来。这样模型不会把图路由到错误节点。
    next_step = decision.next_step if decision.next_step in candidates else candidates[0]
    reason = decision.reason
    if decision.next_step not in candidates:
        reason = f"模型选择了不可用的 {decision.next_step}，已由路由边界修正为 {next_step}。"

    # 打印和写入 State的是同一份调度结果：前者方便运行时观察，后者供条件边使用。
    print(f"[Supervisor] next={next_step} reason={reason}")
    return {
        "next_step": next_step,
        "decisions": [f"Supervisor -> {next_step}: {reason}"],
        "trace": [f"[Supervisor] 决定下一步：{next_step}"],
    }


def attractions_agent(state: TravelState) -> TravelState:
    """只负责根据需求提出初步景点和行程，不负责全局调度。"""
    request = require_request(state)
    prompt = [
        SystemMessage(
            content=(
                "你是景点规划子Agent。请根据用户需求规划一个轻松的初步行程。"
                "必须返回至少 3 个景点、覆盖 5 天的每日行程，以及大于 0 的预计总花费。"
                "每天只安排一条简短行程，内容要照顾老人并控制行程强度。"
                "不要返回空列表，不要把数字费用填为 0，不要讨论下一步调用哪个子Agent。"
            )
        ),
        HumanMessage(
            content=(
                f"用户需求：{request}\n"
                "请直接生成完整的景点规划，不要只描述应该如何规划。"
            )
        ),
    ]
    # 先把模型限制为 AttractionPlan格式，再发送提示词。
    attraction_model = model.with_structured_output(AttractionPlan)
    # 得到模型返回的结果，再转换成 AttractionPlan对象。
    attraction_result = attraction_model.invoke(prompt)
    result = AttractionPlan.model_validate(attraction_result)
    print(f"[景点规划子Agent] places={result.places} cost={result.estimated_cost}")

    # LangGraph State保存普通字典，不直接保存 Pydantic对象。
    attraction_data = result.model_dump()
    return {
        "attraction_plan": attraction_data,
        "completed_agents": ["attractions_agent"],
        "trace": ["[景点规划子Agent] 完成初步行程规划"],
    }


def budget_constraint_agent(state: TravelState) -> TravelState:
    """只从用户需求提取预算约束，具体方案的花费由优化子Agent综合判断。"""
    request = require_request(state)
    prompt = [
        SystemMessage(
            content=(
                "你是预算约束提取子Agent。只从用户需求提取预算上限、行程节奏和舒适度约束。"
                "当前可能还没有景点方案，所以不要声称已经完成费用核算。"
                "不要修改行程，不要判断是否超预算，也不要决定下一个子Agent。"
            )
        ),
        HumanMessage(
            content=(
                f"用户需求：{request}"
            )
        ),
    ]
    # 先要求模型按照 BudgetConstraints格式返回预算上限、节奏和约束。
    budget_model = model.with_structured_output(BudgetConstraints)
    # 得到模型返回的结果，再转换成 BudgetConstraints对象。
    budget_result = budget_model.invoke(prompt)
    result = BudgetConstraints.model_validate(budget_result)
    print(
        f"[预算约束子Agent] limit={result.budget_limit} pace={result.pace}"
    )

    constraints_data = result.model_dump()
    return {
        "budget_constraints": constraints_data,
        "completed_agents": ["budget_constraint_agent"],
        "trace": ["[预算约束子Agent] 完成预算约束提取"],
    }


def optimizer_agent(state: TravelState) -> TravelState:
    """根据前两个子Agent的结果调整方案，并产出最终行程。"""
    request = require_request(state)
    attraction_plan = require_state_dict(state, "attraction_plan")
    budget_constraints = require_state_dict(state, "budget_constraints")
    prompt = [
        SystemMessage(
            content=(
                "你是行程优化子Agent。综合用户需求、景点规划和预算约束，"
                "调整出适合老人的轻松旅行方案，并给出关键调整。"
                "final_plan必须是完整方案，至少包含5天逐日行程、总预算和老人出行建议，"
                "不能只返回标题或一句概括。"
                "这是最后一个专业子Agent，请输出可以直接给用户的方案。"
            )
        ),
        HumanMessage(
            content=(
                f"用户需求：{request}\n"
                f"景点规划：{json.dumps(attraction_plan, ensure_ascii=False)}\n"
                f"预算约束：{json.dumps(budget_constraints, ensure_ascii=False)}\n"
                "请直接生成完整的最终方案，不要描述应该如何生成方案。"
            )
        ),
    ]
    # 先要求模型按照 OptimizedPlan格式输出最终方案和调整说明。
    optimizer_model = model.with_structured_output(OptimizedPlan)
    # 得到模型返回的结果，再转换成 OptimizedPlan对象。
    optimized_result = optimizer_model.invoke(prompt)
    result = OptimizedPlan.model_validate(optimized_result)
    print(f"[行程优化子Agent] changes={result.changes}")

    optimized_data = result.model_dump()
    return {
        "optimized_plan": optimized_data,
        "completed_agents": ["optimizer_agent"],
        "trace": ["[行程优化子Agent] 完成最终行程优化"],
    }


def finish(state: TravelState) -> TravelState:
    """普通收尾节点；它不决定流程，也不再调用子Agent。"""
    print("[Finish] Supervisor确认所有专业子Agent已完成")
    return {"trace": ["[Finish] 输出最终旅行方案"]}


def route_from_supervisor(state: TravelState) -> str:
    """把 Supervisor 的结构化决定转换为图上的节点名。"""
    next_step = state.get("next_step")
    if next_step is None:
        raise RuntimeError("Supervisor没有写入 next_step，无法继续路由。")
    return next_step


def build_graph():
    builder = StateGraph(TravelState)
    builder.add_node("supervisor", supervisor)
    builder.add_node("attractions_agent", attractions_agent)
    builder.add_node("budget_constraint_agent", budget_constraint_agent)
    builder.add_node("optimizer_agent", optimizer_agent)
    builder.add_node("finish", finish)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "attractions_agent": "attractions_agent",
            "budget_constraint_agent": "budget_constraint_agent",
            "optimizer_agent": "optimizer_agent",
            "finish": "finish",
        },
    )
    builder.add_edge("attractions_agent", "supervisor")
    builder.add_edge("budget_constraint_agent", "supervisor")
    builder.add_edge("optimizer_agent", "supervisor")
    builder.add_edge("finish", END)
    return builder.compile(name="Supervisor Travel Planner")


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Supervisor 多 Agent 旅行规划实验")
    parser.add_argument(
        "--request",
        default=(
            "我想带家人去云南旅行 5 天，预算 10000 元，希望行程轻松一些，适合老人。"
        ),
        help="旅行规划需求",
    )
    args = parser.parse_args()

    graph = build_graph()
    result = graph.invoke({"request": args.request})
    print("\n=== Supervisor 调度轨迹 ===")
    for item in result.get("trace", []):
        print(item)

    optimized_plan = require_state_dict(result, "optimized_plan")
    final_plan = optimized_plan.get("final_plan")
    changes = optimized_plan.get("changes")
    if not isinstance(final_plan, str) or not isinstance(changes, list):
        raise RuntimeError("最终方案的结构化结果不完整。")

    print("\n=== 最终方案 ===")
    print(final_plan)
    print("\n=== 关键调整 ===")
    for change in changes:
        print(f"- {change}")


if __name__ == "__main__":
    main()
