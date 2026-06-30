# AI Forge

AI Engineering 实战锻造场。

这个仓库通过文章、Notebook 和可运行示例，持续研究 LangChain、LangGraph、RAG、MCP、Agent 工程化、记忆、工具调用与安全控制。每个专题的 README 同时记录已经完成的内容和接下来准备研究的问题。

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/package%20manager-uv-261230)](https://docs.astral.sh/uv/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1C3C3C)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-practice-5B5BD6)](https://modelcontextprotocol.io/)

## 专题入口

| 专题 | 研究范围 | 文章与后续计划 |
| --- | --- | --- |
| LangChain | 模型、Messages、Prompt、Tools、Memory、Agent、Middleware、LCEL、Embeddings | [查看专题](labs/langchain/foundations) |
| LangGraph | State、Node、Edge、Checkpoint、Human-in-the-loop、Durable Execution、Memory | [查看专题](labs/langgraph/foundations) |
| RAG | 文档加载、文本切分、向量库、Retriever、Prompt 与问答链路 | [查看专题](labs/rag/foundations) |
| MCP | Host、Client、Server、Tool、Resource、Prompt、JSON-RPC 与 Transport | [查看专题](labs/mcp/foundations) |
| Skills | Codex Skills、工作流固化与工程自动化 | [查看内容](labs/skills) |
| Coding | Python、FastAPI 与 AI 工程所需的服务化基础 | [查看内容](labs/coding) |

尚未进入正式研究计划的选题保存在 [drafts/backlog](drafts/backlog)。每个正式专题只在自己的 README 中维护一次研究状态，根 README 不重复展开文章清单。

## 如何运行

本仓库要求 Python 3.13 或更高版本，并使用 uv 管理环境：

```bash
uv sync
```

启动 Notebook：

```bash
uv run jupyter notebook
```

运行 Python 示例：

```bash
uv run python path/to/example.py
```

在 Codex 沙箱或不希望使用用户级 uv 缓存时：

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync python path/to/example.py
```

各实验的特殊启动参数放在对应文章、Notebook 或示例目录中。例如 MCP Server 的运行方式见 [MCP 示例代码](labs/mcp/foundations/examples)。

检查公共入口、相对链接和目录约定：

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync python scripts/check_repo.py
```

## 内容组织

```text
.
├── labs/            # 已形成文章、Notebook 或可运行示例的专题
├── drafts/          # 尚未成熟的草稿和候选选题
├── assets/          # 根 README 使用的资源
├── scripts/         # 仓库检查脚本
├── pyproject.toml
└── uv.lock
```

示例代码、数据和图片跟随所属专题，分别放在就近的 `examples/`、`data/` 和 `assets/` 中；只有根 README 使用的资源放在根目录 `assets/`。

## 研究与写作约定

### 研究状态

专题 README 使用统一表格：

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 专题内顺序 | 已有成果链接或计划文件名 | 这项研究要回答的核心问题 | 已完成 / 进行中 / 待研究 |

新增研究内容时直接更新对应专题表格：

- 已完成：已经形成文章、Notebook 或稳定实验。
- 进行中：当前正在研究并准备形成成果。
- 待研究：已经明确问题，但尚未开始。
- 尚未归入专题的想法先放入 `drafts/backlog/`。

### 文章与 GitHub 的分工

- 每篇文章只回答一个清晰问题。
- 公众号文章讲背景、核心直觉、工程判断和实验结论。
- GitHub 保存完整代码、Notebook、截图、示例数据和运行说明。
- 新文章先确定所属专题和成果文件，再开始写作；发布后在专题 README 更新状态与入口。
- 已发布正文尽量保持稳定，确需大幅重写时单独规划新版内容。

推荐文章骨架：

```text
标题：用具体问题命名

1. 为什么这个问题值得讲
2. 用最小例子建立直觉
3. 工程实现中真正需要注意什么
4. 实验验证了什么，还有什么没有验证
5. 完整代码、Notebook 和运行入口
```

文章专属素材放在对应专题的 `assets/`，独立脚本或服务放在 `examples/`。文章结尾优先链接到具体专题或成果文件，而不是只链接仓库首页。

### 发布前检查

- 标题是否只回答一个问题。
- 是否使用真实项目代码和配置，而不是另造平行示例。
- 是否删除重复背景、大段无关代码、长截图和排障过程。
- 文章中的代码、Notebook 或示例是否能够复现。
- 是否清理个人路径、无关输出和敏感信息。
- 相对链接、示例数据和专题 README 状态是否已经更新。

## 公众号

公众号用于发布更短、更聚焦的文章版本；仓库保留完整实验和持续更新的研究记录。

<p align="center">
  <img src="assets/wechat-qr.jpg" width="220" alt="公众号二维码">
</p>
