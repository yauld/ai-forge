---
title: Supervisor 多 Agent：中心 Agent 如何统一调度多个角色
date: 2026-07-22
tags:
  - LangGraph
  - Multi-Agent
  - Supervisor
  - State
summary: "通过一个云南家庭旅行规划实验，观察 Supervisor 如何在程序定义的合法边界内调度多个专业子Agent，并让专业结果通过共享 State 回到中心流程。"
---

# Supervisor 多 Agent：中心 Agent 如何统一调度多个角色

这篇实验回答一个问题：

```text
当一个任务需要多个专业子Agent协作时，谁负责决定下一步调用谁？
```

本实验使用一个云南家庭旅行规划任务，让三个专业子Agent协作完成方案：

```text
用户需求
  ↓
Supervisor
  ↓
景点规划子Agent / 预算约束子Agent / 行程优化子Agent
  ↓
Supervisor
  ↓
最终方案
```

实验最重要的结论是：

> Supervisor拥有全局调度权，专业子Agent只负责局部任务；专业子Agent完成后，把结果写回 State并返回 Supervisor，而不是直接把控制权交给另一个专业子Agent。

## 1. 实验目标与范围

### 1.1 本实验要理解什么

运行并阅读这个实验后，应该能够解释：

- Supervisor是什么，以及它和专业子Agent的职责差异。
- 为什么三个专业子Agent都通过 `add_node()`加入 Graph。
- Supervisor如何读取当前 State并决定下一步。
- 专业子Agent如何把结果写回共享 State。
- 为什么专业子Agent完成后都返回 Supervisor。
- 程序定义的流程边界和模型决策分别负责什么。

### 1.2 本实验暂时不展开什么

当前实验中的每个专业子Agent是一个带有明确职责的模型节点。它们还没有自己的工具循环、复杂内部状态或独立子图。

以下内容留到后续主题：

- Agent之间直接移交控制权的 Handoff模式。
- 把一个专业子Agent实现成完整子图。
- 多 Agent并行执行。
- Agent内部的工具调用循环。
- 生产环境中的重试、缓存、限流和观测。

这里先把一个问题讲透：Supervisor如何统一调度多个角色。

## 2. 准备实验

实验目录位于：

```text
labs/langgraph/foundations/experiments/26_supervisor_travel_planner/
```

配套文件：

```text
main.py                         # 实验主程序
render_graphviz.py              # 导出 Graphviz 图片
supervisor_travel_planner_architecture.png
supervisor_travel_planner_runtime.png
```

本实验使用项目当前配置的本地 Ollama模型：

```text
qwen3-coder:30b
```

运行前确认 Ollama已经启动，并且模型已经准备好：

```bash
ollama pull qwen3-coder:30b
```

从仓库根目录运行：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py
```

导出静态 Graphviz图片，不调用模型：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/render_graphviz.py
```

## 3. 先看业务角色

用户输入的是：

```text
我想带家人去云南旅行5天，预算10000元，希望行程轻松一些，适合老人。
```

实验只保留三个专业子Agent。

### 3.1 景点规划子Agent

职责是根据用户需求生成初步规划，包括：

- 至少三个景点。
- 五天每日行程。
- 初步预计费用。

它不负责决定下一步调用谁，也不负责全局汇总。

### 3.2 预算约束子Agent

这个角色的名字非常重要。它不是完整的预算核算 Agent，而是预算约束提取 Agent。

它只负责从用户需求中提取：

- 预算上限。
- 行程节奏。
- 老人出行相关的舒适度约束。

它不负责计算当前景点方案的真实花费，也不判断是否已经超预算。这样命名和提示词能够避免模型把一个“约束提取”角色误解成“预算检查”角色。

### 3.3 行程优化子Agent

它读取前两个专业子Agent的结果，生成最终方案，包括：

- 五天逐日行程。
- 总预算说明。
- 老人出行建议。
- 对初步方案做出的关键调整。

它是最后一个专业子Agent，但它也不负责调度下一个子Agent。任务完成后，仍然把结果交回 Supervisor。

## 4. Supervisor拥有什么控制权

