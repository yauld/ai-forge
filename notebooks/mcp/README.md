# MCP 实战

这个目录记录 MCP 在 AI 应用架构中的位置，以及 Tool、Resource、Prompt、Host、Client、Server 如何协作。

## 推荐路线

| 阶段 | 内容 | 文件 |
| --- | --- | --- |
| 架构定位 | MCP 是什么，以及为什么要把它放回 AI 应用架构里理解 | [01](<01 | MCP 是什么：先把它放回 AI 应用架构里理解.md>) |
| 角色协作 | 通过订单分析理解 Host、Client、Server | [02](<02 | MCP 架构：从一次订单分析看懂 Host、Client、Server.md>) |
| 能力设计 | Tool、Resource、Prompt 的边界与设计方式 | [03](<03 | MCP Tool、Resource、Prompt：从会用到会设计.md>) |
| 通信过程 | 从 `initialize` 到 `tools/call` 理解 MCP 通信 | [04](<04 | MCP 通信过程：从 initialize 到 tools-call.ipynb>) |

## 示例代码

- [examples/shop_order_analysis_server.py](examples/shop_order_analysis_server.py)：订单分析 MCP Server。
- [examples/shop_order_primitives_server.py](examples/shop_order_primitives_server.py)：Tool、Resource、Prompt primitives 示例。
- [examples/data/shop_orders.sqlite](examples/data/shop_orders.sqlite)：订单示例数据。

## 重点主题

- MCP 不是“又一个工具调用写法”，而是把上下文能力协议化。
- Host、Client、Server 的边界决定了能力发现、调用和结果返回的职责。
- Tool 适合执行动作，Resource 适合暴露上下文，Prompt 适合沉淀可复用任务模板。
- 一个好的 MCP Server 不只是能调用，还要考虑输入校验、错误返回、资源命名和能力说明。

## 适合读者

- 想理解 MCP 架构和协议边界的开发者。
- 想把内部系统能力接入 AI 应用的人。
- 正在设计 Agent 工具生态的人。

## 下一步

读完 MCP 后，可以继续进入：

- [LangGraph 实战](../langgraph)：把 MCP 能力放进可控工作流。
- [LangChain 实战](../langchain)：理解工具调用和 Agent 运行时控制。
