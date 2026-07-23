# LangChain with_structured_output：别再只靠提示词要求模型返回 JSON

以前我让大模型返回结构化结果时，常用办法是在 prompt 里写：

```text
请严格返回 JSON，格式如下：
{
  "intent": "...",
  "order_id": "...",
  "reply": "..."
}
```

这个方式能用，但它本质上只是“请求模型配合”。

模型可能会严格返回 JSON，也可能多说一句解释、少一个字段、写错字段名，或者返回一段看起来像 JSON 但程序解析不了的文本。

LangChain 的 `with_structured_output` 解决的是同一个问题：让模型输出结构化结果。但它的思路不是继续强化 prompt，而是把输出结构变成 schema。

下面用一个最小实验对比这两种方式。

## 实验场景

用户输入：

```text
我想退 20260722001 这个订单
```

我们希望模型判断意图、提取订单号，并生成一句回复：

```json
{
  "intent": "refund",
  "order_id": "20260722001",
  "reply": "..."
}
```

## 方式一：prompt 要求返回 JSON

第一种方式是直接把 JSON 格式写进 prompt。

```python
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
```

这里的关键是：

```python
response.content
```

它仍然是一段字符串。即使模型返回了合法 JSON，后续代码通常还要自己做：

```python
json.loads(response.content)
```

然后再处理解析失败、字段缺失、类型错误、枚举值不符合预期等问题。

## 方式二：with_structured_output

第二种方式是先定义输出 schema。

```python
class IntentResult(BaseModel):
    # 这个 Pydantic 模型就是结构化输出的 schema。
    # intent 被限制成三个固定值，order_id 允许没有。
    intent: Literal["refund", "shipping", "other"] = Field(description="用户意图")
    order_id: str | None = Field(description="订单号，没有就返回 None")
    reply: str = Field(description="给用户的一句话回复")
```

然后把 schema 交给模型：

```python
def run_structured_output(llm: ChatOllama, user_input: str) -> None:
    # 这种方式把输出结构交给 with_structured_output 约束。
    # 返回值会被解析成 IntentResult 对象。
    structured_llm = llm.with_structured_output(IntentResult)
    result = structured_llm.invoke(user_input)
    assert isinstance(result, IntentResult)

    print("方式二：with_structured_output")
    print(type(result))
    print(result)
```

核心只有两行：

```python
structured_llm = llm.with_structured_output(IntentResult)
result = structured_llm.invoke(user_input)
```

这时拿到的不是字符串，而是 `IntentResult` 对象。

## 完整实验入口

```python
def main() -> None:
    llm = ChatOllama(
        model="qwen3-coder:30b",
        temperature=0,
    )
    user_input = "我想退 20260722001 这个订单"

    run_json_prompt(llm, user_input)
    print()
    run_structured_output(llm, user_input)
```

运行：

```bash
uv run labs/coding/experiments/01_with_structured_output/main.py
```

## 核心区别

普通 JSON prompt 是自然语言约束：

```text
请严格返回 JSON
```

你是在请求模型按格式返回。

`with_structured_output` 是结构化约束：

```python
structured_llm = llm.with_structured_output(IntentResult)
```

你是在定义这次模型调用的输出契约。

所以它们的差异可以概括为：

```text
普通 prompt JSON 是“请求模型配合”；
with_structured_output 是“定义输出契约”。
```

## 它是不是一定成功？

不是。

`with_structured_output` 不是保证模型永远不失败。更准确地说：

如果结构化输出成功，它返回的就是指定结构对象。

如果模型或底层接口没有按 schema 返回，LangChain 会在解析或校验阶段暴露问题，而不是让一段乱格式文本悄悄流进后续业务代码。

这才是它真正重要的地方。

真实应用里，我们害怕的不是模型偶尔失败，而是模型失败了，程序还以为它成功了。

## 放到 LangGraph 多 Agent 里有什么好处？

`with_structured_output` 虽然是 LangChain 模型接口，但在 LangGraph 里一样可以用。

因为 LangGraph 负责流程编排，节点内部仍然可以调用 LangChain 的模型。

在多 Agent 场景里，它的价值会更明显。

比如 Supervisor Agent 要决定下一步交给谁：

```python
class RouteResult(BaseModel):
    next: Literal["researcher", "coder", "reviewer", "finish"]
    reason: str
```

如果只靠 prompt 要求返回 JSON，后续条件边拿到的可能还是一段不稳定文本。

但用 `with_structured_output`，Supervisor 节点可以返回一个明确的路由对象：

```python
router = llm.with_structured_output(RouteResult)
route = router.invoke(messages)
assert isinstance(route, RouteResult)
```

后续 LangGraph 条件边就可以稳定读取：

```python
return state["route"].next
```

这时 Agent 之间的交接不再是“自然语言约定”，而是“类型化协议”。

多 Agent 链路越长，这个好处越明显：路由、审核、任务拆解、是否结束，都可以用结构化结果表达，错误也更容易在节点边界暴露。

## 什么时候用？

如果模型输出只是自然语言回答，普通调用就够了。

但如果模型输出要继续进入程序逻辑，比如意图识别、信息抽取、参数生成、分类打标、路由决策，就应该优先考虑 `with_structured_output`。

因为这时你需要的不是“一段看起来像 JSON 的文本”，而是“程序可以依赖的结构化对象”。

一句话总结：

```text
不要只要求模型“像 JSON”。
让模型输出真正进入你的类型系统。
```
