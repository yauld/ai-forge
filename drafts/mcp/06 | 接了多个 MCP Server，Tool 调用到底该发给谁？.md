# 06 | 接了多个 MCP Server，Tool 调用到底该发给谁？

一个 AI 应用只连接一个 MCP Server 时，调用 Tool 看起来很简单：

```text
模型想调用 get_order
→ Client 发送 tools/call
→ Server 返回订单
```

但真实应用往往不止接一个 Server。

比如，一个 Server 负责订单分析，另一个负责订单详情；以后还可能继续接入文件、知识库和工单系统。此时 Host 收到一条调用意图：

```json
{
  "tool": "get_order",
  "arguments": {
    "order_id": "O-1001"
  }
}
```

问题来了：

> `get_order` 属于哪个 Server，这次调用应该发到哪条连接？

这不是模型多猜一次就能解决的问题，而是 Host 必须处理的路由问题。

## 1. MCP Client 不是所有 Server 共用的一条万能连接

先把三个角色的关系说清楚：

- Host 是承载 AI 应用、管理上下文和执行策略的一方。
- MCP Client 是 Host 内部与某个 MCP Server 通信的协议组件。
- MCP Server 对外提供 Tool、Resource 和 Prompt。

一个 Host 可以连接多个 Server，但每个 Server 通常有自己的 Client 连接：

```text
Host
├─ ClientSession A → 订单分析 Server
└─ ClientSession B → 订单详情 Server
```

每条连接都要单独经历初始化、能力发现、调用和关闭。

这样做并不是为了把架构画得更热闹，而是因为每个 Server 都有独立的生命周期和能力集合。订单分析 Server 退出，不应该让订单详情 Server 的连接也变得不可识别；调用订单详情 Tool，也不能把消息误发给订单分析 Server。

所以更准确的理解是：

> Host 连接多个 Server，不是把它们塞进一个 Client，而是管理多组“Server 与 Client 连接”的对应关系。

## 2. 能力发现之后，Host 还要记住能力来自哪里

Client 完成初始化后，可以向 Server 查询它提供的能力：

```python
tools = await session.list_tools()
resources = await session.list_resources()
resource_templates = await session.list_resource_templates()
prompts = await session.list_prompts()
```

假设两个 Server 返回了这些结果：

```text
订单分析 Server
  tools: query_daily_order_summary, list_orders_by_status
  resources: shop://database/schema
  prompts: daily_order_analysis_report

订单详情 Server
  tools: get_order, search_orders
  resource templates: shop://orders/{order_id}
  prompts: analyze_one_order
```

如果 Host 发现完能力后，只合并成一张扁平名单：

```text
query_daily_order_summary
list_orders_by_status
get_order
search_orders
```

来源信息就丢了。

在只有两个 Tool 名称不重复的 Server 时，这个问题可能暂时没有暴露。等多个 Server 都提供 `search`、`query` 或 `get_status`，Host 就无法只凭 Tool 名找到正确连接。

因此，Host 更适合按 Server 保存能力目录：

```python
capability_directory = {
    "shop-order-analysis": {
        "tools": [
            "query_daily_order_summary",
            "list_orders_by_status",
        ],
    },
    "shop-order-primitives": {
        "tools": [
            "get_order",
            "search_orders",
        ],
    },
}
```

这份“能力目录”不是 MCP 新增的一类 primitive，而是 Host 为选择、展示、校验和路由能力维护的本地数据。

MCP Server 负责报告“我有什么”，Host 负责记住“谁有什么”。

## 3. Tool 调用意图必须包含 Server 来源

当 Host 已经决定执行一次 Tool 调用时，调用意图不能只有 Tool 名和参数，还应该包含 Server 标识：

```python
intent = {
    "server": "shop-order-primitives",
    "tool": "get_order",
    "arguments": {"order_id": "O-1001"},
}
```

随后，Host 至少要做两层检查：

```text
这个 Server 是否已经连接？
→ 这个 Tool 是否真的由该 Server 提供？
→ 找到对应 ClientSession
→ 发起 call_tool
```

对应的核心代码并不复杂：

```python
server_id = intent["server"]
tool_name = intent["tool"]

if server_id not in sessions:
    raise ValueError(f"Unknown MCP server: {server_id}")

if tool_name not in capability_directory[server_id]["tools"]:
    raise ValueError(
        f"Server {server_id} does not provide tool {tool_name}"
    )

result = await sessions[server_id].call_tool(
    tool_name,
    intent["arguments"],
)
```

这里最重要的并不是这几行 Python，而是调用发生前的判断顺序。

Host 不能因为模型输出了一个看起来存在的 Tool 名，就随便选一条连接发送。它要先确认 Server 是自己已经连接和管理的对象，再确认 Tool 确实出现在该 Server 的能力目录中。

能力发现因此不只是“给模型看看有哪些工具”，它也是 Host 后续校验调用来源的依据。

## 4. Client 负责协议调用，Host 负责决策

同一个 `ClientSession` 可以完成多种 MCP 操作：

```python
await session.call_tool(...)
await session.read_resource(...)
await session.get_prompt(...)
```

Client 知道如何把这些操作转换成 MCP 请求，并通过对应连接发送给 Server。

但它不负责决定：

- 哪些能力要暴露给模型；
- 模型提出的调用是否可信；
- 危险操作是否需要用户确认；
- Tool 结果是否应该进入模型上下文；
- 多个 Server 中应该选择哪一个。

这些都属于 Host 的职责。

这也是为什么实验里可以不接真实大模型，直接手写一条调用意图。模型如何选择 Tool，和 Client 如何连接、发现及调用 Server，是两层不同的问题。

把两层拆开后，链路会清楚很多：

```text
模型或应用产生调用意图
→ Host 选择并校验 Server 与 Tool
→ MCP Client 通过对应连接发送请求
→ MCP Server 执行并返回结果
```

如果把路由责任模糊地推给 Client，或者把模型输出直接当成可执行地址，多 Server 接入越多，调用边界就越容易失控。

## 5. 多 Server 接入，真正要维护的是对应关系

接入多个 MCP Server 时，可以先检查四件事：

1. 每个 Server 是否有独立、可管理的 Client 连接；
2. 能力目录是否保留了 Server 来源；
3. 调用意图是否同时包含 Server、Tool 和参数；
4. Host 是否在发送前校验 Tool 确实属于目标 Server。

最后把核心判断压缩成一句话：

> 多 Server 场景下，Host 不能只知道“有哪些 Tool”，还必须知道“每个 Tool 属于谁”，才能把调用发到正确的 Client 连接。

## 6. 完整文章与实验代码

公众号只保留多 Server 能力发现与路由的核心判断。完整运行方法和可执行代码放在 GitHub：

GitHub 仓库：

```text
https://github.com/yauld/ai-forge
```

完整实验文章：

```text
labs/mcp/foundations/06 | MCP Client：Host 如何发现并调用 Server 能力.md
```

