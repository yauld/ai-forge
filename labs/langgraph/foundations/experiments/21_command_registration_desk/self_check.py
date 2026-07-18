"""前台报名 Command 实验的零依赖自检。"""

from registration_command_demo import build_graph


def main() -> None:
    graph = build_graph()

    complete = graph.invoke(
        {"name": "小林", "phone": "13800000000", "workshop": "LangGraph 入门课"}
    )
    assert complete.get("valid") is True
    assert complete.get("missing_fields") == []
    assert complete.get("validation_note") == "报名表信息完整，可以进入办理。"
    assert complete.get("final_message") == "小林，你的LangGraph 入门课报名已受理。"

    incomplete = graph.invoke({"name": "小周", "workshop": "LangGraph 入门课"})
    assert incomplete.get("valid") is False
    assert incomplete.get("missing_fields") == ["手机号"]
    assert incomplete.get("validation_note") == "报名表缺少：手机号。"
    assert incomplete.get("final_message") == "请先补充手机号，补齐后再继续报名。"

    print("自检通过：Command(update=..., goto=...) 能正确分流两种报名表。")


if __name__ == "__main__":
    main()
