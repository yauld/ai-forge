# AI Forge 内容地图

这份地图用于帮助读者快速找到 AI Forge 中的学习主题。当前仓库保留了早期实验和文章的原始组织方式，后续会逐步整理成更稳定的学习单元。

## LangChain

入口：[notebooks/langchain](../notebooks/langchain)

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

建议路线：

1. `01` 到 `08`：先理解 LangChain 的基础对象和工具调用。
2. `09` 到 `15`：进入记忆与对话状态管理。
3. `16` 到 `27`：进入 Agent 与 Middleware 的工程化控制。

## LangGraph

入口：[notebooks/langgraph](../notebooks/langgraph)

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

建议路线：

1. `00` 到 `06`：理解 LangGraph 的核心骨架。
2. `07` 到 `10`：学习条件流程、工具节点和图可视化。
3. `11` 到 `16`：进入 checkpoint、人工审批和失败恢复。
4. `17`：理解记忆系统如何支撑长期助手。

## RAG

入口：[notebooks/rag](../notebooks/rag)

适合目标：从文档处理到向量检索，再到最小问答链路，建立 RAG 的完整工程路径。

主要主题：

- RAG 基础通识
- 向量与余弦相似度
- CSV、JSON、PDF、Text、Markdown、目录加载
- Text Splitter
- 向量库增删查与持久化
- Retriever
- Prompt 组装与 LLM 调用

建议路线：

1. `01` 到 `03`：先理解 RAG 与向量相似度。
2. `04` 到 `07`：学习文档加载和切分。
3. `08` 到 `10`：完成向量库、Retriever 和最小问答链路。

## MCP

入口：[notebooks/mcp](../notebooks/mcp)

适合目标：理解 MCP 在 AI 应用架构中的位置，以及 Tool、Resource、Prompt 如何被设计和调用。

主要主题：

- MCP 是什么，以及它为什么出现在 AI 应用架构里
- Host、Client、Server 的协作关系
- Tool、Resource、Prompt 的边界和设计方式
- 从 `initialize` 到 `tools/call` 的通信过程
- 订单分析 MCP Server 示例

相关示例：

- [notebooks/mcp/examples/shop_order_analysis_server.py](../notebooks/mcp/examples/shop_order_analysis_server.py)
- [notebooks/mcp/examples/shop_order_primitives_server.py](../notebooks/mcp/examples/shop_order_primitives_server.py)
- [notebooks/mcp/examples/data/shop_orders.sqlite](../notebooks/mcp/examples/data/shop_orders.sqlite)

## Python / FastAPI

入口：[notebooks/python](../notebooks/python)

适合目标：补齐 AI 工程实验中常用的 Python 服务化基础。

当前主题：

- FastAPI Depends 与依赖注入

## Codex Skills

入口：[notebooks/skills](../notebooks/skills)

适合目标：理解如何把重复的写作、检查、工程流程固化成 Codex Skill。

当前主题：

- 为 Codex 写一个写作 Skill，把反复改稿变成固定工作流

## 待整理主题

入口：[notebooks/待跟踪](../notebooks/待跟踪)

这里保存仍在跟踪或构思中的选题，包括 MCP 安全、Skill 供应链安全、提示词安全、模型安全护栏、多智能体系统等。后续成熟后会迁移到正式主题目录。
