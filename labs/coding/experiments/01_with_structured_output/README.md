# 01_with_structured_output

这个实验对比两种让模型返回结构化结果的方式：

- 在 prompt 里要求模型返回指定 JSON。
- 使用 `with_structured_output` 返回指定结构。

场景保持完全相同：判断用户输入的意图，提取订单号，并生成一句回复。

## 方式一：prompt 要求返回 JSON

```python
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
print(response.content)
```

这种方式的重点是：返回值仍然是模型生成的文本。

## 方式二：with_structured_output

```python
class IntentResult(BaseModel):
    intent: Literal["refund", "shipping", "other"] = Field(description="用户意图")
    order_id: str | None = Field(description="订单号，没有就返回 None")
    reply: str = Field(description="给用户的一句话回复")


structured_llm = llm.with_structured_output(IntentResult)
result = structured_llm.invoke(user_input)

print(result)
```

这种方式的重点是：返回值会被解析成 `IntentResult` 对象。

## 运行

需要本地 Ollama 已启动，并且有模型：

```bash
ollama pull qwen3-coder:30b
```

运行：

```bash
uv run labs/coding/experiments/01_with_structured_output/main.py
```

## 观察结论

普通 JSON prompt 更像是“请求模型配合”：

- 输出是字符串。
- 后续通常还要自己 `json.loads`。
- 字段是否稳定，主要依赖模型是否听话。

`with_structured_output` 更像是“定义输出契约”：

- 输出是 Pydantic 对象。
- 字段和枚举来自 schema。
- 更适合进入后续代码逻辑。