先看架构图：

![Supervisor 多 Agent架构图](experiments/26_supervisor_travel_planner/supervisor_travel_planner_architecture.png)

这张图表达的是角色关系，不是一条固定的运行路径。

Supervisor和三个专业子Agent在 LangGraph中都是节点。它们的区别不在于使用了不同的 `add_node()` API，而在于职责不同：

```text
Supervisor：决定全局下一步
景点规划子Agent：负责景点和初步行程
预算约束子Agent：负责提取预算约束
行程优化子Agent：负责整合结果
```

图中的两类箭头表示：

- 蓝色实线：Supervisor把任务分配给专业子Agent。
- 灰色虚线：专业子Agent完成工作后，把结果返回 Supervisor。

因此，当前实验不是下面这种直接接力：

```text
景点规划子Agent → 预算约束子Agent → 行程优化子Agent
```

而是：

```text
Supervisor → 景点规划子Agent → Supervisor
Supervisor → 预算约束子Agent → Supervisor
Supervisor → 行程优化子Agent → Supervisor
```

这就是 Supervisor模式的核心结构。

## 5. State如何承载协作结果

当前实验的 State定义如下：

```python
class TravelState(TypedDict, total=False):
    request: str
    attraction_plan: dict
    budget_constraints: dict
    optimized_plan: dict
    completed_agents: Annotated[list[str], operator.add]
    decisions: Annotated[list[str], operator.add]
    trace: Annotated[list[str], operator.add]
    next_step: str
```

可以把它看成一份持续更新的工作记录：

```text
request
  用户的原始需求

attraction_plan
  景点规划子Agent写入的初步方案

budget_constraints
  预算约束子Agent写入的预算、节奏和舒适度约束

optimized_plan
  行程优化子Agent写入的最终方案

completed_agents
  已完成的专业子Agent列表

next_step
  Supervisor写入的下一步节点名称
```

数据交接关系是：

```text
景点规划子Agent
  写入 attraction_plan

预算约束子Agent
  写入 budget_constraints

行程优化子Agent
  读取 attraction_plan 和 budget_constraints
  写入 optimized_plan

Supervisor
  读取 completed_agents
  写入 next_step
```

`completed_agents`、`decisions`和 `trace`使用列表 reducer，是为了让每次节点返回的一条记录累积到同一个列表，而不是覆盖前面已经发生的记录。

## 6. Supervisor如何决定下一步

### 6.1 先由程序确定合法候选

Supervisor函数先读取已经完成的 Agent：

```python
completed = state.get("completed_agents", [])
```

然后根据前置条件生成当前合法候选：

```python
if "attractions_agent" not in completed and "budget_constraint_agent" not in completed:
    candidates = ["attractions_agent", "budget_constraint_agent"]
elif "attractions_agent" not in completed:
    candidates = ["attractions_agent"]
elif "budget_constraint_agent" not in completed:
    candidates = ["budget_constraint_agent"]
elif "optimizer_agent" not in completed:
    candidates = ["optimizer_agent"]
else:
    candidates = ["finish"]
```

这段代码属于流程边界，不是 Supervisor模型的替代品。

它规定了几条不能被模型跳过的前置条件：

- 景点规划和预算约束提取都可以先执行。
- 行程优化必须等待前两个结果。
- 所有专业子Agent完成后才能结束。

因此当前实验使用的是受约束的 Supervisor：

```text
程序代码：规定合法候选
模型：在合法候选中选择下一步
程序代码：检查模型选择
LangGraph：执行条件路由
```

真实业务通常也需要这种边界。权限、审批、工具白名单和必要前置数据不应该完全交给模型自由猜测。

### 6.2 再由模型选择下一步

Supervisor把这些信息交给本地模型：

```python
prompt = [
    SystemMessage(...),
    HumanMessage(
        content=(
            f"用户需求：{request}\n"
            f"已经完成的 Agent：{completed}\n"
            f"当前状态：{json.dumps(state, ensure_ascii=False, default=str)}\n"
            f"候选 next_step：{candidates}\n"
        )
    ),
]
```

