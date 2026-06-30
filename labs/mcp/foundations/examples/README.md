# MCP 示例代码

这个目录保存 MCP 专题的可运行示例。示例使用一个小型电商订单数据库，模拟 AI 应用如何通过 MCP 读取上下文、调用工具并生成分析任务。

## 文件说明

| 文件 | 说明 |
| --- | --- |
| [shop_order_analysis_server.py](shop_order_analysis_server.py) | 第二篇文章使用的订单分析 MCP Server。 |
| [shop_order_primitives_server.py](shop_order_primitives_server.py) | 第三篇文章使用的 Tool、Resource、Prompt primitives 对照示例。 |
| [data/shop_orders.sqlite](data/shop_orders.sqlite) | 示例 SQLite 数据库。Server 启动时会自动创建并刷新数据。 |

## 准备环境

在仓库根目录安装依赖：

```bash
uv sync
```

MCP Inspector 通过 `npx` 启动，因此本机还需要可用的 Node.js / npm 环境。

## 运行订单分析 Server

在仓库根目录执行：

```bash
npx -y @modelcontextprotocol/inspector \
  uv run --no-sync --script labs/mcp/foundations/examples/shop_order_analysis_server.py
```

这个 Server 提供：

- Resource: `shop://database/schema`
- Resource: `shop://business/metrics`
- Tool: `query_daily_order_summary`
- Tool: `list_orders_by_status`
- Prompt: `daily_order_analysis_report`

可以在 Inspector 里尝试：

- 读取 `shop://database/schema`
- 调用 `query_daily_order_summary`，参数：

```json
{
  "start_date": "2026-06-19",
  "end_date": "2026-06-25"
}
```

- 调用 `list_orders_by_status`，参数：

```json
{
  "status": "refunded",
  "limit": 5
}
```

## 运行 primitives 对照示例

在仓库根目录执行：

```bash
npx -y @modelcontextprotocol/inspector \
  uv run --no-sync python labs/mcp/foundations/examples/shop_order_primitives_server.py
```

这个 Server 提供：

- Resource Template: `shop://orders/{order_id}`
- Tool: `get_order`
- Tool: `search_orders`
- Prompt: `analyze_one_order`

可以在 Inspector 里尝试：

- 读取 resource：`shop://orders/O-1001`
- 调用 `get_order`，参数：

```json
{
  "order_id": "O-1001"
}
```

- 调用 `search_orders`，参数：

```json
{
  "status": "paid",
  "min_amount": 500,
  "limit": 5
}
```

## 设计观察

- `shop://orders/O-1001` 是稳定、可寻址的上下文，适合 Resource Template。
- `search_orders` 需要动态筛选条件，适合 Tool。
- `daily_order_analysis_report` 和 `analyze_one_order` 把常见分析任务沉淀成 Prompt。
- 示例数据库每次启动都会刷新，保证实验结果稳定。

## 常见问题

如果 Inspector 启动后看不到能力列表，先确认命令是在仓库根目录执行。

如果 `uv run --no-sync` 报缺少依赖，先运行：

```bash
uv sync
```

如果 `npx` 不可用，先安装 Node.js / npm，或使用你本机已有的 MCP Inspector 启动方式。
