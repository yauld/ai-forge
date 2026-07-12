# 10 | Skills + MCP：如何让 Skill 指导 MCP 工具调用

Skills 和 MCP 经常会一起出现，但它们不是同一种东西。

Skill 负责描述一类任务的做法：什么时候使用、按什么步骤做、需要哪些上下文、结果应该如何组织。MCP 负责把外部系统能力暴露给 Host：有哪些工具、参数 schema 是什么、调用后返回什么结果。

所以二者放在一起时，最小闭环不是“Skill 自己调用 MCP”，而是：

> Skill 说明当前任务应该使用哪个 MCP Server 的哪个 Tool；Host 读取 Skill，并把 MCP Tool schema 绑定给模型；模型提出 Tool Call；Host 再通过 MCP Client 真正调用 Server。

本实验只验证正常协作路径，不讨论危险操作确认、权限拦截或对抗输入。我们用一个订单查询场景，让本地 Ollama 模型 `qwen3-coder:30b` 按 Skill 指令调用一个最小 MCP Tool。

## 一、实验目标与配套文件

本实验回答一个问题：

> 一个 Skill 如何指导模型使用 MCP Server 暴露出来的 Tool？

具体目标有三个：

1. 用规范的 `SKILL.md` 描述订单查询任务，并保留 `name` 和 `description`。
2. 用 MCP Server 暴露一个真实工具 `get_order`。
3. 用 Host 把 Skill、Ollama 模型和 MCP Client 串成一次完整调用。

配套代码位于：

```text
labs/skills/foundations/examples/stage10-mcp-skill/
```

目录结构如下：

```text
stage10-mcp-skill/
├── README.md
├── host.py
├── mcp_server.py
└── skills/
    └── order-query/
        └── SKILL.md
```

这套代码故意保持很小：一个 Skill，一个 MCP Server，一个 Tool，一个 Host 入口。它不引入多 Skill 检索、不做 LangGraph 编排，也不把安全治理提前混进来。先看清正常链路，后面的复杂能力才有落点。

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

准备完成后，在仓库根目录运行：

```bash
uv run python labs/skills/foundations/examples/stage10-mcp-skill/host.py
```

默认任务是：

```text
帮我查一下订单 O-1001 的状态、商品和金额，并用一句话告诉我结果。
```

也可以指定另一个订单：

```bash
uv run python labs/skills/foundations/examples/stage10-mcp-skill/host.py \
  --task "帮我查一下订单 O-1002 的状态、商品和金额，并用一句话告诉我结果。"
```

## 三、这次请求会经历什么

整个链路可以拆成 7 步：

```text
User
  -> Host 扫描 Skill metadata
  -> Ollama 根据 name / description 选择 Skill
  -> Host 加载完整 SKILL.md
  -> Host 连接 MCP Server 并发现 Tool
  -> Host 把 MCP Tool schema 绑定给 Ollama
  -> Ollama 按 Skill 指令提出 Tool Call
  -> Host 调用 MCP Server，并把结果交回 Ollama 生成最终回答
```

这里有一个容易混淆的点：

> 绑定给模型的不是 MCP Tool 本身，而是 Tool 的说明书：名称、描述和参数 schema。

模型不会直接执行外部工具。模型只会提出类似下面这样的调用意图：

```json
{
  "name": "get_order",
  "args": {
    "order_id": "O-1001"
  }
}
```

真正执行工具的是 Host：

```python
result = await session.call_tool(tool_name, arguments)
```

这也是 Skill、Host、MCP Server 的核心分工：

| 角色 | 本实验中的职责 |
| --- | --- |
| Skill | 说明订单查询任务要使用 `stage10-order-query` MCP Server 的 `get_order` 工具 |
| Host | 扫描 Skill、连接 MCP Server、把 Tool schema 绑定给模型、执行 Tool Call |
| Ollama 模型 | 根据 Skill 正文和用户任务提出 Tool Call，并根据工具结果生成最终回答 |
| MCP Server | 暴露并执行真实工具 `get_order` |