Supervisor提示词还明确写出了三个角色的职责，尤其说明预算约束子Agent：

```text
只负责从用户需求提取预算、节奏和舒适度约束，
不负责计算实际费用，也不负责判断是否超预算。
```

这一步很重要。模型不会读取 Python函数内部来推断 Agent职责，它主要根据提示词、State字段和候选节点名称理解当前角色。

### 6.3 结构化读取模型决定

模型返回的不是随意文本，而是 `SupervisorDecision`结构：

```python
class SupervisorDecision(BaseModel):
    next_step: NextStep
    reason: str
```

调用过程拆成三步：

```python
decision_model = model.with_structured_output(SupervisorDecision)
decision_result = decision_model.invoke(prompt)
decision = SupervisorDecision.model_validate(decision_result)
```

分别表示：

1. 得到一个要求按照 `SupervisorDecision`格式输出的模型对象。
2. 调用模型得到结果。
3. 把模型结果转换成可以读取 `next_step`和 `reason`字段的对象。

这里的结构化输出解决的是“模型应该返回什么形状”，不是“模型是否一定做出了正确业务决定”。所以后面还要进行候选校验。

### 6.4 检查模型是否越过流程边界

模型即使收到候选列表，也可能返回一个当前不允许的节点。代码会做白名单检查：

```python
next_step = (
    decision.next_step
    if decision.next_step in candidates
    else candidates[0]
)
```

这说明模型的决定不是直接拥有执行权的命令。它必须经过程序定义的路由边界，才能真正驱动 Graph。

最后，Supervisor把结果写回 State：

```python
return {
    "next_step": next_step,
    "decisions": [f"Supervisor -> {next_step}: {reason}"],
    "trace": [f"[Supervisor] 决定下一步：{next_step}"],
}
```

条件边读取 `next_step`，把 Graph跳转到下一个节点。

## 7. 专业子Agent如何返回结果

以景点规划子Agent为例，它只负责自己的局部任务：

```python
attraction_model = model.with_structured_output(AttractionPlan)
attraction_result = attraction_model.invoke(prompt)
result = AttractionPlan.model_validate(attraction_result)
attraction_data = result.model_dump()
```

它最终返回：

```python
return {
    "attraction_plan": attraction_data,
    "completed_agents": ["attractions_agent"],
    "trace": ["[景点规划子Agent] 完成初步行程规划"],
}
```

注意三个边界：

- 它只写 `attraction_plan`。
- 它把自己加入 `completed_agents`。
- 它不写 `next_step`，也不调用另一个专业子Agent。

预算约束子Agent和行程优化子Agent遵循同样的边界：

```text
专业子Agent完成局部任务
  ↓
更新自己的 State字段
  ↓
返回 Supervisor
```

在 `build_graph()`中，三个子Agent虽然都通过 `add_node()`注册，但它们的职责不同：

```python
builder.add_node("supervisor", supervisor)
builder.add_node("attractions_agent", attractions_agent)
builder.add_node("budget_constraint_agent", budget_constraint_agent)
builder.add_node("optimizer_agent", optimizer_agent)
```

LangGraph没有单独的 `add_agent()` API。一个子Agent在图中首先是一个可执行节点；当它内部进一步发展出多个节点、工具和循环时，才适合封装成子图。

## 8. 运行实验并观察证据

### 8.1 场景一：默认合法输入

运行：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py
```

一次成功运行的关键输出如下：

```text
[Supervisor] next=attractions_agent
[景点规划子Agent] places=['昆明滇池公园', '大理古城', '丽江古城'] cost=9800
[Supervisor] next=budget_constraint_agent
[预算约束子Agent] limit=10000 pace=轻松
[Supervisor] next=optimizer_agent
[行程优化子Agent] changes=[...]
[Supervisor] next=finish
[Finish] Supervisor确认所有专业子Agent已完成
```

最终方案包含：

- 五天逐日行程。
- 总预算9800元。
- 老人出行建议。
- 行程调整说明。

这些是直接观察到的证据。根据这些输出，可以确认：

1. 景点规划子Agent先完成了初步规划。
2. 预算约束子Agent提取了用户约束。
3. 行程优化子Agent读取前两个结果后生成最终方案。
4. 每个专业子Agent完成后都回到了 Supervisor。
5. Supervisor最后才把流程送到 `finish`。

### 8.2 场景二：更严格的预算和节奏约束

运行：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py \
  --request "两位老人去云南5天，预算6000元，希望每天不要安排太多景点"
```

