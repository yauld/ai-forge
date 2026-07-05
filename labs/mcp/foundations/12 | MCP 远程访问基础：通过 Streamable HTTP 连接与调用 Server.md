# MCP 远程访问基础：通过 Streamable HTTP 连接与调用 Server

前面的实验主要关心 MCP 消息、能力设计和安全边界。即使已经见过
Streamable HTTP，也可能还缺少一个最基本的使用直觉：

> 一个 MCP Server 独立运行以后，另一个进程究竟怎样找到并调用它？

本文暂时不加入 OAuth、Token 和权限控制，只完成最小远程访问：

```text
启动 MCP Server
→ Client 按 URL 建立连接
→ initialize
→ tools/list
→ tools/call
```

完成实验后，你应该能：

- 解释 MCP 中的“远程 Server”是什么意思；
- 看懂一个 MCP URL 的主机、端口和 endpoint；
- 区分 stdio 与 Streamable HTTP 的启动和连接方式；
- 独立启动 Server，再用 Client 连接并调用 Tool；
- 区分服务未启动、endpoint 错误和 Tool 执行错误。

## 1. “远程”到底是什么意思

远程 Server 最重要的特征不是“部署在公网”，而是：

> Server 独立运行，Client 不负责启动它，而是通过网络地址连接它。

两个程序即使运行在同一台电脑上，只要 Server 独立监听 HTTP 地址，Client 通过
URL 连接，就已经具备远程访问的基本结构。

本地实验的进程关系是：

```text
终端一
remote_connection_server.py
  └─ 监听 http://127.0.0.1:8001/mcp

终端二
remote_connection_client.py
  └─ 连接上述 URL
       → initialize
       → tools/list
       → tools/call
```

这与 stdio 的差别很直接：

| 对比项 | stdio | Streamable HTTP |
| --- | --- | --- |
| 谁启动 Server | Client 通常启动 Server 子进程 | 运维、终端或服务平台独立启动 |
| Client 连接什么 | 子进程的 stdin/stdout | MCP URL |
| Server 是否持续运行 | 通常随 Client 一起退出 | 可以独立持续运行 |
| 常见使用场景 | 本机工具 | 独立服务、局域网或互联网服务 |

MCP 消息仍然是 `initialize`、`tools/list` 和 `tools/call`。变化的是消息经过
Streamable HTTP 传输，不是 Tool 的业务含义。

## 2. MCP URL 是怎样组成的

实验使用：

```text
http://127.0.0.1:8001/mcp
```

它可以拆成四部分：

| 部分 | 当前值 | 含义 |
| --- | --- | --- |
| 协议 | `http://` | 本地实验使用 HTTP |
| 主机 | `127.0.0.1` | 当前电脑自身 |
| 端口 | `8001` | Server 监听的网络端口 |
| endpoint | `/mcp` | 接收 MCP 消息的 HTTP 路径 |

Client 必须拿到完整 URL。只知道“Server 在 8001 端口”还不够；如果把 `/mcp`
写成 `/wrong`，HTTP 请求虽然能到达这台 Server，却找不到 MCP endpoint。

地址会随部署位置变化：

```text
本机实验：http://127.0.0.1:8001/mcp
局域网：http://192.168.1.20:8001/mcp
正式服务：https://mcp.example.com/mcp
```

正式服务通常由域名、HTTPS、反向代理或网关提供稳定入口。下一阶段再讨论谁有权
访问这个入口。本阶段的无授权 Server 只绑定 `127.0.0.1`，不要直接暴露到公网。

## 3. 实验代码为什么只有两个文件

实验文件如下：

| 文件 | 作用 |
| --- | --- |
| `examples/remote_connection_server.py` | 独立启动订单查询 MCP Server |
| `examples/remote_connection_client.py` | 按 URL 连接并调用 `get_order` |

Server 继续复用现有订单查询代码，没有另造业务案例：

```python
from shop_order_primitives_server import OrderFound, OrderNotFound, find_order
```

实验不需要授权服务、浏览器回调、自定义 HTTP Client 或 Token 存储。我们只观察
最基本的远程连接。

## 4. Server：独立监听一个 MCP endpoint

Server 的关键配置只有一行：

```python
mcp = FastMCP("shop-order-remote", host="127.0.0.1", port=8001)
```

它表示：

- 只接受当前电脑发来的连接；
- 监听 `8001` 端口；
- Streamable HTTP 默认使用 `/mcp` endpoint。

然后注册一个只读订单查询 Tool：

```python
@mcp.tool(...)
def get_order(order_id: str) -> OrderFound | OrderNotFound:
    order = find_order(order_id)
    if order is None:
        return OrderNotFound(order_id=order_id, message=f"订单 {order_id} 不存在")
    return OrderFound(order=order)
```

最后以 Streamable HTTP 运行：

```python
mcp.run(transport="streamable-http")
```

运行到这里时，Server 会持续等待请求。它不知道之后由哪个 Client 连接，也不会
主动启动 Client。

## 5. Client：根据 URL 建立 MCP Session

Client 默认使用本地实验地址，也允许从命令行传入其他 URL：

