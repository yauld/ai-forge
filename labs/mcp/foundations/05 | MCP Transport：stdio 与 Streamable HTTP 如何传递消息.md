# 05 | MCP Transport：stdio 与 Streamable HTTP 如何传递消息

上一篇已经沿着下面这条链路观察过 MCP 消息：

```text
initialize
→ notifications/initialized
→ tools/list
→ tools/call
```

但当时还有一个问题没有回答：

> 同样的 JSON-RPC 消息，究竟怎样从 Client 到达 Server？

本文保持订单能力不变，分别通过 stdio 和 Streamable HTTP 连接同一个 Server。重点不是再设计一组 Tool，而是分清两个层次：

- Data layer 决定消息表达什么，例如 `initialize`、`tools/list` 和 `tools/call`。
- Transport layer 决定消息怎样传递，例如 Client 进程通过 Server 子进程的 stdin/stdout 通信，或者通过 HTTP endpoint 通信。

实验代码位于：

```text
examples/shop_order_transport_server.py
examples/transport_client.py
examples/broken_stdout_server.py
```

## 1. 先理解 stdio 和 Streamable HTTP

在 MCP 里，stdio 和 Streamable HTTP 都是 transport。transport 的意思很朴素：消息从 Client 传到 Server，要走哪条路。

MCP 真正传递的内容仍然是 JSON-RPC 消息，例如：

```text
initialize
tools/list
tools/call
```

stdio 和 Streamable HTTP 的区别，不是“消息内容不同”，而是“消息走的通道不同”。

### 1.1 stdio 是什么

stdio 是 standard input / output 的缩写，也就是一个进程最基础的标准输入和标准输出。

可以先把它理解成：

```text
Client 进程启动一个 Server 子进程；
Client 进程把 MCP 请求消息写入 Server 子进程的 stdin；
Server 子进程从自己的 stdin 读取请求，处理后把 MCP 响应消息写入自己的 stdout；
Client 进程再从 Server 子进程的 stdout 读取响应。
```

所以 stdio 模式通常不需要你提前手动启动 Server。Client 会启动它，并通过这个 Server 子进程的 stdin/stdout 和它对话。

它适合本地工具、桌面应用、命令行程序这类场景。比如一个 AI IDE 想调用你电脑上的本地脚本，就很适合用 stdio。

stdio 有一个重要约束：

> Server 子进程的 stdout 是 MCP 协议通道，不能随便打印普通日志。

如果 Server 子进程往自己的 stdout 打印了普通文字，Client 可能会把这段文字当成 JSON-RPC 消息解析，于是出错。普通日志应该写到 Server 子进程自己的 stderr。

### 1.2 Streamable HTTP 是什么

Streamable HTTP 可以先理解成“通过 HTTP 暴露一个 MCP endpoint”。

它的关系是：

```text
先启动 MCP HTTP Server
Client 连接 http://127.0.0.1:8000/mcp
Client 通过 HTTP 请求发送 MCP 消息
Server 通过 HTTP 响应返回 MCP 消息
```

所以 Streamable HTTP 模式下，要先启动 Server，再运行 Client。

它适合独立服务、远程访问、Web 后端、容器部署这类场景。Server 不一定和 Client 在同一个进程树里，也不一定由 Client 启动。

名字里的 Streamable 表示：这个 HTTP transport 不只支持普通的一问一答，也可以在需要时用流式方式返回消息。对初学者来说，先记住它是“HTTP 版的 MCP 通信方式”就够了。

### 1.3 先用一句话区分

```text
stdio：Client 进程启动 Server 子进程，并通过 Server 子进程的 stdin/stdout 通信。
Streamable HTTP：Server 先独立启动，Client 通过 HTTP endpoint 通信。
```

理解了这点，再看下面的实验就简单很多：我们不是在改订单 Tool，而是在切换同一组 MCP 消息的传输通道。

## 2. Transport 没有改变 Server 的业务能力

第三篇的订单 Server 已经提供：

- Resource Template：`shop://orders/{order_id}`
- Tool：`get_order`
- Tool：`search_orders`
- Prompt：`analyze_one_order`

这个 Server 没有重新实现这些能力，而是直接复用原来的 `mcp` 实例：

```python
from shop_order_primitives_server import ensure_database, mcp
```

启动时只选择 transport：

```python
def main() -> None:
    args = parse_args()
    ensure_database()
    mcp.run(transport=args.transport)
```

可选值是：

```text
stdio
streamable-http
```

这正是本次实验要建立的第一个直觉：