## 四、Skill 如何描述 MCP 工具

`skills/order-query/SKILL.md` 的 frontmatter 保留了最小规范字段：

```yaml
---
name: order-query
description: 当用户需要查询订单状态、订单金额、商品名称或订单摘要时，使用这个 Skill。
---
```

其中：

- `name` 是 Skill 的稳定标识；
- `description` 用于发现和路由，帮助 Host 或模型判断用户任务是否应该命中这个 Skill。

正文里写清了 MCP 工具的使用方式：

```markdown
## 可用 MCP 工具

- 在 `stage10-order-query` MCP Server 中，有 `get_order` 工具。
- 完成订单查询任务时，需要使用这个工具读取订单状态、商品名称和金额。

## 执行步骤

1. 从用户请求中提取订单号，例如 `O-1001`。
2. 调用 `stage10-order-query` MCP Server 中的 `get_order` 工具查询订单信息。
3. 根据工具返回结果，用一句自然语言回复用户。
4. 不要编造工具结果中没有出现的信息。
```

这就是 Skills + MCP 的典型写法：Skill 不定义工具实现，也不直接执行工具；它告诉模型和 Host，当前任务应该使用哪个 MCP Server 的哪个 Tool，以及结果应该如何处理。

## 五、MCP Server 暴露什么

`mcp_server.py` 只做一件事：暴露 `get_order` Tool。

```python
mcp = FastMCP("stage10-order-query")

ORDERS: dict[str, dict[str, object]] = {
    "O-1001": {
        "order_id": "O-1001",
        "status": "paid",
        "amount": 199,
        "currency": "CNY",
        "product": "耳机",
    },
    "O-1002": {
        "order_id": "O-1002",
        "status": "paid",
        "amount": 88,
        "currency": "CNY",
        "product": "数据线",
    },
}
```

Tool 定义如下：

```python
@mcp.tool()
def get_order(order_id: str) -> dict[str, object]:
    """根据订单号查询订单状态、金额和商品名称。"""
    order = ORDERS.get(order_id)
    if order is None:
        return {
            "found": False,
            "order_id": order_id,
        }
    return {
        "found": True,
        "order": order,
    }
```

注意这里的边界：MCP Server 并不知道 Skill，也不关心用户原始任务。它只提供一个可调用能力：给我 `order_id`，我返回订单信息。

## 六、Host 如何把二者串起来

`host.py` 是本实验最关键的文件。它不是完整生产级 runtime，而是一个线性实验版 Host。

第一步，Host 扫描 `skills/*/SKILL.md`，只读取 metadata：

```python
skills = scan_skills(SKILLS_ROOT)
```

`scan_skills()` 只解析 frontmatter 里的 `name` 和 `description`：

```python
SkillMetadata(
    name=frontmatter["name"],
    description=frontmatter["description"],
    path=skill_file,
)
```

这样做是为了模拟 Skills 的渐进式披露：发现阶段只需要 metadata，不需要把完整 Skill 正文提前塞进模型上下文。

第二步，模型只根据 metadata 选择 Skill：

```python
selected_skill_name = route_skill(model, task, skills)
```

命中后，Host 才加载完整 `SKILL.md`：

```python
skill_text = selected_skill.path.read_text(encoding="utf-8")
```

第三步，Host 启动并连接 MCP Server：

```python
session = await connect_mcp(stack)
listed_tools = await session.list_tools()
```

`list_tools()` 返回的是 MCP Server 暴露出来的 Tool 定义。Host 随后把它转换成模型可见的工具 schema：

```python
model_tools = [
    {
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema,
    }
    for tool in listed_tools.tools
    if tool.name == "get_order"
]
tool_enabled_model = model.bind_tools(model_tools)
```

这一步很关键。模型不是直接拿到了 MCP 连接，也不是直接拿到了 Python 函数。模型拿到的是：

```text
工具名 + 工具描述 + 参数 schema
```

第四步，Host 把 Skill 正文、用户任务和 Tool schema 一起交给模型：

