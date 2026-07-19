---
title: LangGraph Command：节点里同时更新状态和决定下一步
date: 2026-07-18
tags:
  - LangGraph
  - Command
  - Conditional Edge
  - Ollama
summary: "用一个前台报名表实验，对比 Command(update=..., goto=...) 和普通条件边的职责边界。"
---

# LangGraph Command：节点里同时更新状态和决定下一步

这篇实验回答一个很小但很关键的问题：

```text
当一个节点既要写入判断结果，又要根据这个判断决定下一步去哪，应该怎么写？
```

我们用“前台接待员检查报名表”做例子。报名表有三个字段：姓名、手机号、报名课程。

如果信息完整，流程进入 process 节点，生成报名受理消息。如果缺少信息，流程进入 ask_for_more 节点，生成补充资料消息。

这个场景故意设计得很朴素，因为 Command 的重点不是复杂业务，而是把两件事看清楚：

```text
update：写回 State
goto：跳到下一个节点
```

## 1. 实验目标

本实验包含两个实现：

```text
experiments/21_command_registration_desk/registration_command_demo.py
experiments/21_command_registration_desk/conditional_edge_demo.py
```

第一个脚本使用 `Command(update=..., goto=...)`。validate_request 节点在同一个返回值里完成状态更新和节点跳转。

第二个脚本使用普通条件边。validate_request 节点只更新 State，route_after_validation 函数再根据 State 决定下一步去哪里。

运行这两个脚本后，可以观察到它们的业务结果一样，但控制流组织方式不同。

当前项目实测版本：

```text
langgraph==1.2.0
langchain-ollama==1.1.0
pytest==9.1.1
```

运行前需要本地 Ollama 已启动，并且已经拉取 `qwen3-coder:30b`。模型只用于根据最终状态生成一条前台回复，流程判断不交给模型。

## 2. State 里只放业务状态

两个脚本使用同一组 State 字段：

```python
class RegistrationState(TypedDict, total=False):
    name: str
    phone: str
    workshop: str
    valid: bool
    missing_fields: list[str]
    validation_note: str
    final_message: str
```

这里不要放 `next_window` 或 `route_trace`。

`next_window` 容易让人误以为 State 里某个字段控制了图的跳转，但在 LangGraph 里，真正决定下一步的是边、条件边，或者 Command 的 `goto`。

`route_trace` 也不是业务状态。要观察流程走向，可以直接看 streaming 输出里实际执行了哪些节点。

所以这个实验只保留和报名业务有关的字段：

- `valid` 表示报名表是否完整。
- `missing_fields` 表示缺少哪些字段。
- `validation_note` 表示校验节点写入的说明。
- `final_message` 表示后续节点生成的处理结果。

## 3. Command 版本：节点自己写 State，也自己决定下一步

Command 版本的核心代码在 `registration_command_demo.py`：

```python
def validate_request(state: RegistrationState) -> Command[NextNode]:
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
```

这段代码可以直接读成：

```text
如果报名表缺字段：
  把 valid、missing_fields、validation_note 写回 State
  然后 goto ask_for_more 节点

如果报名表完整：
  把 valid、missing_fields、validation_note 写回 State
  然后 goto process 节点
```

`goto` 后面的字符串必须对应图里注册过的节点名：

```python
builder.add_node("ask_for_more", ask_for_more)
builder.add_node("process", process)
```

图结构里不需要再给 validate_request 添加条件边：

```python
builder.add_edge(START, "validate_request")
builder.add_edge("ask_for_more", END)
builder.add_edge("process", END)
```

因为 validate_request 返回的 Command 已经告诉 LangGraph 下一步该去哪里。

## 4. 条件边版本：节点只写 State，router 决定下一步

条件边版本在 `conditional_edge_demo.py`。validate_request 不返回 Command，只返回普通字典：

```python
def validate_request(state: RegistrationState) -> RegistrationState:
    missing_fields: list[str] = []

    if not state.get("name"):
        missing_fields.append("姓名")

    if not state.get("phone"):
        missing_fields.append("手机号")

    if not state.get("workshop"):
        missing_fields.append("报名课程")

    if missing_fields:
        return {
            "valid": False,
            "missing_fields": missing_fields,
            "validation_note": f"报名表缺少：{'、'.join(missing_fields)}。",
        }

    return {
        "valid": True,
        "missing_fields": [],
        "validation_note": "报名表信息完整，可以进入办理。",
    }
```

这个节点只做一件事：检查报名表，把结果写回 State。

下一步去哪，交给 router 函数：

```python
def route_after_validation(state: RegistrationState) -> NextNode:
    if state.get("valid") is True:
        return "process"

    return "ask_for_more"
```

图结构里要显式注册条件边：

```python
builder.add_conditional_edges(
    "validate_request",
    route_after_validation,
    {
        "process": "process",
        "ask_for_more": "ask_for_more",
    },
)
```

