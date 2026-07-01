# MCP 实战专题

这个专题用一个电商订单分析场景，解释 MCP 在 AI 应用架构中的位置，以及 Host、Client、Server、Tool、Resource、Prompt 如何协作。

MCP 不只是“另一种工具调用写法”。它更像一层上下文能力协议：让 AI 应用可以发现外部系统能力，读取上下文，调用工具，并把这些能力组织成可复用、可检查、可演进的接口。

## 你会学到什么

- MCP 为什么会出现在 AI 应用架构里。
- Host、Client、Server 分别负责什么。
- Tool、Resource、Prompt 的边界如何划分。
- JSON-RPC 消息、初始化和能力发现如何工作。
- 如何围绕真实业务系统设计、运行和调试 MCP 能力。

## 适合读者

- 想理解 MCP 架构和协议边界的开发者。
- 想把内部系统、数据库或业务 API 接入 AI 应用的人。
- 正在设计 Agent 工具生态、上下文能力层或企业内部 AI 平台的人。

## 研究路线

表格同时记录已有成果和后续研究计划。已有文件可直接打开；尚未创建的文件使用计划名称占位。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [MCP 是什么：先把它放回 AI 应用架构里理解.md](01%20%7C%20MCP%20是什么：先把它放回%20AI%20应用架构里理解.md) | MCP 到底是什么，解决了什么连接问题？ | 已完成 |
| 02 | [MCP 架构：从一次订单分析看懂 Host、Client、Server.md](02%20%7C%20MCP%20架构：从一次订单分析看懂%20Host、Client、Server.md) | Host、Client、Server 如何在一次订单分析中协作？ | 已完成 |
| 03 | [MCP Tool、Resource、Prompt：从会用到会设计.md](03%20%7C%20MCP%20Tool、Resource、Prompt：从会用到会设计.md) | 一个能力应该设计成哪种 Server Primitive？ | 已完成 |
| 04 | [MCP 通信过程：从 initialize 到 tools-call.ipynb](04%20%7C%20MCP%20通信过程：从%20initialize%20到%20tools-call.ipynb) | 从 `initialize` 到 `tools/call`，MCP 消息如何流动？ | 已完成 |
| 05 | [MCP Transport：stdio 与 Streamable HTTP 如何传递消息.md](05%20%7C%20MCP%20Transport：stdio%20与%20Streamable%20HTTP%20如何传递消息.md) | 同一组消息如何通过 stdio 和 Streamable HTTP 传递？ | 已完成 |
| 06 | [MCP Client：Host 如何发现并调用 Server 能力.md](06%20%7C%20MCP%20Client：Host%20如何发现并调用%20Server%20能力.md) | Host 如何发现多个 Server 的能力并正确路由调用？ | 已完成 |
| 07 | [MCP 调试：从 Server 启动失败到 Tool 调用异常.md](07%20%7C%20MCP%20调试：从%20Server%20启动失败到%20Tool%20调用异常.md) | 如何按进程、Transport、生命周期、能力发现和执行逐层定位失败？ | 已完成 |
| 08 | `MCP 安全：权限、授权与危险 Tool 的确认边界.md` | 谁可以访问什么能力，高风险 Tool 应如何确认和审计？ | 待研究 |
| 09 | `MCP Registry、Extensions 与生态.md` | 如何区分核心协议、扩展、实验能力和特定 Client 行为？ | 待研究 |

## 示例项目

示例代码集中在 [examples](examples)。它们共享一个小型 SQLite 订单数据库，用来模拟真实业务系统。

| 文件 | 作用 |
| --- | --- |
| [shop_order_analysis_server.py](examples/shop_order_analysis_server.py) | 订单分析 MCP Server，包含 schema resource、指标口径 resource、订单汇总 tool、订单明细 tool 和日报 prompt。 |
| [shop_order_primitives_server.py](examples/shop_order_primitives_server.py) | 用单笔订单查询对比 Resource Template 与 Tool 的边界。 |
| [shop_order_transport_server.py](examples/shop_order_transport_server.py) | 复用同一组订单能力，通过 stdio 或 Streamable HTTP 启动 Server。 |
| [transport_client.py](examples/transport_client.py) | 分别通过 stdio 和 Streamable HTTP 执行同一条 MCP Tool 调用。 |
| [multi_server_client.py](examples/multi_server_client.py) | 连接两个 stdio Server，发现能力目录，并按 Server 来源路由 Tool 调用。 |
| [broken_stdout_server.py](examples/broken_stdout_server.py) | 故意污染 stdout，用来观察 stdio 协议通道被普通日志干扰时的表现。 |
| [debug_order_server.py](examples/debug_order_server.py) | 提供 schema 契约错误、慢查询和数据库异常等可重复故障。 |
| [debug_client.py](examples/debug_client.py) | 按进程、Transport、发现和执行层运行阶段 7 调试实验。 |
| [shop_orders.sqlite](examples/data/shop_orders.sqlite) | 启动示例时自动生成或刷新，用于保存订单样例数据。 |