这个场景不是为了证明预算约束子Agent完成了费用核算，而是观察约束如何流过 State：

```text
用户输入更严格的预算和节奏
  ↓
budget_constraint_agent提取新的约束
  ↓
optimizer_agent读取这些约束
  ↓
最终方案据此调整
```

应该重点检查：

- 预算约束子Agent输出的 `budget_limit`是否变化。
- `pace`是否体现“每天不要安排太多景点”。
- 最终方案是否比默认场景更保守。
- Supervisor调度关系是否仍然完整。

### 8.3 场景三：完整回归

重新运行默认命令：

```bash
uv run python labs/langgraph/foundations/experiments/26_supervisor_travel_planner/main.py
```

确认边界场景没有破坏正常流程：

- 景点规划结果仍然完整。
- 预算约束仍然能够写入 State。
- 行程优化仍然能够读取两个前置结果。
- Supervisor仍然能够进入 `finish`。

## 9. 直接观察与实现推断

实验输出能够直接证明的内容包括：

- Supervisor实际输出了哪些 `next_step`。
- 每个专业子Agent输出了哪些结果摘要。
- State中的流程轨迹最终经过了哪些节点。
- 最终方案是否包含要求的内容。

根据代码结构可以进一步推断：

- 专业子Agent之间没有直接的控制权转移。
- `next_step`是 Supervisor写入并由条件边读取的。
- `candidates`为模型决策提供了程序定义的合法边界。
- 专业子Agent的结果通过 State交给后续 Agent。

需要保持一个边界：Supervisor输出的 `reason`是模型生成的解释，不应单独当作业务事实。真正可靠的证据是 State字段、节点执行轨迹和最终结果之间的对应关系。

## 10. 常见误区

### 10.1 Agent必须使用特殊的 Graph API吗？

不需要。Agent在 LangGraph中首先是一个可执行节点，所以使用 `add_node()`是正常写法。

当前实验中，Agent是单个结构化模型节点。更复杂的 Agent可以由一整张子图实现，但那是后续主题。

### 10.2 `candidates`是不是说明模型没有决策权？

不是。它说明当前实验采用了受约束的 Supervisor：程序限制非法路径，模型在合法候选中做选择。

业务中的权限、审批、必要前置数据和工具白名单通常也需要由程序控制，不能完全交给模型自由推测。

### 10.3 预算约束子Agent是不是完成了预算核算？

不是。它只提取用户输入里的预算和舒适度约束。当前实验没有独立的费用计算节点，也没有比较“预计总费用”和“预算上限”的专门检查逻辑。

### 10.4 为什么所有 Agent都返回 Supervisor？

因为这是 Supervisor模式的控制权特征。专业子Agent完成自己的局部任务后，不直接决定另一个子Agent，而是把结果交还中心 Supervisor。

Agent之间直接移交控制权属于 Handoff模式，下一篇主题会单独讨论。

## 11. 验收清单

完成实验后，应该能够回答：

- Supervisor负责什么，专业子Agent负责什么？
- 为什么专业子Agent之间没有直接连接？
- `TravelState`中哪些字段承载了 Agent之间的结果？
- `candidates`为什么由程序代码限制？
- 模型实际决定了什么，LangGraph实际执行了什么？
- 为什么三个子Agent都通过 `add_node()`加入 Graph？
- 当前 Agent和完整子图 Agent有什么区别？
- 为什么预算约束子Agent不能被描述成预算核算子Agent？

如果这些问题都能结合代码和运行输出解释清楚，那么本实验的目标就达到了：

```text
Supervisor掌握全局调度权，
专业子Agent负责局部任务，
State负责传递结果，
LangGraph负责执行路由。
```
