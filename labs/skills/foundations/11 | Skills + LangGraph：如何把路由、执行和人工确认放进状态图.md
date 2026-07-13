# 11 | Skills + LangGraph：如何把路由、执行和人工确认放进状态图

前面已经分别看过 Skills runtime 和 Skills + MCP。

阶段 05 里，我们把一个用于观察职责边界的最小 Skills runtime 拆成 Registry、Router、Loader、Executor 和 Trace。阶段 10 里，我们验证了 Skill 与 MCP 的正常协作链路：Skill 描述方法，MCP Server 暴露工具，Host 连接 Server、发现工具、把 Tool schema 给模型，最后由 Host 执行 Tool Call。

但这些实验都是线性的。

真实任务一旦出现分支、暂停、恢复和人工确认，继续把所有逻辑塞进一个 Host 函数里，状态会很快变得难追踪。这个阶段要验证的不是“LangGraph 能不能包一层流程图”，而是：

> Skills runtime 的路由、加载、工具规划、工具执行和人工确认，应该如何进入 LangGraph 的 StateGraph？

本实验用一个订单报告任务来做最小闭环：

```text
帮我查询订单 O-1001，生成一份简短订单报告，确认后写入本地报告文件。
```

这句话同时包含了三类动作：

- 选择合适的 Skill；
- 调用 MCP 工具查询订单；
- 写入文件前等待人工确认。

如果只做顺序调用，当然也能跑通。但这里的关键是：写文件前要暂停，人工批准后还要从 checkpoint 恢复，并且暂停前已经完成的 Skill 路由、MCP 工具发现、工具规划和工具结果都不能丢。

## 一、实验目标与配套文件

本实验回答一个问题：

> 当任务需要 Skill 路由、MCP 工具调用和人工确认时，LangGraph 应该编排什么，Skill 又应该负责什么？

具体目标有四个：

1. 把 Skill 扫描、路由、加载放入 LangGraph 节点。
2. 按 Skills + MCP 的规范链路，先发现 MCP 工具，再让模型基于 Skill 正文和 Tool schema 规划工具调用。
3. 在写入报告前使用 `interrupt(...)` 暂停，等待人工确认。
4. 使用 checkpoint 保存中间状态，让人工批准或拒绝后可以继续执行。

配套代码位于：

```text
labs/skills/foundations/examples/stage11-langgraph-skills/
```

目录结构如下：

```text
stage11-langgraph-skills/
├── data/
│   └── orders.json
├── graph.py
├── mcp_server.py
├── run_demo.py
├── outputs/
│   └── .gitkeep
├── runtime/
│   ├── __init__.py
│   ├── loader.py
│   ├── mcp_client.py
│   ├── registry.py
│   ├── report_writer.py
│   ├── router.py
│   └── types.py
└── skills/
    ├── order-report/
    │   └── SKILL.md
    └── shipping-policy/
        └── SKILL.md
```

这里故意放了两个 Skill：

- `order-report`：查询订单并生成订单报告；
- `shipping-policy`：查询通用物流政策，不处理具体订单。

MCP Server 里也故意放了两个 Tool：

- `get_order(order_id)`：查询具体订单；
- `get_shipping_policy(region)`：查询通用物流政策。

这样路由和工具选择都不是单选题。模型需要先在多个 Skill 中选 `order-report`，再在多个 MCP Tool 中选 `get_order`。

## 二、运行前提

本仓库使用 `uv` 管理 Python 环境。请先在仓库根目录安装依赖：

```bash
uv sync
```

本实验使用本地 Ollama 模型：

```text
qwen3-coder:30b
```

运行前需要确认 Ollama 服务已经启动，并且本地已有这个模型。可以用下面的命令准备模型：

```bash
ollama pull qwen3-coder:30b
```

实验分两段运行。第一段让图执行到人工确认节点并暂停：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py pause
```

第二段模拟人工批准，从 checkpoint 恢复并写入报告：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py approve
```

也可以模拟人工拒绝：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py reject
```

如果你反复运行实验，建议换一个 `thread_id`，避免接到上一次留下的 checkpoint：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py pause \
  --thread-id stage11-order-report-demo-002
```

## 三、这张图做了什么

当前 StateGraph 的结构是：

```text
START
  -> scan_skills
  -> route_skill
  -> load_skill
  -> discover_mcp_tools
  -> plan_tool_call
  -> execute_mcp_tool
  -> draft_report
  -> wait_for_approval
       | approve -> write_report -> final_answer -> END
       | reject  -> final_answer -> END
```