```python
messages = [
    SystemMessage(
        content=(
            "你正在作为 Host 中的执行模型工作。请严格按照下面的 Skill "
            "说明完成任务。需要查询订单时，使用已提供的 MCP 工具。\n\n"
            f"{skill_text}"
        )
    ),
    HumanMessage(content=task),
]

first_response = await tool_enabled_model.ainvoke(messages)
```

如果模型按 Skill 正文提出 Tool Call，Host 才真正调用 MCP Server：

```python
for tool_call in first_response.tool_calls:
    tool_name = tool_call["name"]
    arguments = tool_call["args"]
    result = await session.call_tool(tool_name, arguments)
```

最后，Host 把 MCP Tool 的结果作为 `ToolMessage` 交回模型：

```python
messages.append(
    ToolMessage(
        content=json.dumps(tool_result, ensure_ascii=False),
        tool_call_id=tool_call["id"],
    )
)

final_response = await tool_enabled_model.ainvoke(messages)
```

这时模型不再猜订单信息，而是基于真实 Tool 结果组织最终回答。

## 七、运行与观察

运行默认命令：

```bash
uv run python labs/skills/foundations/examples/stage10-mcp-skill/host.py
```

一次成功运行的关键输出如下：

```text
discovered_skills: [{"name": "order-query", "description": "当用户需要查询订单状态、订单金额、商品名称或订单摘要时，使用这个 Skill。"}]
route_result: {"skill": "order-query", "reason": "用户明确要求查询订单状态、商品名称和金额，完全符合order-query技能的描述。"}
loaded_skill: order-query
mcp_tools: ["get_order"]
model_tool_calls: [{"name": "get_order", "args": {"order_id": "O-1001"}, "id": "...", "type": "tool_call"}]
mcp_tool_result: {"tool": "get_order", "result": {"found": true, "order": {"order_id": "O-1001", "status": "paid", "amount": 199, "currency": "CNY", "product": "耳机"}}}
final_answer: 订单 O-1001 当前状态是 paid，商品是耳机，金额为 199 元。
```

这些输出分别证明了几件事。

`discovered_skills` 说明 Host 先发现了 Skill metadata：

```text
name = order-query
description = 当用户需要查询订单状态、订单金额、商品名称或订单摘要时，使用这个 Skill。
```

`route_result` 说明模型根据用户任务选择了 `order-query`。这一步还没有 MCP Tool 调用，只是 Skill 路由。

`mcp_tools` 说明 Host 已经连接 MCP Server，并通过 `list_tools()` 发现了 `get_order`。

`model_tool_calls` 是模型提出的调用意图：

```json
{
  "name": "get_order",
  "args": {
    "order_id": "O-1001"
  }
}
```

`mcp_tool_result` 是 MCP Server 返回的真实工具结果。最终回答里的状态、商品和金额都来自这里，而不是模型自己编出来的。

## 八、结论

这个最小实验可以得到一个清楚结论：

> Skill 负责说明当前任务应该怎么使用外部能力；MCP Server 负责暴露外部能力；Host 负责把二者接起来，并执行模型提出的 Tool Call。

更具体地说：

- Skill 正文可以写“在某个 MCP Server 里有某个 Tool，当前场景需要使用这个 Tool”。
- Host 通过 MCP Client 的 `list_tools()` 拿到 Tool 定义。
- Host 把 Tool 的名称、描述和参数 schema 绑定给模型。
- 模型根据 Skill 正文提出 Tool Call。
- Host 使用 `session.call_tool()` 调用 MCP Server。
- 模型基于 Tool 返回结果生成最终回答。

所以 Skills + MCP 的最小搭配不是把二者揉成一个东西，而是让它们各自站在正确的位置：

```text
Skill 描述任务方法
MCP 暴露外部工具
Host 串联 Skill、模型和 MCP 调用
```

如果只记一句话，可以记成：

> Skill 是 MCP 工具的使用说明书；MCP Server 是工具箱；Host 是真正拿起工具执行的人。
