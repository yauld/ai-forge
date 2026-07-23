#!/usr/bin/env python3
from typing import Literal

from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    # 这个 Pydantic 模型就是结构化输出的 schema。
    # intent 被限制成三个固定值，order_id 允许没有。
    intent: Literal["refund", "shipping", "other"] = Field(description="用户意图")
    order_id: str | None = Field(description="订单号，没有就返回 None")
    reply: str = Field(description="给用户的一句话回复")


def run_json_prompt(llm: ChatOllama, user_input: str) -> None:
    # 这种方式只是“请求模型配合”返回 JSON，结果仍然是字符串。
    prompt = f"""
请判断用户意图，并严格返回 JSON：
{{
  "intent": "refund | shipping | other",
  "order_id": "订单号，没有则为 null",
  "reply": "给用户的一句话回复"
}}

用户输入：
{user_input}
"""

    response = llm.invoke(prompt)

    print("方式一：prompt 要求返回 JSON")
    print(type(response.content))
    print(response.content)



def run_structured_output(llm: ChatOllama, user_input: str) -> None:
    # 这种方式把输出结构交给 with_structured_output 约束。
    # 返回值会被解析成 IntentResult 对象。
    structured_llm = llm.with_structured_output(IntentResult)
    result = structured_llm.invoke(user_input)
    assert isinstance(result, IntentResult)

    print("方式二：with_structured_output")
    print(type(result))
    print(result)


def main() -> None:
    llm = ChatOllama(
        model="qwen3-coder:30b",
        temperature=0,
    )
    user_input = "我想退 20260722001 这个订单"

    run_json_prompt(llm, user_input)
    print()
    run_structured_output(llm, user_input)


if __name__ == "__main__":
    main()
