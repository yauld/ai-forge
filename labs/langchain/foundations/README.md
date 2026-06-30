# LangChain 实战

这个目录记录 LangChain 在 AI 应用开发中的核心用法：模型接入、消息、提示词、工具、记忆、Agent 和 Middleware。

## 推荐路线

| 阶段 | 内容 | 文件范围 |
| --- | --- | --- |
| 基础接入 | 环境搭建、模型创建、调用方式、Messages、Prompt | `01` - `07` |
| 工具与记忆 | Tools、短期记忆、长期记忆、Embeddings、LCEL | `08` - `15` |
| Agent 流程 | ReAct 过程、Agent 为什么需要工程约束 | `16` - `17` |
| Middleware | 限制循环、失败兜底、人工审批、脱敏、上下文整理、自定义拦截 | `18` - `27` |

## 重点主题

- 模型调用不只是 API 封装，还包括消息结构、Prompt 组织和输出处理。
- Tools 是 Agent 连接外部系统的入口，也是风险控制的关键边界。
- Memory 需要区分短期对话状态和跨会话长期记忆。
- Middleware 是把 Agent 从“能跑”推向“可控、可审计、可运营”的工程层。

## 适合读者

- 想系统理解 LangChain 基础接口的开发者。
- 正在把 LLM 接入业务系统的人。
- 想学习 Agent 工程化控制方式的人。

## 下一步

读完 LangChain 后，可以继续进入：

- [LangGraph 实战](../../langgraph/foundations)：把流程组织成可控状态图。
- [RAG 实战](../../rag/foundations)：补齐知识检索链路。
- [MCP 实战](../../mcp/foundations)：理解工具生态与上下文协议。