对应代码在 `graph.py`：

```python
builder.add_edge(START, "scan_skills")
builder.add_edge("scan_skills", "route_skill")
builder.add_edge("route_skill", "load_skill")
builder.add_edge("load_skill", "discover_mcp_tools")
builder.add_edge("discover_mcp_tools", "plan_tool_call")
builder.add_edge("plan_tool_call", "execute_mcp_tool")
builder.add_edge("execute_mcp_tool", "draft_report")
builder.add_edge("draft_report", "wait_for_approval")
builder.add_conditional_edges(
    "wait_for_approval",
    choose_after_approval,
    {
        "write_report": "write_report",
        "final_answer": "final_answer",
    },
)
builder.add_edge("write_report", "final_answer")
builder.add_edge("final_answer", END)
```

这个图里，每个节点只做一件事：

| 节点 | 职责 |
| --- | --- |
| `scan_skills` | 扫描 `skills/*/SKILL.md`，只读取 `name` 和 `description` |
| `route_skill` | 模型根据 Skill metadata 选择 Skill |
| `load_skill` | 命中后加载完整 `SKILL.md` 正文 |
| `discover_mcp_tools` | Host 连接 MCP Server，读取真实 Tool schema |
| `plan_tool_call` | 模型根据用户任务、Skill 正文和 Tool schema 规划工具调用 |
| `execute_mcp_tool` | Host 执行模型规划出来的 MCP Tool call |
| `draft_report` | 根据工具结果生成报告草稿 |
| `wait_for_approval` | 写文件前暂停，等待人工批准或拒绝 |
| `write_report` | 人工批准后写入报告 |
| `final_answer` | 整理最终响应 |

这也是本实验想强调的边界：

> Skill 负责描述任务方法，MCP 负责暴露外部工具，LangGraph 负责流程状态、暂停、恢复和分支。

## 四、State 如何承载中间结果

LangGraph 的节点函数接收 `state`，返回一个状态增量。运行时会把节点返回值合并进当前 State，再传给下一个节点。

本实验的 State 定义在 `runtime/types.py`：

```python
class SkillGraphState(TypedDict, total=False):
    task: str
    model_name: str
    skill_candidates: list[dict[str, str]]
    selected_skill: str
    route_reason: str
    route_raw_response: str
    skill_text: str
    loaded_files: list[str]
    mcp_tools: list[dict[str, Any]]
    tool_call_plan: dict[str, Any]
    tool_call_raw_response: str
    order_id: str
    tool_name: str
    tool_result: dict[str, Any]
    report_draft: str
    approval: str
    output_path: str
    write_result: dict[str, Any]
    final_answer: str
    trace: Annotated[list[dict[str, Any]], operator.add]
```

普通字段默认覆盖。例如 `route_skill` 节点返回：

```python
return {
    "selected_skill": route_result.skill_name,
    "route_reason": route_result.reason,
    "route_raw_response": route_result.raw_response,
}
```

LangGraph 会把这几个字段写入 State。所以下游 `load_skill` 节点可以读取 `selected_skill`。

`trace` 比较特殊：

```python
trace: Annotated[list[dict[str, Any]], operator.add]
```

这表示它使用 reducer 合并。每个节点返回一段新的 trace：

```python
{
    "trace": [
        {
            "node": "route_skill",
            "selected_skill": route_result.skill_name,
        }
    ]
}
```

LangGraph 会把它追加到旧 trace 后面，而不是覆盖。这样最后就能看到完整路径。

还有一个小细节：因为 `SkillGraphState` 使用了 `TypedDict(total=False)`，Pylance 会提醒某些 key 可能不存在。实验代码没有用 `# type: ignore` 糊过去，而是写了显式读取函数：

```python
def _require_str(state: SkillGraphState, key: str) -> str:
    value = state.get(key)
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"State 缺少必需字符串字段：{key}")
    return value
```

这让两个事实都更清楚：

- 上游节点确实应该写入这些字段；
- 如果图结构改坏了，下游节点会报出明确缺失字段。

## 五、Skill 路由：只看 metadata，不看正文

`scan_skills_node` 只扫描 metadata：

```python
candidates = [
    {"name": skill.name, "description": skill.description}
    for skill in skills
]
```

两个候选 Skill 分别是：

```text
order-report
shipping-policy
```

`order-report` 的 description 是：

```yaml
description: 当用户需要查询订单并生成订单报告，尤其是要求写入文件或提交前确认时，使用这个 Skill。
```

`shipping-policy` 的 description 是：

