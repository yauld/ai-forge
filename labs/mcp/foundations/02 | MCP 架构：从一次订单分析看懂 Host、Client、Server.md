# 02 | MCP 架构：从一次订单分析看懂 Host、Client、Server

设想一个很常见的业务问题：

> 运营同学在AI应用里问：最近 7 天订单表现怎么样？有没有异常？

模型只理解这句话还不够。它还需要知道订单数据在哪里、表中有哪些字段、指标口径是什么，以及通过什么方式查询数据。要让这些环节真正连起来，背后需要三个角色协作：Host、Client 和 Server。

本文将围绕这个真实但足够小的订单分析场景，拆解一次 MCP 交互是如何发生的：AI 应用怎样连接 Server、发现能力、调用工具，并最终生成分析结果。

这里的 Cursor 或 Claude Desktop 是用户直接操作的 AI 应用，也就是 MCP Host，后文简称 Host。

## 1. 先看整体架构

先用一条链路把角色放回架构里：

```text
用户
  ↓
AI 应用（MCP Host）
  ↓
MCP Client
  ↓
MCP Server
  ↓
外部系统
```

Host 就是前面说的 AI 应用（MCP Host）的简称。Client 是 Host 内部的协议组件。在这个案例里，Server 作为订单数据库的适配层，向 Host 暴露能力。

这一篇重点关注中间这段：

```text
Host
  ↓
Client
  ↓
Server
```

也就是：Host 如何连接 Server、发现能力、调用能力，再把结果交给模型使用。

## 2. 这次实验的业务场景

业务问题是：

> 最近 7 天订单表现怎么样？有没有异常？

为了回答这个问题，Host 需要三类能力：

- 先知道订单表有哪些字段，以及业务指标怎么算。
- 再查询订单汇总和异常订单明细。
- 最后按固定分析结构输出一份中文日报。

这正好对应 MCP Server 暴露的三类能力：

| MCP 能力 | 实验里的名字 | 业务含义 |
| --- | --- | --- |
| Resource | `shop://database/schema` | 订单表结构和字段说明 |
| Resource | `shop://business/metrics` | 订单数、成交额、退款数、客单价等指标口径 |
| Prompt | `daily_order_analysis_report` | 订单日报分析任务模板 |
| Tool | `query_daily_order_summary` | 查询一段日期内的每日订单汇总 |
| Tool | `list_orders_by_status` | 查询某类订单明细，例如退款订单 |

可以把这张表当作本文的实验地图：后面的代码和 Inspector 页面都会围绕这五个能力展开。

## 3. Server 是怎么实现的

实验代码在：

```text
examples/shop_order_analysis_server.py
```

这个文件用本地 SQLite 模拟外部订单数据库。真实业务里，这一层可以替换成 MySQL、PostgreSQL、数据仓库或业务 API。

先看 Server 初始化：

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("shop-order-analysis")
```

`FastMCP("shop-order-analysis")` 创建了一个 MCP Server。这个名字会在 MCP Inspector 连接成功后显示出来。

### 3.1 用 SQLite 模拟外部系统

Server 里先准备了一批样例订单：

```python
DATA_DIR = Path(__file__).with_name("data")
DB_PATH = DATA_DIR / "shop_orders.sqlite"

SAMPLE_ORDERS = [
    ("O-1001", "2026-06-19", "paid", 199.0, "华东", "耳机"),
    ("O-1006", "2026-06-21", "refunded", 399.0, "华南", "机械键盘"),
    ("O-1014", "2026-06-25", "refunded", 1299.0, "华东", "相机"),
]
```

完整示例代码里样例数据更多，这里只摘几行。每一行代表一条订单记录：

```text
order_id, order_date, status, amount, region, product
```

`ensure_database()` 会创建 `orders` 表，并写入样例数据：

```python
def ensure_database() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id TEXT PRIMARY KEY,
                order_date TEXT NOT NULL,
                status TEXT NOT NULL,
                amount REAL NOT NULL,
                region TEXT NOT NULL,
                product TEXT NOT NULL
            )
            """
        )
        conn.execute("DELETE FROM orders")
        conn.executemany(
            """
            INSERT INTO orders
                (order_id, order_date, status, amount, region, product)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            SAMPLE_ORDERS,
        )
