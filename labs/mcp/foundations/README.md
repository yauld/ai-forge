# MCP 实战专题

这个专题用一个电商订单分析场景，解释 MCP 在 AI 应用架构中的位置，以及 Host、Client、Server、Tool、Resource、Prompt 如何协作。

MCP 不只是“另一种工具调用写法”。它更像一层上下文能力协议：让 AI 应用可以发现外部系统能力，读取上下文，调用工具，并把这些能力组织成可复用、可检查、可演进的接口。

## 你会学到什么

- MCP 为什么会出现在 AI 应用架构里。
- Host、Client、Server 分别负责什么。
- Tool、Resource、Prompt 的边界如何划分。
- 为什么订单查询、订单详情和订单日报适合用不同 MCP primitive 表达。
- 一个可运行的 MCP Server 应该如何组织输入校验、错误返回、能力说明和示例数据。

## 适合读者

- 想理解 MCP 架构和协议边界的开发者。
- 想把内部系统、数据库或业务 API 接入 AI 应用的人。
- 正在设计 Agent 工具生态、上下文能力层或企业内部 AI 平台的人。
- 读过公众号短文后，希望继续看完整代码、截图和运行细节的读者。

## 学习路线

建议按顺序阅读。前两篇先建立架构直觉，第三篇进入能力设计，第四篇再看通信过程。

| 顺序 | 主题 | 解决的问题 | 文件 |
| --- | --- | --- | --- |
| 01 | 架构定位 | MCP 到底是什么，为什么要放回 AI 应用架构里理解 | [MCP 是什么](<01 | MCP 是什么：先把它放回 AI 应用架构里理解.md>) |
| 02 | 角色协作 | Host、Client、Server 如何在一次订单分析里协作 | [MCP 架构](<02 | MCP 架构：从一次订单分析看懂 Host、Client、Server.md>) |
| 03 | 能力设计 | Tool、Resource、Prompt 各自适合表达什么能力 | [MCP primitives](<03 | MCP Tool、Resource、Prompt：从会用到会设计.md>) |
| 04 | 通信过程 | 从 `initialize` 到 `tools/call`，MCP 消息如何流动 | [MCP 通信过程](<04 | MCP 通信过程：从 initialize 到 tools-call.ipynb>) |

## 示例项目

示例代码集中在 [examples](examples)。它们共享一个小型 SQLite 订单数据库，用来模拟真实业务系统。

| 文件 | 作用 |
| --- | --- |
| [examples/shop_order_analysis_server.py](examples/shop_order_analysis_server.py) | 订单分析 MCP Server，包含 schema resource、指标口径 resource、订单汇总 tool、订单明细 tool 和日报 prompt。 |
| [examples/shop_order_primitives_server.py](examples/shop_order_primitives_server.py) | 用单笔订单查询对比 Resource Template 与 Tool 的边界。 |
| [examples/data/shop_orders.sqlite](examples/data/shop_orders.sqlite) | 启动示例时自动生成/刷新，用于保存订单样例数据。 |

运行方式见 [examples/README.md](examples/README.md)。

## 快速运行

在仓库根目录执行：

```bash
uv sync
```

启动订单分析 Server：

```bash
npx -y @modelcontextprotocol/inspector \
  uv run --no-sync --script notebooks/mcp/examples/shop_order_analysis_server.py
```

启动 Tool、Resource、Prompt primitives 示例：

```bash
npx -y @modelcontextprotocol/inspector \
  uv run --no-sync python notebooks/mcp/examples/shop_order_primitives_server.py
```

如果你只想看文章，可以先读前 3 篇；如果你想理解 MCP 的实际消息流，再打开第 4 篇 Notebook。

## 公众号配套

公众号文章负责讲清楚问题、架构直觉和工程判断；这个目录保留完整代码、截图、Notebook 和可复现实验。

稳定入口：

```text
https://github.com/yauld/ai-forge/tree/main/notebooks/mcp
```

## 设计要点

- Resource 适合暴露上下文，例如数据库 schema、业务指标口径、可寻址的订单详情。
- Tool 适合执行动作，例如按日期查询订单汇总、按状态筛选订单。
- Prompt 适合沉淀可复用任务模板，例如生成订单日报分析提示词。
- Server 需要在边界处做输入校验，不能假设 Host 或模型永远传入正确参数。
- Tool annotations 可以给 Host 提供风险提示，但不能替代真正的权限控制和业务校验。

## 下一步

读完 MCP 后，可以继续进入：

- [LangGraph 实战](../langgraph)：把 MCP 能力放进可控工作流。
- [LangChain 实战](../langchain)：理解工具调用和 Agent 运行时控制。