> Tool、Resource 和 Prompt 属于 MCP 能力层；stdio 和 Streamable HTTP 是这些能力所使用的传输方式。

切换 transport，不需要重写 `get_order` 的输入 Schema、输出结构或查询逻辑。

## 3. stdio：Client 启动并管理 Server 子进程

先运行 stdio 实验：

```bash
uv run labs/mcp/foundations/examples/transport_client.py stdio
```

Client 使用当前 Python 解释器启动 Server：

```python
parameters = StdioServerParameters(
    command=sys.executable,
    args=[str(server), "--transport", "stdio"],
    cwd=HERE,
)

async with stdio_client(parameters) as streams:
    ...
```

进程关系是：

```text
transport_client.py
  └─ 启动 shop_order_transport_server.py
       ├─ stdin：Client 进程把 MCP 请求消息写到这里
       ├─ stdout：Server 子进程把 MCP 响应消息写到这里，Client 从另一端读取
       └─ stderr：Server 子进程把普通日志写到这里
```

stdio transport 中，每条消息都是一行 UTF-8 JSON-RPC。消息之间用换行符分隔，消息内部不能包含未转义的换行。

例如第四篇里的 `tools/call`，在 stdio 中可以理解为：

```text
Client 进程向 Server 子进程的 stdin 写入一行 JSON
→ Server 子进程从自己的 stdin 读取这行 JSON，并执行 get_order
→ Server 子进程把结果作为一行 JSON 写入自己的 stdout
→ Client 进程从 Server 子进程的 stdout 读取这行 JSON
```

实验输出的关键部分是：

```text
transport: stdio
protocol: 2025-11-25
tools: ['get_order', 'search_orders']
isError: False
structuredContent: {
  'result': {
    'found': True,
    'order': {
      'order_id': 'O-1001',
      ...
    }
  }
}
```

这里仍然经历了初始化、能力发现和 Tool 调用，只是 SDK 帮我们管理了底层读写。

### 3.1 为什么 stdout 不能打印普通日志

stdio 把 Server 子进程的 stdout 当作协议通道。Server 子进程写入自己 stdout 的每一行，都应该是一条合法 MCP 消息。

`broken_stdout_server.py` 故意违反这条规则：

```python
print("这是一条不应该出现在 stdout 的普通日志", flush=True)
mcp.run(transport="stdio")
```

运行：

```bash
uv run \
  labs/mcp/foundations/examples/transport_client.py stdio \
  --server labs/mcp/foundations/examples/broken_stdout_server.py
```

Client 会把这行文字当成 JSON-RPC 消息解析，并报告：

```text
Failed to parse JSONRPC message from server
Invalid JSON: expected value at line 1 column 1
```

当前实验使用的 Python SDK 会记录这条解析错误，然后继续处理后续合法消息；其他 Client 不一定会恢复，也可能直接断开连接。因此 Server 不应依赖 Client 的容错行为。

普通日志应该写入 Server 子进程自己的 stderr，例如：

```python
print("Server 已启动", file=sys.stderr)
```

stdio Server 的规则可以压缩成一句话：

> Client 进程只向 Server 子进程的 stdin 写 MCP 消息；Server 子进程只向自己的 stdout 写 MCP 消息；普通日志写 Server 子进程自己的 stderr。

## 4. Streamable HTTP：Server 独立监听 HTTP endpoint

stdio 中，Client 通常负责启动 Server 子进程。Streamable HTTP 中，Server 是一个独立运行的 HTTP 服务，Client 连接它暴露的 MCP endpoint。

先启动 Server：

```bash
uv run \
  labs/mcp/foundations/examples/shop_order_transport_server.py \
  --transport streamable-http
```

当前示例默认监听：

```text
http://127.0.0.1:8000/mcp
```

再打开另一个终端运行 Client：

```bash
uv run labs/mcp/foundations/examples/transport_client.py streamable-http
```

Client 的连接代码变成：

```python
async with streamable_http_client(url) as (read, write, _):
    ...
```

但连接建立后，上层代码没有变化：

```python
async with ClientSession(read, write) as session:
    initialized = await session.initialize()
    tools = await session.list_tools()
    result = await session.call_tool(
        "get_order",
        {"order_id": "O-1001"},
    )
```

输出也与 stdio 实验一致：

```text
transport: streamable-http
protocol: 2025-11-25
tools: ['get_order', 'search_orders']
isError: False
structuredContent: {
  'result': {
    'found': True,
    'order': {
      'order_id': 'O-1001',
      ...
    }
  }
}
```