这就是条件边的典型职责分工：

```text
validate_request 节点：更新 State
route_after_validation 函数：读取 State，决定下一步节点
```

## 5. 运行 Command 版本

运行：

```bash
uv run labs/langgraph/foundations/experiments/21_command_registration_desk/registration_command_demo.py
```

完整报名表的关键输出：

```text
=== 资料完整：写入 valid=True，并直接 goto process 节点 ===
节点输出： {'validate_request': {'valid': True, 'missing_fields': [], 'validation_note': '报名表信息完整，可以进入办理。'}}
节点输出： {'process': {'final_message': '小林，你的LangGraph 入门课报名已受理。'}}
模型生成回复： 小林，您的LangGraph入门课报名已经受理啦！信息完整，可以继续办理后续流程哦～
```

缺少手机号的关键输出：

```text
=== 资料缺失：写入 missing_fields，并直接 goto ask_for_more 节点 ===
节点输出： {'validate_request': {'valid': False, 'missing_fields': ['手机号'], 'validation_note': '报名表缺少：手机号。'}}
节点输出： {'ask_for_more': {'final_message': '请先补充手机号，补齐后再继续报名。'}}
模型生成回复： 您好，请您先补充手机号码，信息补齐后我们就能继续为您办理报名啦！
```

这里要看两个观察点。

第一，validate_request 的输出里已经包含 State 更新结果。

第二，streaming 输出里的下一个节点分别是 process 和 ask_for_more，说明 Command 的 `goto` 生效了。

## 6. 运行条件边版本

运行：

```bash
uv run labs/langgraph/foundations/experiments/21_command_registration_desk/conditional_edge_demo.py
```

完整报名表的关键输出：

```text
=== 资料完整：validate_request 只写 State，条件边跳到 process 节点 ===
节点输出： {'validate_request': {'valid': True, 'missing_fields': [], 'validation_note': '报名表信息完整，可以进入办理。'}}
节点输出： {'process': {'final_message': '小林，你的LangGraph 入门课报名已受理。'}}
模型生成回复： 小林，您的LangGraph入门课报名已经受理啦！信息完整，可以开始办理了。
```

缺少手机号的关键输出：

```text
=== 资料缺失：validate_request 只写 State，条件边跳到 ask_for_more 节点 ===
节点输出： {'validate_request': {'valid': False, 'missing_fields': ['手机号'], 'validation_note': '报名表缺少：手机号。'}}
节点输出： {'ask_for_more': {'final_message': '请先补充手机号，补齐后再继续报名。'}}
模型生成回复： 您好，请您先补充手机号码，信息补齐后我们就能继续为您办理报名啦！
```

业务结果和 Command 版本一致。差别在于：

```text
Command 版本：跳转决定写在节点返回值里
条件边版本：跳转决定写在图结构的条件边里
```

## 7. 怎么选择

如果判断结果和下一步天然绑定，Command 更直接。

这次报名表校验就是这种情况：

```text
缺字段 -> 写 missing_fields -> 去 ask_for_more
不缺字段 -> 写 valid=True -> 去 process
```

这三件事很难拆开看。校验节点既知道缺什么，也知道下一步应该去哪。用 Command 可以让这个意图集中在一个节点返回值里。

如果跳转规则更像全局流程编排，普通条件边更清楚。

例如同一个 State 字段会被多个节点更新，或者路由规则需要被单独测试、复用、替换，就适合把 router 函数放在图结构里：

```text
节点负责产出状态
router 负责解释状态并选择边
```

可以用一句话区分：

```text
Command：这个节点处理完后，自己知道下一步去哪。
条件边：这个节点处理完后，由图上的路由规则决定下一步去哪。
```

另外要注意，本文讲的是节点返回值里的 Command：

```python
Command(update=..., goto=...)
```

它和人工中断恢复时使用的 `Command(resume=...)` 不是同一个场景。后者是作为 `invoke` 或 `stream` 的顶层输入，用来恢复之前暂停的图执行。

## 8. 验收

运行测试：

```bash
uv run pytest labs/langgraph/foundations/experiments/21_command_registration_desk
```

实测结果：

```text
collected 4 items

labs/langgraph/foundations/experiments/21_command_registration_desk/test_conditional_edge_demo.py . [ 25%]
.                                                                        [ 50%]
labs/langgraph/foundations/experiments/21_command_registration_desk/test_registration_command_demo.py . [ 75%]
.                                                                        [100%]

4 passed
```

完成这篇实验后，应该能说清楚三件事：

1. `Command(update=..., goto=...)` 里的 `update` 会更新 State，`goto` 会指定下一步节点。
2. 普通条件边把“写 State”和“决定下一步”拆成节点函数与 router 函数。
3. 当决策和状态更新天然绑定时，Command 更自然；当路由规则更像图结构的一部分时，条件边更清楚。
