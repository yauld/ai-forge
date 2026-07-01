# 06 | MCP Client：Host 如何发现并调用 Server 能力

前几篇已经从 Server 侧看过 MCP：

- Server 暴露 Tool、Resource 和 Prompt。
- Client 先 `initialize`，再发现和调用能力。
- 同一组 MCP 消息可以通过 stdio 或 Streamable HTTP 传递。

这一篇换到 Host 侧。我们写一个很小的 MCP Client 程序，让它同时连接两个本地 Server，发现它们分别提供什么能力，再把一次 tool call 路由到正确的 Server。

实验代码在：

```text
examples/multi_server_client.py
```

## 1. 这次实验回答什么问题

先记住一个核心判断：

> MCP Client 是 Host 内部连接某一个 MCP Server 的协议组件。

一个 Host 可以连接多个 Server，但通常不会把所有 Server 混成一个连接。更常见的做法是：

```text
Host
├─ ClientSession A → shop-order-analysis Server
└─ ClientSession B → shop-order-primitives Server
```

这样做有两个直接好处：

1. 每个 Server 的生命周期可以单独管理。
2. Host 能知道某个 Tool、Resource 或 Prompt 来自哪个 Server。

第二点尤其重要。真实 Host 不能只维护一张无来源的工具名列表，否则一旦多个 Server 出现同名能力，就不知道该把调用发给谁。

## 2. 实验会连接哪两个 Server

本实验复用前面已经写好的两个 stdio Server。

第一个是订单分析 Server：

```text
examples/shop_order_analysis_server.py
```

它提供：

- Resource：`shop://database/schema`
- Resource：`shop://business/metrics`
- Tool：`query_daily_order_summary`
- Tool：`list_orders_by_status`
- Prompt：`daily_order_analysis_report`

第二个是 primitives 对照 Server：

```text
examples/shop_order_primitives_server.py
```

它提供：

- Resource Template：`shop://orders/{order_id}`
- Tool：`get_order`
- Tool：`search_orders`
- Prompt：`analyze_one_order`

这两个 Server 都通过 stdio 启动，所以 Client 会负责启动它们的子进程，并在实验结束时关闭。

## 3. Host 配置：先写清楚要连接谁

先把 Host 要连接的两个 Server 写成常量：

```python
HERE = Path(__file__).resolve().parent

ANALYSIS_SERVER = HERE / "shop_order_analysis_server.py"
PRIMITIVES_SERVER = HERE / "shop_order_primitives_server.py"
```

这里先不引入复杂配置对象。阶段 6 的重点不是设计通用配置系统，而是看清 Host 如何连接 Server、发现能力和路由调用。

## 4. 为每个 Server 创建独立 ClientSession

连接一个 stdio Server 的核心代码是：

```python
parameters = StdioServerParameters(
    command=sys.executable,
    args=[str(server_script)],
    cwd=HERE,
)
read, write = await stack.enter_async_context(stdio_client(parameters))
session = await stack.enter_async_context(ClientSession(read, write))

await session.initialize()
```

这几行对应的是：

```text
Host 启动 Server 子进程
→ 建立 stdio transport
→ 创建 ClientSession
→ initialize
```

`AsyncExitStack` 用来统一管理多个异步上下文。实验结束离开 `async with AsyncExitStack()` 时，ClientSession 和 stdio 子进程都会被清理。

这就是 Client session 生命周期里最基本的一段：

```text
connect
→ initialize
→ discover capabilities
→ call/read/get
→ close
```

## 5. 发现能力：不要丢掉 Server 来源

初始化后，Client 可以分别发现四类能力：

```python
tools = await session.list_tools()
resources = await session.list_resources()
resource_templates = await session.list_resource_templates()
prompts = await session.list_prompts()
```

然后 Host 把结果保存到自己的能力目录：

```python
capability_directory = {
    "shop-order-analysis": await discover_capabilities(analysis_session),
    "shop-order-primitives": await discover_capabilities(primitives_session),
}
```

运行实验：

```bash
uv run labs/mcp/foundations/examples/multi_server_client.py
```

会看到类似输出：

```text
=== Host capability directory ===

[shop-order-analysis]
tools: ['query_daily_order_summary', 'list_orders_by_status']
resources: ['shop://database/schema', 'shop://business/metrics']
resource_templates: []
prompts: ['daily_order_analysis_report']

[shop-order-primitives]
tools: ['get_order', 'search_orders']
resources: []
resource_templates: ['shop://orders/{order_id}']
prompts: ['analyze_one_order']
```

这份目录是 Host 的视角。它不是 MCP 协议里的新 primitive，而是 Host 为了后续选择、展示、校验和路由能力而维护的本地数据结构。