```

这一步对应 MCP 架构里的“外部系统”。在本实验里，外部系统就是本地 SQLite 订单库。

### 3.2 Resource：提供订单上下文

订单表结构适合做成 resource，因为它是一份上下文资料，不是一次查询动作。

```python
@mcp.resource("shop://database/schema")
def database_schema() -> str:
    """读取订单数据库的表结构和字段含义。"""
    return """# 订单数据库 Schema

表名：orders

| 字段 | 含义 |
| --- | --- |
| order_id | 订单编号 |
| order_date | 下单日期，格式为 YYYY-MM-DD |
| status | 订单状态：paid 已支付，cancelled 已取消，refunded 已退款 |
| amount | 订单金额，单位：元 |
| region | 用户所在区域 |
| product | 商品名称 |
"""
```

业务指标口径也适合做成 resource：

```python
@mcp.resource("shop://business/metrics")
def business_metrics() -> str:
    """读取订单分析里的业务指标口径。"""
    return """# 订单分析指标口径

- 订单数：指定日期范围内的订单总数。
- 成交额：status = paid 的订单金额总和。
- 已支付订单数：status = paid 的订单数量。
- 取消订单数：status = cancelled 的订单数量。
- 退款订单数：status = refunded 的订单数量。
- 客单价：成交额 / 已支付订单数。
"""
```

这两个 resource 的作用是让 Host 拿到“怎么看懂订单数据”的业务上下文，并在需要时提供给模型。这里不再展开 resource 的通用定义，重点看它在这次订单分析里的位置：它是后续分析前需要读取的业务资料。

### 3.3 Prompt：提供分析流程模板

这个 prompt 负责把订单分析任务组织成稳定流程。

```python
@mcp.prompt()
def daily_order_analysis_report(date_range: str = "2026-06-19 到 2026-06-25") -> str:
    """生成一份订单日报分析提示词模板。"""
    return f"""你是一名电商数据分析助手，请分析 {date_range} 的订单表现。

请按下面步骤完成：

1. 先读取 `shop://database/schema`，理解 orders 表字段。
2. 再读取 `shop://business/metrics`，理解订单数、成交额、取消数、退款数、客单价的计算口径。
3. 调用 `query_daily_order_summary` 查询日期范围内的每日汇总。
4. 如果取消或退款明显偏高，再调用 `list_orders_by_status` 查看明细。
5. 最后用中文输出一份简短日报。

注意：不要编造数据库里没有的数据。
"""
```

它的重点是“如何问、按什么流程分析”，不是“直接查数据”。

这个 prompt 看起来有点像一个小型 skill，但在 MCP 里它仍然只是 prompt：它负责生成一组可复用 messages，不负责自动选择工具，也不负责执行整个工作流。

换句话说，prompt 只是把“怎么问、按什么步骤分析”包装起来；真正读取 resource、调用 tool、把结果交给模型，仍然由 Host 来安排。

### 3.4 Tool：真正查询订单数据

订单汇总查询会带着参数去外部系统查询数据，所以在这个案例里设计成 tool。下面省略了 `parse_date()` 和 `rows_to_dicts()` 两个辅助函数，完整代码见文件。

```python
@mcp.tool()
def query_daily_order_summary(start_date: str, end_date: str) -> dict[str, object]:
    """按日期查询订单数、成交额、取消数和退款数。"""
    start = parse_date(start_date)
    end = parse_date(end_date)
    ensure_database()

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT
                order_date,
                COUNT(*) AS order_count,
                SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) AS paid_amount,
                SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_count,
                SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_count,
                SUM(CASE WHEN status = 'refunded' THEN 1 ELSE 0 END) AS refunded_count
            FROM orders
            WHERE order_date BETWEEN ? AND ?
            GROUP BY order_date
            ORDER BY order_date
            """,
            (start, end),
        )
        rows = rows_to_dicts(cursor)

    total_paid_amount = sum(float(row["paid_amount"] or 0) for row in rows)
    total_paid_count = sum(int(row["paid_count"] or 0) for row in rows)
    avg_order_value = (
        round(total_paid_amount / total_paid_count, 2) if total_paid_count else 0
    )

    return {
        "date_range": f"{start} 到 {end}",
        "daily_rows": rows,
        "summary": {
            "paid_amount": round(total_paid_amount, 2),
            "paid_count": total_paid_count,
            "cancelled_count": sum(int(row["cancelled_count"] or 0) for row in rows),
            "refunded_count": sum(int(row["refunded_count"] or 0) for row in rows),
            "avg_order_value": avg_order_value,
        },
    }
```

完整代码在 `examples/shop_order_analysis_server.py`。文章里保留这段，是为了让你看到 tool 不是静态说明，而是真的会带着参数去查询数据库。

退款订单明细查询也是 tool：

```python
@mcp.tool()
def list_orders_by_status(
    status: Literal["paid", "cancelled", "refunded"],
    limit: int = 5,
) -> list[dict[str, object]]:
    """按订单状态查看明细，用于排查取消或退款订单。"""
    ensure_database()
    safe_limit = max(1, min(limit, 20))

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            """
            SELECT order_id, order_date, status, amount, region, product
            FROM orders
            WHERE status = ?
            ORDER BY order_date DESC, order_id DESC
            LIMIT ?
            """,
            (status, safe_limit),
        )
        return rows_to_dicts(cursor)
```

这里有一个真实工具设计里很常见的小细节：`limit` 会被限制在 1 到 20 之间，避免一次返回太多数据。

### 3.5 启动 Server

最后通过 stdio transport 启动：

```python
def main() -> None:
    ensure_database()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

这个 Server 不是直接给人打开看的，而是给 MCP Client 连接的。

## 4. 用 MCP Inspector 连接 Server

为了先看清架构职责和连接生命周期，这里不手写 Client，而是用官方 MCP Inspector 作为客户端侧调试工具。

启动命令：

```bash
npx -y @modelcontextprotocol/inspector \
  uv run --script examples/shop_order_analysis_server.py
```

前半段 `npx -y @modelcontextprotocol/inspector` 表示按需运行 MCP 官方 Inspector；后半段 `uv run --script examples/shop_order_analysis_server.py` 是传给 Inspector 的 Server 启动命令。也就是说，Inspector 会用这条 Python 命令启动订单分析 MCP Server，并通过 stdio 和它通信。

命令执行后，浏览器会自动打开 MCP Inspector 页面：

![Inspector 初始页面：尚未连接 Server](assets/02-inspector-initial-disconnected.png)

此时 Inspector 已经启动，但还没有真正连接到 MCP Server。底部的 `Disconnected` 说明还没有发生 `initialize`，也还没有发现 resources、prompts 和 tools。

下一步点击左侧的 `Connect`，Inspector 才会启动订单分析 MCP Server，并进入连接、初始化和能力发现流程。

## 5. 连接成功：initialize 已经发生

点击 `Connect` 后，Inspector 会启动并连接订单分析 Server。

![Inspector 已连接订单分析 MCP Server](assets/02-inspector-connected.png)

这张图里最重要的是三处：

- 左侧显示 `Connected`，说明 Inspector 已经作为客户端侧连接上 Server。
- Server 名称是 `shop-order-analysis`，对应代码里的 `FastMCP("shop-order-analysis")`。
- History 里出现 `initialize`，说明 Client 和 Server 已经完成初始化和能力协商。

一次 MCP 连接通常会经历这些步骤：

```text
1. Host 根据配置启动或连接 MCP Server。
2. Host 内部的 MCP Client 和 Server 建立 transport。
3. Client 发送 initialize 请求。
4. Server 返回自己的协议版本、serverInfo 和 capabilities。
5. Client 发送 notifications/initialized。
6. Host/Client 开始发现 tools、resources、prompts。
```

在真正使用工具之前，双方需要先确认“我是谁、我支持什么协议版本、我有哪些能力、你能接受什么能力”。这就是 `initialize` 和 capability negotiation 的意义。

## 6. 看 Resources：上下文从哪里来

在 Resources 页面点击 `List Resources`，再打开 `database_schema`。

![Resources 页面读取订单数据库 schema](assets/02-inspector-resources-schema.png)

这张图对应代码里的：

```python
@mcp.resource("shop://database/schema")
def database_schema() -> str:
    ...
```

这里的 `database_schema` 不是查询动作，而是一份上下文资料。它告诉 Host，或者说告诉后续会接收上下文的模型：orders 表有哪些字段，`status` 的取值分别代表什么。

所以 resource 的重点是“给模型看懂业务和数据”，不是“执行查询”。

## 7. 看 Prompts：任务模板从哪里来

在 Prompts 页面点击 `List Prompts`，选择 `daily_order_analysis_report`，填写日期范围后点击 `Get Prompt`。

![Prompts 页面获取订单日报分析模板](assets/02-inspector-prompts-report.png)

这张图对应代码里的：

```python
@mcp.prompt()
def daily_order_analysis_report(date_range: str = "2026-06-19 到 2026-06-25") -> str:
    ...
```

Prompt 不会自己查询数据库。它返回的是一组 messages，用来告诉模型应该按什么流程分析：先读 resources，再调用 tools，最后输出中文日报。

所以 prompt 的重点是“组织任务表达”，不是“提供数据”，也不是“执行动作”。

## 8. 看 Tools：外部动作如何被调用

在 Tools 页面点击 `List Tools`，可以看到两个业务动作。

![Tools 页面发现订单查询工具](assets/02-inspector-tools-list.png)

`query_daily_order_summary` 用来查日期范围内的订单汇总，`list_orders_by_status` 用来查某种状态的订单明细。

打开 `query_daily_order_summary`，填写：

```json
{ "start_date": "2026-06-19", "end_date": "2026-06-25" }
```

![填写订单汇总 tool 的输入参数](assets/02-inspector-tool-input.png)

这里对应代码里的函数参数：

```python
def query_daily_order_summary(start_date: str, end_date: str) -> dict[str, object]:
```

点击 `Run Tool` 后，Server 会查询 SQLite 订单数据库，并把结果返回给 Inspector。

![订单汇总 tool 返回查询结果](assets/02-inspector-tool-result-summary.png)

这一步才是“执行动作”。如果换成真实业务系统，这里可能就是查询 MySQL、调用订单 API 或访问数据仓库。

History 里会出现 `tools/call`，说明这是一次 MCP tool 调用。

## 9. 把页面串回 MCP 架构

现在把 Inspector 页面和 MCP 架构对应起来：

| Inspector 页面 | 背后的 MCP 行为 | 对应代码 | 业务含义 |
| --- | --- | --- | --- |
| Connected + History `initialize` | Client 和 Server 初始化、协商能力 | `mcp.run(transport="stdio")` | 连接订单分析 Server |
| Resources / `database_schema` | `resources/list` + `resources/read` | `@mcp.resource(...)` | 读取表结构上下文 |
| Prompts / `daily_order_analysis_report` | `prompts/list` + `prompts/get` | `@mcp.prompt()` | 获取日报分析模板 |
| Tools / `query_daily_order_summary` | `tools/list` + `tools/call` | `@mcp.tool()` | 查询订单汇总 |
| Tool Result | Server 返回 tool 调用结果 | `return {...}` | 把数据库结果交回 Host |

如果用户问：

> 最近 7 天订单表现怎么样？有没有异常？

理想流程不是模型直接去查数据库，而是：

```text
1. Host 连接订单分析 MCP Server。
2. Server 告诉 Host：我有订单 schema、指标口径、订单查询工具和日报 prompt。
3. 模型根据用户问题判断：需要先理解数据，再查询订单。
4. Host 读取 `shop://database/schema` 和 `shop://business/metrics`。
5. 模型基于这些上下文提出 tool call 意图。
6. Host 调用 `query_daily_order_summary`。
7. 如果发现退款或取消异常，再调用 `list_orders_by_status`。
8. Server 查询 SQLite 数据库并返回结果。
9. Host 把结果交给模型。
10. 模型按照 `daily_order_analysis_report` 的结构输出中文分析。
```

注意，这里要区分 Inspector 和真实 Host 的边界。Inspector 可以帮我们验证到这一步：

```text
Inspector 发现能力
  ↓
读取 resources 理解业务上下文
  ↓
获取 prompt 组织分析任务
  ↓
调用 tools 查询订单数据库
```

如果换成 Cursor、Claude Desktop 这类真实 Host，才会继续多出下一步：Host 把必要上下文和 tool result 交给模型，由模型生成最终的中文分析。

## 10. Host 如何把这些信息交给模型

前面我们看到，Inspector 可以从 Server 发现 resources、prompts 和 tools，也可以读取 resource、获取 prompt、调用 tool。

这一步是上一篇只简要提过、本文需要讲清楚的地方：真实 Host 还会决定哪些信息进入模型上下文。

更准确的链路是：

```text
MCP Server 返回能力描述或调用结果
  ↓
MCP Client 把协议结果交给 Host
  ↓
Host 决定给模型看什么、什么时候给、以什么形式给
  ↓
模型基于这些上下文推理、生成 tool call 意图或最终回答
```

不同能力进入模型上下文的方式也不一样：

| MCP 返回的信息 | Host 通常如何使用 | 模型通常会拿到什么 |
| --- | --- | --- |
| `tools/list` 返回 tool 名称、描述、输入 schema | Host 整理成模型可用的工具说明 | 模型知道有什么工具、参数怎么填 |
| `resources/read` 返回 resource 内容 | Host 选择是否放进上下文 | 模型看到订单 schema、指标口径等资料 |
| `prompts/get` 返回 prompt messages | Host 把它作为对话消息或任务模板 | 模型按稳定结构完成分析 |
| `tools/call` 返回 tool result | Host 把结果交回模型 | 模型基于真实查询结果组织回答 |

以订单分析为例，模型通常不会直接看到数据库连接。它看到的是 Host 提供的工具说明、订单 schema、指标口径，以及 tool 调用后的查询结果。

所以这一层边界可以这样记：

> Server 负责暴露和返回能力；Host 负责管理、筛选和注入模型上下文；模型负责推理和生成。

## 11. 小结

这篇文章的重点不是重新定义 MCP，而是看懂一条连接如何跑起来：

- Host 通过 Client 连接 Server，而不是模型直接连接 Server。
- `initialize` 和 capability negotiation 发生在能力发现和调用之前。
- Server 暴露的 resources、prompts、tools 可以在 Inspector 里被发现、读取和调用。
- Tool 调用结果会先返回 Host，再由 Host 决定如何提供给模型。
- MCP Inspector 可以帮助我们先看清连接生命周期，再去写真正的 Client。

到这里，你就能把 MCP 从“概念定义”推进到“运行结构”。下一步再深入 tools、resources、prompts 的协议细节，就会更自然。

## 12. 参考资料

- MCP 架构概览：https://modelcontextprotocol.io/docs/learn/architecture
- MCP Server 开发：https://modelcontextprotocol.io/docs/develop/build-server
- MCP Inspector：https://modelcontextprotocol.io/docs/tools/inspector
- MCP Python SDK：https://github.com/modelcontextprotocol/python-sdk
