# 27 Handoff 多 Agent：客服工单自主移交

这个实验用一个售后客服工单说明 Handoff 多 Agent 的核心价值：没有中心 Supervisor 时，当前 Agent 根据自己的职责边界判断“我能不能继续处理”，并把控制权移交给更合适的下一个 Agent。

示例工单是：用户购买的智能门锁第 15 天无法连接 App，已经超过普通退货期，但用户要求退款。

这个场景比旅行预算更适合 Handoff，因为每个 Agent 的权限天然不同：

- `refund_agent` 负责退款政策判断，但不能做技术故障诊断。
- `technical_agent` 负责判断是否疑似商品故障，但不能批准退款。
- `human_agent` 负责处理超过普通政策范围的人工升级审批。

## 运行

从仓库根目录执行：

```bash
uv run python labs/langgraph/foundations/experiments/27_handoff_support_ticket/main.py
```

导出静态结构图和代表性运行路径图：

```bash
uv run python labs/langgraph/foundations/experiments/27_handoff_support_ticket/render_graphviz.py
```

图片会生成在：

```text
labs/langgraph/foundations/experiments/27_handoff_support_ticket/handoff_support_ticket_architecture.png
labs/langgraph/foundations/experiments/27_handoff_support_ticket/handoff_support_ticket_runtime.png
```

静态结构图展示 `ALLOWED_HANDOFFS` 约束后的业务移交关系；运行路径图展示本实验正常情况下的代表性路径。

实验使用本地 `qwen3-coder:30b`。默认最多允许 6 次移交，避免 Agent 之间无限循环。

## 观察重点

```text
refund_agent -> technical_agent
technical_agent -> refund_agent
refund_agent -> human_agent
human_agent -> finish
```

这条链路不是为了凑循环，而是由业务职责决定：

- 退款 Agent 第一次处理时发现缺少故障证据，所以交给技术 Agent。
- 技术 Agent 完成诊断后不能退款，所以交回退款 Agent。
- 退款 Agent 拿到故障证据后发现订单已超过普通退货期，所以交给人工升级 Agent。
- 人工升级 Agent 做最终审批，然后结束流程。

`handoff_history` 会记录每次移交的来源、目标、原因和次数。实验没有让模型直接跳到任意节点：Agent 的移交意图必须经过 `ALLOWED_HANDOFFS` 和最大次数校验，校验失败后进入 `failed`。

## 实验结论

Handoff 适合“下一个处理者由当前处理结果决定”的任务。它不是固定流水线，也不是中心 Supervisor 统一调度。合理的工程边界是：Agent 负责提出局部移交意图，程序负责限制合法范围，LangGraph 负责执行通过校验的 `Command(update=..., goto=...)`。
