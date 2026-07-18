# LangGraph Command 前台报名实验

配套实验文稿：

[LangGraph Command：节点里同时更新状态和决定下一步](../../22%20%7C%20LangGraph%20Command：节点里同时更新状态和决定下一步.md)

这个实验用“前台接待员检查报名表”说明 `Command(update=..., goto=...)`：

```text
validate_request
  ├─ 信息完整：写入 valid=True，然后 goto process 节点
  └─ 信息缺失：写入 missing_fields，然后 goto ask_for_more 节点
```

也就是说，validate_request 节点不是只写状态，也不是只决定路线，而是在同一个返回值里完成两件事：

```python
return Command(
    update={"valid": True},
    goto="process",
)
```

这里的 `goto` 指向 LangGraph 节点名。前台“窗口”只是生活类比，不是 State 里的业务字段。

## 文件

```text
registration_command_demo.py  # 最小实验脚本
conditional_edge_demo.py  # 用普通条件边实现同一个报名表流程
self_check.py  # 不依赖 pytest 的快速自检
test_registration_command_demo.py  # pytest 回归测试
test_conditional_edge_demo.py  # 条件边版本的 pytest 回归测试
```

## 运行

运行前确认本地 Ollama 已启动，并且已经拉取 `qwen3-coder:30b`。

```bash
uv run labs/langgraph/foundations/experiments/21_command_registration_desk/registration_command_demo.py
```

如果要看普通条件边版本，运行：

```bash
uv run labs/langgraph/foundations/experiments/21_command_registration_desk/conditional_edge_demo.py
```

观察输出里的 `节点输出`：

- 完整报名表会先看到 validate_request 写入 valid、validation_note，再进入 process。
- 缺失手机号的报名表会先看到 validate_request 写入 missing_fields、validation_note，再进入 ask_for_more。
- 每个案例最后都会调用本地 `qwen3-coder:30b`，根据已经确定的处理结果生成一句前台回复。

注意：实验里的路线判断不交给模型。模型只在流程结束后改写一句前台回复，这样能保持 Command 的控制流效果清楚可验证。

## Command 和条件边的区别

Command 版本里，validate_request 节点直接返回：

```python
Command(
    update={"valid": True},
    goto="process",
)
```

条件边版本里，validate_request 节点只返回 State 更新：

```python
return {
    "valid": True,
    "missing_fields": [],
    "validation_note": "报名表信息完整，可以进入办理。",
}
```

下一步去哪交给单独的 router 函数：

```python
def route_after_validation(state):
    if state.get("valid") is True:
        return "process"
    return "ask_for_more"
```

## 测试

```bash
uv run pytest labs/langgraph/foundations/experiments/21_command_registration_desk
```

如果当前环境没有安装 pytest，也可以运行不依赖测试框架的快速自检：

```bash
uv run labs/langgraph/foundations/experiments/21_command_registration_desk/self_check.py
```

测试验证两件事：

- 资料完整时，State 被更新为 valid=True，并得到 process 节点生成的受理消息。
- 资料缺失时，State 被写入 missing_fields，并得到 ask_for_more 节点生成的补充资料消息。
