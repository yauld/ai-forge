# LangGraph 实战

这个目录记录如何用 LangGraph 构建可控、可恢复、可检查的 AI 工作流和 Agent 流程。

## 推荐路线

| 阶段 | 内容 | 文件范围 |
| --- | --- | --- |
| 入门与架构 | 学习路线、开发环境、CLI 启动、Studio 数据流 | `00` - `03` |
| 核心骨架 | State、Node、Edge、Graph、类型提示、条件边 | `04` - `07` |
| 工具与状态 | ToolNode、Runnable、Reducer、Graphviz 可视化 | `08` - `10` |
| 持久化与恢复 | Checkpoint、多轮对话、状态回退、Postgres、Durable Execution | `11` - `16` |
| 人机协作与记忆 | Human-in-the-loop、跨会话记忆、个人助理 | `15` - `17` |

## 重点主题

- LangGraph 的核心价值不是“画图”，而是把 AI 流程变成可控制的状态转移。
- Checkpoint 让工作流可以暂停、恢复、回看和修正。
- Human-in-the-loop 适合高风险工具调用、审批流和半自动 Agent。
- Durable Execution 让节点失败后可以从断点继续，而不是从头重跑。

## 适合读者

- 已经理解 LangChain 基础接口，想进一步做复杂流程编排的人。
- 希望 Agent 具备可恢复、可审计、可人工介入能力的人。
- 想构建生产级 AI Workflow 的开发者。

## 下一步

读完 LangGraph 后，可以继续进入：

- [MCP 实战](../../mcp/foundations)：理解外部工具和上下文能力如何被协议化。
- [LangChain Middleware](../../langchain/foundations)：理解 Agent 调用过程中的工程拦截层。
