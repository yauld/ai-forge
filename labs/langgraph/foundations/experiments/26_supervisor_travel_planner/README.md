# 26 Supervisor 多 Agent：中心 Agent 如何统一调度多个角色

这个实验用“云南家庭旅行规划”说明 Supervisor 多 Agent 的核心控制关系：三个专业子Agent都只负责自己的工作，下一步调用谁、什么时候结束，全部由中心 Supervisor决定。

## 实验目标

用户提出一个复杂但具体的需求：

> 我想带家人去云南旅行 5 天，预算 10000 元，希望行程轻松一些，适合老人。

实验只保留三个专业子Agent：

```text
景点规划子Agent：规划初步景点和每日行程
预算约束子Agent：只提取预算、节奏和舒适度约束，不计算实际费用
行程优化子Agent：综合前两个结果，生成最终方案
```

图的控制流是：

```text
START
  -> Supervisor
  -> 景点规划子Agent 或预算约束子Agent
  -> Supervisor
  -> 另一个尚未完成的专业子Agent
  -> Supervisor
  -> 行程优化子Agent
  -> Supervisor
  -> Finish
  -> END
```

最值得观察的是：三个专业子Agent都返回 Supervisor，专业子Agent之间没有直接连线。开始阶段景点规划子Agent和预算约束子Agent都可以先执行，具体先后顺序由 Supervisor模型根据当前 State作出；两个结果齐全后，再调用行程优化子Agent。

## 运行前提

项目使用本地 Ollama的 `qwen3-coder:30b`，请先确认 Ollama已启动并且模型已经准备好：

```bash
ollama pull qwen3-coder:30b
```

在仓库根目录运行：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py
```

导出 LangGraph结构图片，不调用模型：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/render_graphviz.py
```

图片会生成在：

```text
labs/langgraph/foundations/experiments/26_supervisor_travel_planner/supervisor_travel_planner_architecture.png
labs/langgraph/foundations/experiments/26_supervisor_travel_planner/supervisor_travel_planner_runtime.png
```

其中，`supervisor_travel_planner_architecture.png`只表达中心调度关系；`supervisor_travel_planner_runtime.png`展示一条代表性运行路径。预算约束提取和景点规划的实际先后顺序由Supervisor模型决定，因此运行图不是唯一执行顺序。

也可以替换用户需求，观察同一组角色如何被调度：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py \
  --request "两位老人去云南 5 天，预算 6000 元，希望每天不要安排太多景点"
```

## 代码阅读顺序

1. 先看 `TravelState`，确认三个专业子Agent通过哪些字段交换结果。
2. 再看 `supervisor`，它调用模型生成 `next_step`，并把选择写回 State。
3. 查看三个专业子Agent，注意它们只写自己的结果，不决定下一个节点。
4. 最后看 `build_graph`，重点观察每个专业子Agent都回到 `supervisor`。

## 观察重点

一次正常运行应该看到类似的调度轨迹，前两个子Agent的顺序可能不同：

```text
Supervisor -> attractions_agent 或 budget_constraint_agent
Supervisor -> 另一个尚未完成的子Agent
Supervisor -> optimizer_agent
Supervisor -> finish
```

模型输出的具体景点、费用和文字会变化，但控制流应保持这个顺序。代码对 Supervisor的选择做了候选范围校验：模型如果选择了当前不允许的子Agent，实验会记录修正原因并使用合法候选，避免模型输出把图带入死循环。

## 这个实验说明了什么

Supervisor 多 Agent不是“多个节点改名成多个 Agent”。它的关键在于：

- 专业子Agent有独立职责和结构化输出；
- 预算约束子Agent只提取约束，不冒充预算核算子Agent；
- Supervisor拥有全局视角，负责分配任务和安排顺序；
- 专业子Agent完成工作后把结果交回Supervisor，而不是直接把控制权交给另一个专业子Agent；
- LangGraph负责保存共享 State并执行Supervisor决定的下一步。

这个实验暂不实现 Handoff。下一篇实验会复用同一旅行规划场景和三个角色，让子Agent之间直接移交控制权，比较两种模式的差异。
