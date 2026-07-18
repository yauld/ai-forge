"""最小 LangGraph Command 实验：前台报名表检查与分流。"""

from __future__ import annotations

from typing import Literal, TypedDict

from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command


NextNode = Literal["process", "ask_for_more"]


class RegistrationState(TypedDict, total=False):
    """State 保存报名表内容，以及前台接待员写下的处理记录。"""

    name: str
    phone: str
    workshop: str
    valid: bool
    missing_fields: list[str]
    validation_note: str
    final_message: str


def validate_request(state: RegistrationState) -> Command[NextNode]:
    """在同一个返回值里写入校验结果，并决定下一步进入哪个节点。"""
    missing_fields: list[str] = []

    if not state.get("name"):
        missing_fields.append("姓名")

    if not state.get("phone"):
        missing_fields.append("手机号")

    if not state.get("workshop"):
        missing_fields.append("报名课程")

    if missing_fields:
        return Command(
            update={
                "valid": False,
                "missing_fields": missing_fields,
                "validation_note": f"报名表缺少：{'、'.join(missing_fields)}。",
            },
            goto="ask_for_more",
        )

    return Command(
        update={
            "valid": True,
            "missing_fields": [],
            "validation_note": "报名表信息完整，可以进入办理。",
        },
        goto="process",
    )


def ask_for_more(state: RegistrationState) -> RegistrationState:
    """ask_for_more 节点读取校验结果，并告诉报名者还需要补充什么。"""
    missing_fields = state.get("missing_fields", [])
    missing_text = "、".join(missing_fields)

    return {
        "final_message": f"请先补充{missing_text}，补齐后再继续报名。",
    }


def process(state: RegistrationState) -> RegistrationState:
    """process 节点只处理已经被前台标记为信息完整的报名表。"""
    name = state.get("name", "同学")
    workshop = state.get("workshop", "课程")

    return {
        "final_message": f"{name}，你的{workshop}报名已受理。",
    }


def build_graph():
    builder = StateGraph(RegistrationState)
    builder.add_node("validate_request", validate_request)
    builder.add_node("ask_for_more", ask_for_more)
    builder.add_node("process", process)

    builder.add_edge(START, "validate_request")
    builder.add_edge("ask_for_more", END)
    builder.add_edge("process", END)

    return builder.compile()


def generate_reply_with_local_model(final_state: RegistrationState) -> str:
    """用本地模型根据已确定的处理结果生成最终回复。"""
    model = ChatOllama(model="qwen3-coder:30b", temperature=0)
    response = model.invoke(
        [
            (
                "system",
                "你是报名处前台。只根据给定结果写一句简短、礼貌、口语化的中文回复。",
            ),
            (
                "human",
                "处理结果："
                f"{final_state.get('final_message', '')}\n"
                f"校验备注：{final_state.get('validation_note', '')}",
            ),
        ]
    )
    return str(response.content)


def run_case(title: str, form: RegistrationState) -> None:
    graph = build_graph()

    print(f"\n=== {title} ===")
    print("输入报名表：")
    print("姓名：", form.get("name", ""))
    print("手机号：", form.get("phone", ""))
    print("报名课程：", form.get("workshop", ""))

    for event in graph.stream(form, stream_mode="updates"):
        print("节点输出：", event)

    final_state = graph.invoke(form)
    print("最终状态：", final_state)
    print("模型生成回复：", generate_reply_with_local_model(final_state))


def main() -> None:
    run_case(
        "资料完整：写入 valid=True，并直接 goto process 节点",
        {"name": "小林", "phone": "13800000000", "workshop": "LangGraph 入门课"},
    )
    run_case(
        "资料缺失：写入 missing_fields，并直接 goto ask_for_more 节点",
        {"name": "小周", "workshop": "LangGraph 入门课"},
    )


if __name__ == "__main__":
    main()