```yaml
description: 当用户需要了解通用物流政策、配送时效、偏远地区规则或运费说明时，使用这个 Skill；不要用于查询具体订单状态或生成订单报告。
```

`route_skill` 节点调用 `runtime/router.py`：

```python
route_result = route_skill(
    task=task,
    skills=skills,
    model_name=state.get("model_name", DEFAULT_MODEL),
)
```

Router 的 prompt 明确约束：

```text
请只根据 Skill 的 name 和 description，为用户任务选择一个最匹配的 Skill。
如果没有明确匹配项，返回 "none"。
```

也就是说，路由阶段不读取完整 `SKILL.md`，更不会看到 MCP 工具结果。这仍然是 Skills 的渐进式披露：先用轻量 metadata 判断是否命中，命中后再加载正文。

一次运行中，模型返回：

```json
{
  "skill": "order-report",
  "reason": "用户任务涉及查询特定订单并生成订单报告，符合 order-report Skill 的描述。"
}
```

这说明路由模型在两个 Skill 中选择了正确的一个。

## 六、加载 Skill 后，不能立刻执行工具

这是本实验和最小 demo 最不一样的地方。

如果 `load_skill` 后直接进入 `execute_mcp_tool`，代码当然更短。但那样会跳过 Skills + MCP 正常链路里的两个关键步骤：

1. Host 连接 MCP Server 并发现真实工具；
2. Host 把 Skill 正文和 Tool schema 交给模型，让模型判断该调用哪个 Tool。

所以本实验在 `load_skill` 后插入了两个节点：

```text
load_skill
  -> discover_mcp_tools
  -> plan_tool_call
  -> execute_mcp_tool
```

`discover_mcp_tools` 调用 `runtime/mcp_client.py` 里的 `list_tools()`：

```python
tools = list_tools(server_path=SERVER_PATH, cwd=HERE)
```

MCP Server 暴露了两个工具：

```python
@mcp.tool()
def get_order(order_id: str) -> dict[str, object]:
    """根据订单号查询订单状态、金额和商品名称。"""
```

以及一个无关工具：

```python
@mcp.tool()
def get_shipping_policy(region: str = "CN") -> dict[str, object]:
    """查询指定地区的通用物流政策，不返回具体订单状态。"""
```

一次运行中，工具发现结果是：

```json
[
  {
    "name": "get_order",
    "description": "根据订单号查询订单状态、金额和商品名称。",
    "input_schema": {
      "properties": {
        "order_id": {
          "type": "string"
        }
      },
      "required": ["order_id"],
      "type": "object"
    }
  },
  {
    "name": "get_shipping_policy",
    "description": "查询指定地区的通用物流政策，不返回具体订单状态。",
    "input_schema": {
      "properties": {
        "region": {
          "default": "CN",
          "type": "string"
        }
      },
      "type": "object"
    }
  }
]
```

注意这里的关系：

> Skill 正文说任务应该怎么做，MCP Server 返回当前真实可用的工具 schema，模型在二者交集里规划下一步工具调用。

## 七、模型规划 Tool Call，Host 执行 Tool Call

`plan_tool_call_node` 会把三类信息交给模型：

```text
用户任务
Skill 正文
Tool schemas
```

并要求模型返回结构化 JSON：

```json
{
  "tool": "<tool-name>",
  "arguments": {},
  "reason": "<简短原因>"
}
```

一次运行中，模型返回：

```json
{
  "tool": "get_order",
  "arguments": {
    "order_id": "O-1001"
  },
  "reason": "根据用户任务，需要查询订单 O-1001 的详细信息，因此调用 get_order 工具并传入订单号。"
}
```

这一步才是真正的“模型选择 MCP Tool”。它不是在唯一工具里被迫选择，而是在 `get_order` 和 `get_shipping_policy` 中选了正确工具。

模型返回后，Host 还会校验计划：

```python
_validate_tool_call_plan(plan, mcp_tools)
```

校验至少做两件事：

- 模型选择的工具名必须存在于 MCP Server 发现的工具列表里；
- `arguments` 必须是 JSON object。

真正执行工具的是 `execute_mcp_tool_node`：

```python
tool_result = call_tool(
    server_path=SERVER_PATH,
    cwd=HERE,
    tool_name=tool_name,
    arguments=arguments,
)
```

这仍然保持了阶段 10 的边界：

| 角色 | 本实验中的职责 |
| --- | --- |
| Skill | 描述订单报告任务应该如何做 |
| MCP Server | 暴露 `get_order` 与 `get_shipping_policy` 工具 |
| 模型 | 选择 Skill，并规划 MCP Tool call |
| Host | 扫描、加载、发现工具、校验计划、执行 Tool call |
| LangGraph | 保存状态、控制节点顺序、暂停和恢复 |

