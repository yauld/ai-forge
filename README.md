# AI Forge

AI Engineering 实战锻造场。

这个仓库用真实代码、Notebook、示例服务和文章草稿，系统记录 AI 应用工程中的关键实践：LangChain、LangGraph、RAG、MCP、Agent 工程化、记忆、工具调用、可观测流程和安全控制。

它不是资料搬运，也不是 API 速查。AI Forge 更像一个长期更新的工程工作台：公众号文章负责讲清楚问题和判断，GitHub 仓库负责沉淀完整实验、运行代码、截图素材和可复现路径。

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/package%20manager-uv-261230)](https://docs.astral.sh/uv/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1C3C3C)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-practice-5B5BD6)](https://modelcontextprotocol.io/)

## 适合谁

- 想从“会调大模型 API”走向“能设计 AI 应用”的开发者。
- 正在学习 LangChain、LangGraph、RAG、MCP、Agent 的工程实践者。
- 希望把公众号文章、Notebook、示例代码结合起来系统学习的读者。
- 想观察一个 AI Engineering 知识库如何从实验记录逐步整理成公开项目的人。

## 内容地图

| 方向 | 主要内容 | 入口 |
| --- | --- | --- |
| LangChain | 模型调用、Messages、Prompt、Tools、Memory、Agent、Middleware、LCEL、Embeddings | [notebooks/langchain](notebooks/langchain) |
| LangGraph | State、Node、Edge、条件边、Reducer、Checkpoint、Human-in-the-loop、Durable Execution、Memory | [notebooks/langgraph](notebooks/langgraph) |
| RAG | 文档加载、文本切分、向量库、Retriever、Prompt 组装、最小问答链路 | [notebooks/rag](notebooks/rag) |
| MCP | Host、Client、Server、Tool、Resource、Prompt、JSON-RPC 通信流程、订单分析示例 | [notebooks/mcp](notebooks/mcp) |
| Python / FastAPI | 工程基础、依赖注入、服务化实验 | [notebooks/python](notebooks/python) |
| Codex Skills | 用 Skill 固化写作和工程工作流 | [notebooks/skills](notebooks/skills) |

更细的主题索引见 [docs/CONTENT_MAP.md](docs/CONTENT_MAP.md)。

## 推荐学习路线

### 1. 从 LangChain 进入 AI 应用开发

先理解模型、消息、提示词和工具，再进入记忆、Agent 和 Middleware。适合希望掌握 LLM 应用基本工程接口的读者。

起点：[notebooks/langchain](notebooks/langchain)

### 2. 用 LangGraph 理解可控 Agent 流程

从 State、Node、Edge 开始，逐步进入 checkpoint、人工审批、失败恢复和跨会话记忆。适合希望构建可控、多步骤、可恢复 AI 工作流的读者。

起点：[notebooks/langgraph](notebooks/langgraph)

### 3. 用 RAG 打通知识问答链路

从文档加载、切分、向量化、检索器到最小问答链路，建立 RAG 的工程直觉。

起点：[notebooks/rag](notebooks/rag)

### 4. 用 MCP 理解工具生态和上下文协议

从架构角色出发，理解 Host、Client、Server 如何协作，再落到 Tool、Resource、Prompt 和通信过程。

起点：[notebooks/mcp](notebooks/mcp)

## 如何运行

本仓库使用 uv 管理 Python 环境，Python 版本要求为 3.13 或更高。

```bash
uv sync
```

启动 Notebook：

```bash
uv run jupyter notebook
```

运行某个示例时，优先使用：

```bash
uv run python path/to/example.py
```

在 Codex 沙箱或不希望修改全局缓存时，可使用：

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync python path/to/example.py
```

## 公众号与 GitHub 如何配合

AI Forge 的内容会采用“双层发布”方式：

- 公众号文章：讲问题背景、核心概念、工程判断和关键结论。
- GitHub 仓库：保存完整 Notebook、示例代码、截图、实验数据和运行说明。

这样公众号文章可以更短、更清晰，读者如果想深入复现，就可以回到仓库继续看完整实验。

每篇文章建议在结尾放一个固定入口：

```text
完整代码、Notebook、截图和运行说明：
https://github.com/yauld/ai-forge
```

具体发布规范见 [docs/PUBLISHING.md](docs/PUBLISHING.md)。

## 仓库结构

```text
.
├── notebooks/
│   ├── langchain/   # LangChain 实战文章与 Notebook
│   ├── langgraph/   # LangGraph 实战文章与 Notebook
│   ├── rag/         # RAG 基础与工程实验
│   ├── mcp/         # MCP 架构、协议与示例服务
│   ├── python/      # Python / FastAPI 工程基础
│   └── skills/      # Codex Skill 实践
├── docs/
│   ├── CONTENT_MAP.md
│   └── PUBLISHING.md
├── pyproject.toml
└── uv.lock
```

## 项目原则

- 用真实项目代码解释概念，不另造一套脱离上下文的演示。
- 每个主题尽量回答一个清晰问题，而不是堆砌材料。
- 公众号负责传播，GitHub 负责复现和长期沉淀。
- 优先保留可运行代码、Notebook、截图和实验数据。
- 内容会持续整理，旧实验会逐步升级为更稳定的学习单元。

## Roadmap

- 整理每个主题目录的 README 和学习顺序。
- 将长文章拆成“公众号短文 + GitHub 深入实验”。
- 为核心实验补充稳定运行说明和最小复现命令。
- 将重点主题逐步整理为 `topic/lesson` 风格的学习单元。
- 在 `yauld` 账号下建立更统一的 AI Engineering 品牌入口。
