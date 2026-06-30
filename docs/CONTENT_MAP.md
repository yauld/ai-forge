# AI Forge 内容地图

这份地图用于帮助读者快速找到 AI Forge 中的学习主题。

AI Forge 的长期公开结构是 `labs/`、`examples/`、`assets/`、`drafts/` 和 `docs/`。旧 `notebooks/` 内容已经迁移到新结构中，迁移过程中没有改写已完成文章正文和 Notebook 内容。

## 主要入口

| 入口 | 说明 |
| --- | --- |
| [labs](../labs) | 可复现实验和 Notebook |
| [examples](../examples) | 独立示例服务、脚本和最小项目 |
| [docs/MIGRATION_PLAN.md](MIGRATION_PLAN.md) | 旧内容迁移记录 |

## LangChain

实验入口：[labs/langchain](../labs/langchain)

适合目标：建立 LLM 应用开发的基础接口直觉，理解模型、消息、提示词、工具、记忆和 Agent 的组合方式。

主要主题：

- 开发环境与模型接入
- OpenAI Python SDK 与 LangChain 模型封装
- Messages 与 Prompt
- Tools 与工具调用
- 短期记忆与长期记忆
- Agent ReAct 流程
- Middleware：限流、失败兜底、人工审批、敏感信息脱敏、上下文整理、自定义拦截逻辑
- LCEL、Embeddings 与语义检索

已迁移实验：

- [labs/langchain/foundations](../labs/langchain/foundations)

建议路线：

1. `foundations` 中的 `01` 到 `08`：先理解 LangChain 的基础对象和工具调用。
2. `foundations` 中的 `09` 到 `15`：进入记忆与对话状态管理。
3. `foundations` 中的 `16` 到 `27`：进入 Agent 与 Middleware 的工程化控制。

## LangGraph

实验入口：[labs/langgraph](../labs/langgraph)

适合目标：理解如何把 AI 应用组织成可控、可恢复、可检查的状态图。

主要主题：

- State、Node、Edge、Graph
- 条件边与流程分支
- ToolNode 与 Runnable
- Reducer 与状态更新
- Graphviz 可视化
- Checkpoint、thread_id 与多轮对话
- 状态查看、回退和修正
- Postgres 持久化
- Human-in-the-loop
- Durable Execution
- 跨会话记忆

已迁移实验：

- [labs/langgraph/foundations](../labs/langgraph/foundations)

建议路线：

1. `foundations` 中的 `00` 到 `06`：理解 LangGraph 的核心骨架。
2. `foundations` 中的 `07` 到 `10`：学习条件流程、工具节点和图可视化。
3. `foundations` 中的 `11` 到 `16`：进入 checkpoint、人工审批和失败恢复。
4. `foundations` 中的 `17`：理解记忆系统如何支撑长期助手。

## RAG

实验入口：[labs/rag](../labs/rag)

适合目标：从文档处理到向量检索，再到最小问答链路，建立 RAG 的完整工程路径。

主要主题：

- RAG 基础通识
- 向量与余弦相似度
- CSV、JSON、PDF、Text、Markdown、目录加载
- Text Splitter
- 向量库增删查与持久化
- Retriever
- Prompt 组装与 LLM 调用

已迁移实验：

- [labs/rag/foundations](../labs/rag/foundations)

建议路线：

1. `foundations` 中的 `01` 到 `03`：先理解 RAG 与向量相似度。
2. `foundations` 中的 `04` 到 `07`：学习文档加载和切分。
3. `foundations` 中的 `08` 到 `10`：完成向量库、Retriever 和最小问答链路。

## MCP

实验入口：[labs/mcp](../labs/mcp)

示例入口：[examples/mcp-servers](../examples/mcp-servers)

适合目标：理解 MCP 在 AI 应用架构中的位置，以及 Tool、Resource、Prompt 如何被设计和调用。

主要主题：

- MCP 是什么，以及它为什么出现在 AI 应用架构里
- Host、Client、Server 的协作关系
- Tool、Resource、Prompt 的边界和设计方式
- 从 `initialize` 到 `tools/call` 的通信过程
- 订单分析 MCP Server 示例

已迁移实验：

- [labs/mcp/foundations](../labs/mcp/foundations)

## Skills

入口：[labs/skills](../labs/skills)

适合目标：理解如何把重复的写作、检查、工程流程固化成 Codex Skill，并逐步沉淀为可复用工作流。

当前内容：

- 为 Codex 写一个写作 Skill，把反复改稿变成固定工作流

## Coding

入口：[labs/coding](../labs/coding)

适合目标：补齐 AI 工程实验中常用的 Python、FastAPI、服务化和工程基础能力。

当前内容：

- [labs/coding/python-fastapi](../labs/coding/python-fastapi)

## 待整理主题

入口：[drafts/backlog](../drafts/backlog)

这里保存仍在跟踪或构思中的选题，包括 MCP 安全、Skill 供应链安全、提示词安全、模型安全护栏、多智能体系统等。后续成熟后再迁移到正式主题目录。