## 6. 调用同一个 Server 的三类能力

先在 `shop-order-analysis` 这个 Server 上分别调用 Tool、读取 Resource、获取 Prompt。

调用订单汇总 Tool：

```python
tool_result = await session.call_tool(
    "query_daily_order_summary",
    {
        "start_date": "2026-06-19",
        "end_date": "2026-06-25",
    },
)
```

读取数据库 schema Resource：

```python
resource_result = await session.read_resource(AnyUrl("shop://database/schema"))
```

获取日报 Prompt：

```python
prompt_result = await session.get_prompt(
    "daily_order_analysis_report",
    {"date_range": "2026-06-19 到 2026-06-25"},
)
```

这三次请求都由同一个 `ClientSession` 发给同一个 Server，但语义不同：

| 类型 | Client 方法 | 含义 |
| --- | --- | --- |
| Tool | `call_tool` | 执行一个动作 |
| Resource | `read_resource` | 读取一份上下文 |
| Prompt | `get_prompt` | 获取一组任务消息模板 |

Client 只负责协议调用。至于这些结果要不要交给模型、如何交给模型、是否需要用户确认，是 Host 的职责。

## 7. 多 Server 路由：调用意图必须带来源

现在模拟一个 Host 已经决定要调用的 tool call intent：

```python
intent = {
    "server": "shop-order-primitives",
    "tool": "get_order",
    "arguments": {"order_id": "O-1001"},
}
```

这里故意让 `intent` 带上 `server`。因为 Host 不能只知道“要调用 `get_order`”，还必须知道“要调用哪个 Server 上的 `get_order`”。

路由函数很小：

```python
async def route_tool_call(
    sessions: dict[str, ClientSession],
    capability_directory: dict[str, dict[str, list[str]]],
    intent: dict[str, Any],
) -> Any:
    server_id = intent["server"]
    tool_name = intent["tool"]
    arguments = intent.get("arguments", {})

    if server_id not in sessions:
        raise ValueError(f"Unknown MCP server: {server_id}")

    tools = capability_directory[server_id]["tools"]
    if tool_name not in tools:
        raise ValueError(f"Server {server_id} does not provide tool {tool_name}")

    return await sessions[server_id].call_tool(tool_name, arguments)
```

这段代码做了两层校验：

1. `server` 是否是 Host 已连接的 Server。
2. `tool` 是否确实由这个 Server 提供。

通过校验后，Host 才使用对应 Server 的 `ClientSession` 发起 `call_tool`。

运行结果里会看到：

```text
=== Routed tool call ===
intent: {'server': 'shop-order-primitives', 'tool': 'get_order', 'arguments': {'order_id': 'O-1001'}}
result: {'result': {'found': True, 'order': {'order_id': 'O-1001', ...}}}
```

这就是多 Server 场景下最基本的路由模型：

```text
tool call intent
→ 读取 server 字段
→ 找到对应 ClientSession
→ 校验 tool 是否属于该 Server
→ call_tool
```

## 8. 为什么这篇没有接真实大模型

真实 AI 应用里，Host 可能会把 Tool 描述交给模型，模型再产生工具调用意图。

但这一步不是 MCP Client 的核心。MCP Client 只关心：

- 如何连接 Server。
- 如何完成初始化。
- 如何发现能力。
- 如何发起协议调用。
- 如何关闭连接。

模型如何选择工具，是 Host 和模型提供商 API 之间的另一层问题。为了把阶段 6 学清楚，这里先用一个手写的 `intent` 模拟“Host 已经决定要调用哪个工具”。

这样可以避免把学习目标混在一起：

```text
本篇重点：MCP Client 与 Server 通信。
暂不展开：模型如何选择 Tool、Host 如何组织完整 Agent 循环。
```

## 9. 小结

这一阶段可以压缩成四句话：

- Host 通常为每个 MCP Server 维护独立 Client 连接。
- `ClientSession` 负责初始化、能力发现和协议调用。
- Host 保存能力目录时，要保留能力来自哪个 Server。
- 多 Server tool call 不能只看工具名，必须路由到正确的 Server 连接。

读完这一篇，你应该能独立写出一个小型 MCP Client：连接本地 Server，发现 Tool、Resource、Prompt，执行一次调用，并在多个 Server 之间做基本路由。

下一篇可以进入调试：当 Server 启动失败、stdio 被污染、初始化失败或 Tool 调用异常时，应该从哪一层开始定位。

## 10. 参考资料

- https://modelcontextprotocol.io/docs/develop/build-client
- https://modelcontextprotocol.io/docs/develop/clients/client-best-practices