```python
MCP_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8001/mcp"
```

真正的连接代码是：

```python
async with streamable_http_client(MCP_URL) as (read, write, _):
    async with ClientSession(read, write) as session:
        initialized = await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("get_order", {"order_id": "O-1001"})
```

可以把它分成三层理解：

1. `MCP_URL` 告诉 Client 去哪里连接；
2. `streamable_http_client()` 建立 HTTP 通道，提供 `read` 和 `write`；
3. `ClientSession` 在通道上发送标准 MCP 消息。

这里没有手写：

```python
http_client.post(...)
```

因为我们要进行的是 MCP 通信，不是自行拼装普通 HTTP 请求。Python SDK 会处理
Streamable HTTP 所需的请求、响应和 Session 细节。

## 6. 运行第一次远程调用

仓库要求 Python 3.13 或更高版本，依赖由 `pyproject.toml` 管理。第一次运行时
先在仓库根目录执行：

```bash
uv sync
```

打开终端一，启动 Server：

```bash
uv run labs/mcp/foundations/examples/remote_connection_server.py
```

看到下面的信息，说明 Server 已经监听端口：

```text
Uvicorn running on http://127.0.0.1:8001
```

这行只显示 HTTP 服务的基础地址。Client 仍要连接完整的 MCP endpoint：

```text
http://127.0.0.1:8001/mcp
```

保持终端一运行，再打开终端二：

```bash
uv run labs/mcp/foundations/examples/remote_connection_client.py
```

真实输出为：

```text
连接地址：http://127.0.0.1:8001/mcp
协议版本：2025-11-25
发现 Tools：['get_order']
调用结果：{'result': {'found': True, 'order': {
    'order_id': 'O-1001',
    'order_date': '2026-06-19',
    'status': 'paid',
    'amount': 199.0,
    'region': '华东',
    'product': '耳机'
}}}
```

这段输出形成了三项证据：

- 协议版本证明 `initialize` 已完成；
- Tool 列表证明 Client 已完成能力发现；
- 订单结果证明 `tools/call` 已到达 Server 并执行。

## 7. 三类失败分别说明什么

### 7.1 Server 没有启动

先停止终端一的 Server，再运行 Client。底层错误包含：

```text
httpx.ConnectError: All connection attempts failed
```

这时 TCP 连接都没有建立，还没有进入 MCP 初始化，更没有执行 Tool。优先检查：

- Server 进程是否运行；
- 主机与端口是否正确；
- 网络或防火墙是否允许连接。

### 7.2 endpoint 写错

保持 Server 运行，给 Client 传入错误路径：

```bash
uv run \
  labs/mcp/foundations/examples/remote_connection_client.py \
  http://127.0.0.1:8001/wrong
```

Server 日志会显示：

```text
POST /wrong HTTP/1.1 404 Not Found
```

这说明主机和端口可达，但 URL 路径不是 MCP endpoint。应检查 `/mcp`，而不是去查
Tool 实现。

### 7.3 Tool 调用失败

如果 Client 已经打印协议版本和 Tool 列表，说明连接、HTTP endpoint 和 MCP
初始化都成功了。此后 `tools/call` 的参数校验或业务错误才属于 Tool 执行层。

因此排查顺序可以记成：

```text
进程是否运行
→ 主机和端口是否可达
→ endpoint 是否正确
→ MCP initialize 是否成功
→ Tool 是否存在、参数和业务是否正确
```

## 8. 从本地实验走向真正的远程机器

如果 Server 与 Client 位于不同电脑，概念没有变化，只需要让 Server 监听可被
外部访问的网络接口，并让 Client 使用 Server 的实际地址。

例如，Server 可能监听：

```python
FastMCP("shop-order-remote", host="0.0.0.0", port=8001)
```

`0.0.0.0` 表示监听本机所有网络接口，但它不是 Client 应填写的目标地址。假设
Server 的局域网 IP 是 `192.168.1.20`，Client 使用：

```text
http://192.168.1.20:8001/mcp
```

真实生产环境还需要处理：

- HTTPS 与证书；
- 域名和反向代理；
- 防火墙、超时与负载均衡；
- 身份认证与权限控制；
- 日志、监控和高可用。

这些工程问题不会改变 MCP Client 的核心入口：它最终仍连接一个 Streamable HTTP
URL。下一阶段先加入最关键的授权边界。

## 9. 本实验的边界

本实验已经证明：

- Server 可以脱离 Client 独立运行；
- Client 可以通过 URL 建立 MCP Session；
- `initialize`、`tools/list` 和 `tools/call` 可以通过 Streamable HTTP 完成；
- 错误端口、错误 endpoint 和 Tool 错误发生在不同层次。

本阶段最终要记住的是：

> 远程 MCP Server 是一个独立运行的服务；Client 不启动它，而是根据完整 MCP
> URL 建立 Streamable HTTP 通道，再在这条通道上完成标准 MCP 会话。

官方参考：

- [MCP Transports](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [MCP Python SDK：Streamable HTTP](https://github.com/modelcontextprotocol/python-sdk#streamable-http-transport)
