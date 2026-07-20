# LangGraph 工具调用治理：安全运维工具执行台

这个实验演示一张图如何管住工具调用，而不是只把工具交给模型自由触发。

完整实验文稿：

```text
../../23 | LangGraph 工具调用治理：让工具执行可控、可恢复、可审计.md
```

重点观察 5 件事：

- 工具错误进入 State，不让整张图直接崩掉。
- 高风险写操作先 `interrupt()`，人工批准后才执行。
- 每条路径都写入 `audit_log`。
- 策略节点按动作类型限制可用工具集合。
- 工具失败后重试一次，仍失败则创建人工处理工单。

实验流程：

```text
classify_request
 -> plan_action
 -> enforce_tool_policy
 -> approval_gate
 -> execute_tool
 -> handle_tool_error
 -> retry_or_fallback
 -> append_audit_log
 -> final_response
```

模型只在 `final_response` 节点中使用本地 Ollama 的 `qwen3-coder:30b`，用于根据最终 State 写一段中文回复。工具规划和工具执行使用确定性 Python 代码，方便看清图结构本身如何治理工具。

运行前确认 Ollama 已启动，并且已经拉取模型：

```bash
ollama list
ollama pull qwen3-coder:30b
```

从仓库根目录运行：

```bash
uv run labs/langgraph/foundations/experiments/23_tool_governance_console/main.py
```

生成 Graphviz 图结构图片：

```bash
uv run labs/langgraph/foundations/experiments/23_tool_governance_console/render_graphviz.py
```

脚本会依次跑 5 条路径：

```text
1. 只读查询成功
2A. 高风险写操作，先暂停等待审批
2B. 人工批准，恢复后执行工具
3A. 高风险写操作，先暂停等待审批
3B. 人工拒绝，恢复后不执行工具
4. 工具失败，重试后降级到人工工单
5. 工具不属于当前动作允许集合，被图拒绝执行
```