这说明 `initialize`、`tools/list`、`tools/call` 和 Tool Result 仍然属于同一套 MCP 语义。改变的是承载消息的方式。

## 5. Streamable HTTP 实际增加了什么

Streamable HTTP 不是简单地把一行 JSON 换成一个 HTTP 请求。它还定义了 HTTP 层的交互规则。

### 5.1 Client 通过 POST 发送消息

Client 发给 Server 的每条 JSON-RPC 消息，都使用一个新的 HTTP POST 请求发送到同一个 MCP endpoint。

请求体是一条 JSON-RPC request、notification 或 response。

如果直接实现 HTTP Client，需要按规范处理 HTTP header 和响应类型。当前实验使用 Python SDK，这些细节由下面这一行封装了：

```python
async with streamable_http_client(url) as (read, write, _):
    ...
```

所以本文先不展开 HTTP header、SSE 响应和 session 管理，只关注最核心的变化：Client 不再启动 Server 子进程，而是连接一个 HTTP endpoint。

### 5.2 暂时不用深入的 HTTP 细节

Streamable HTTP 还有一些更细的机制，比如：

- Server 可以选择是否提供额外的流式推送通道。
- Server 可以选择是否使用 session ID。
- Client 和 Server 会通过 HTTP header 携带一些协议信息。

这些内容属于“把 HTTP transport 做完整”时才需要深入理解的细节。当前实验只需要抓住主线：

> Streamable HTTP 模式下，Server 先独立启动；Client 通过 `/mcp` 这个 HTTP endpoint 发送和接收 MCP 消息。

## 6. 同一条调用，哪些变了，哪些没变

用一张表对照本次实验：

| 观察项 | stdio | Streamable HTTP |
| --- | --- | --- |
| MCP 方法 | `initialize`、`tools/list`、`tools/call` | 相同 |
| Tool 名称和参数 | `get_order`、`O-1001` | 相同 |
| Tool Result | 相同的结构化订单结果 | 相同 |
| Server 运行方式 | Client 启动子进程 | Server 独立监听 endpoint |
| 消息载体 | Client 进程写 Server 子进程的 stdin；Server 子进程写自己的 stdout | HTTP 请求和响应 |
| 普通日志 | Server 子进程写自己的 stderr | Server 日志系统 |
| 额外关注点 | stdout 不能打印普通日志 | endpoint、端口、HTTP 状态码 |

因此，“MCP 与 transport 分层”并不表示 transport 无关紧要。更准确的理解是：

- MCP 方法、参数和结果不因 transport 改变。
- 连接建立、消息 framing、错误表现和关闭方式由 transport 决定。

## 7. Streamable HTTP 多了一层网络边界

HTTP Server 即使只运行在本机，也多了一层网络边界。

本次实验使用：

```text
http://127.0.0.1:8000/mcp
```

这表示 Server 只监听本机地址，适合学习和本地实验。

这里先记住一个边界就够了：

> 从 stdio 切换到 Streamable HTTP，不只是换一个启动参数，也意味着 Server 变成了一个 HTTP 服务。

认证、授权、Origin 校验、session 安全这些内容，放到后续安全主题再展开。

## 8. 应该选择哪种 Transport

不要简单记成“本地用 stdio，远程用 HTTP”。Streamable HTTP 同样可以运行在 localhost。

更实用的判断方式是：

**优先考虑 stdio：**

- Server 由 Host 启动和管理。
- 能力只服务当前 Host 或当前用户。
- 希望用操作系统进程边界隔离连接。
- 不需要独立部署和网络访问。

**优先考虑 Streamable HTTP：**

- Server 需要独立运行。
- 多个 Client 需要访问同一服务。
- Client 和 Server 可能位于不同机器。
- 需要统一处理认证、网关、监控或伸缩。

核心问题不是数据来自文件还是数据库，而是：

> 谁管理 Server，它部署在哪里，哪些 Client 可以跨越什么信任边界访问它？

## 9. 小结

本文最重要的不是记住两段 SDK 代码，而是分清协议消息与传输方式。

- stdio 中，Client 进程启动 Server 子进程，并把 MCP 请求写入 Server 子进程的 stdin。
- Server 子进程把 MCP 响应写入自己的 stdout；普通日志写入自己的 stderr。
- Streamable HTTP 使用统一 MCP endpoint，通过 HTTP 请求和响应传递 MCP 消息。
- 切换 transport 不改变 Tool、Resource、Prompt 及其 MCP 方法。
- HTTP 会增加 endpoint、端口、状态码和网络边界。

## 参考资料

- MCP Transports：https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Lifecycle：https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
