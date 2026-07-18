from registration_command_demo import build_graph


def test_complete_form_goes_to_process() -> None:
    graph = build_graph()

    result = graph.invoke(
        {"name": "小林", "phone": "13800000000", "workshop": "LangGraph 入门课"}
    )

    assert result.get("valid") is True
    assert result.get("missing_fields") == []
    assert result.get("validation_note") == "报名表信息完整，可以进入办理。"
    assert result.get("final_message") == "小林，你的LangGraph 入门课报名已受理。"


def test_incomplete_form_goes_to_ask_for_more() -> None:
    graph = build_graph()

    result = graph.invoke({"name": "小周", "workshop": "LangGraph 入门课"})

    assert result.get("valid") is False
    assert result.get("missing_fields") == ["手机号"]
    assert result.get("validation_note") == "报名表缺少：手机号。"
    assert result.get("final_message") == "请先补充手机号，补齐后再继续报名。"