## 八、人工确认：写文件前暂停

工具执行后，`draft_report_node` 根据工具结果生成报告草稿：

```text
# 订单报告

- 订单号：O-1001
- 状态：paid
- 商品：耳机
- 金额：199 CNY
- 数据来源：stage11-order-report MCP get_order
```

接下来进入 `wait_for_approval_node`：

```python
decision = interrupt(
    {
        "question": "是否批准写入订单报告？回复批准/拒绝，并可附带原因。",
        "selected_skill": selected_skill,
        "output_path": output_path,
        "report_draft": report_draft,
    }
)
```

`interrupt(...)` 会让图停在这里。第一次运行 `pause` 时，输出里会出现 `__interrupt__`，并且 checkpoint 显示下一步仍然是 `wait_for_approval`：

```text
checkpoint_next: ('wait_for_approval',)
```

这时已经进入 checkpoint 的状态包括：

```text
selected_skill
skill_text
mcp_tools
tool_call_plan
tool_result
report_draft
trace
```

这就是 LangGraph 在这个实验里的价值：不是“画一张流程图”，而是在暂停时保住已经完成的中间状态。

## 九、批准或拒绝后如何恢复

人工批准时，运行：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py approve
```

`run_demo.py` 会发送：

```python
Command(resume="批准，写入报告。")
```

LangGraph 会从同一个 `thread_id` 的 checkpoint 恢复。它不会重新从 `scan_skills` 开始，而是回到 `interrupt(...)` 暂停点，把 `resume` 的内容作为 `interrupt(...)` 的返回值继续执行。

`choose_after_approval` 根据人工意见选择后续分支：

```python
def choose_after_approval(state: SkillGraphState) -> Literal["write_report", "final_answer"]:
    if _is_approved(state.get("approval", "")):
        return "write_report"
    return "final_answer"
```

批准时路径是：

```text
wait_for_approval
  -> write_report
  -> final_answer
  -> END
```

最终输出：

```text
已写入订单报告：.../outputs/order-report-demo.md
```

拒绝时运行：

```bash
uv run python labs/skills/foundations/examples/stage11-langgraph-skills/run_demo.py reject
```

路径变成：

```text
wait_for_approval
  -> final_answer
  -> END
```

这时不会进入 `write_report`，也不会产生文件写入副作用。

## 十、这个实验说明了什么

这个实验最终想说明三件事。

第一，Skills 和 LangGraph 不在同一层。

Skill 是任务方法。它回答：

```text
这类任务什么时候触发？
应该按什么步骤做？
需要使用哪些工具？
输出应该满足什么要求？
```

LangGraph 是状态流程。它回答：

```text
当前走到哪一步？
下一步去哪里？
哪些状态需要保存？
哪里需要暂停？
人工恢复后从哪里继续？
```

第二，加载 Skill 正文后，不应该直接硬编码工具调用。

更规范的链路应该是：

```text
load_skill
  -> discover_mcp_tools
  -> plan_tool_call
  -> execute_mcp_tool
```

因为 Skill 正文是一份操作手册，MCP Server 返回的是当前真实工具能力。模型应该在二者共同约束下提出 Tool Call，Host 再执行。

第三，LangGraph 的价值出现在状态边界上。

如果任务只是：

```text
查询订单 -> 回复一句话
```

普通 Python 顺序编排就够了。

但当任务变成：

```text
选择 Skill -> 加载正文 -> 发现工具 -> 规划工具调用 -> 执行工具 -> 生成报告 -> 写入前等待人工确认 -> 批准后恢复
```

这时 LangGraph 的 State、Edge、条件分支、checkpoint 和 `interrupt(...)` 才真正有意义。

## 十一、可以继续改进的地方

当前实验仍然是最小实验版，有几个刻意保留的简化：

1. 报告草稿由确定性代码生成，没有再交给模型改写。
2. `plan_tool_call` 只规划一次工具调用，没有实现多轮工具循环。
3. MCP Server 是 stdio 本地进程，没有引入远程 Server 和权限策略。
4. `write_report` 只演示文件写入，没有处理覆盖确认、幂等 ID 或审计日志。

这些都可以放到后续阶段继续做。阶段 11 的重点不是一次性做成生产级 Agent，而是先把职责边界摆正：

> Skills 管方法，MCP 管工具，LangGraph 管复杂状态流，Host 负责把它们稳定地串起来。
