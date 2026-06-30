# Notebooks Migration Record

`notebooks/` 曾经是 AI Forge 的旧内容来源，不是最终公开结构。当前 Git 跟踪内容已经迁移到新的公开结构中。

迁移目标是把已有文章、Notebook、示例代码和素材整理到 `labs/`、`examples/`、`assets/` 和 `drafts/` 中。迁移过程中不改写任何已完成文章正文，也不修改任何已有 Notebook 内容。

## 硬约束

- 不修改已有 `.md` 文章正文。
- 不修改已有 `.ipynb` Notebook 内容。
- 不给旧文章追加新段落、新链接或新结尾。
- 不改旧文章标题、代码块、图片引用和参考资料。
- 迁移时只做文件级移动、复制、归类和索引。
- `notebooks/` 不再作为公开目录存在。

## 目标结构

```text
ai-forge/
├── labs/        # 可复现实验和 Notebook
├── examples/    # 独立示例服务、脚本和最小项目
├── assets/      # 跨主题复用资源
├── drafts/      # 新文章草稿和选题
└── docs/        # 仓库规范、内容地图和迁移说明
```

## 迁移映射

| 旧位置 | 新位置 | 处理方式 |
| --- | --- | --- |
| `notebooks/langchain/*` | `labs/langchain/foundations/` | 已迁移 Git 跟踪文件，内容不改 |
| `notebooks/langgraph/*` | `labs/langgraph/foundations/` | 已整体迁移，内容不改 |
| `notebooks/rag/*` | `labs/rag/foundations/` | 已整体迁移，内容不改 |
| `notebooks/mcp/*` | `labs/mcp/foundations/` | 已整体迁移，内容不改 |
| `notebooks/python/*` | `labs/coding/python-fastapi/` | 已迁移，内容不改 |
| `notebooks/skills/*` | `labs/skills/` | 已迁移，内容不改 |
| `notebooks/builds/*` | `drafts/builds/` | 已迁移，内容不改 |
| `notebooks/待跟踪/*` | `drafts/backlog/` | 已迁移，内容不改 |

## 迁移结果

已完成的迁移结果：

- `labs/langchain/foundations/`：LangChain 基础与 Middleware 系列。
- `labs/langgraph/foundations/`：LangGraph 基础、checkpoint、Human-in-the-loop 和持久化系列。
- `labs/rag/foundations/`：RAG 基础、文档加载、切分、向量库和 Retriever 系列。
- `labs/mcp/foundations/`：MCP 架构、协议、Tool、Resource、Prompt 和示例服务。
- `labs/coding/python-fastapi/`：Python / FastAPI 工程基础。
- `labs/skills/`：Codex Skills 实践。
- `drafts/builds/`：构建稿和阶段性草稿。
- `drafts/backlog/`：待跟踪选题。

## 迁移前规模

| 主题 | 文章 Markdown | Notebook | 其他顶层文件 | 迁移优先级 |
| --- | ---: | ---: | ---: | --- |
| MCP | 6 | 1 | 0 | P0 |
| RAG | 4 | 7 | 0 | P1 |
| LangGraph | 7 | 14 | 1 | P2 |
| LangChain | 2 | 26 | 0 | P3 |

这张表只统计迁移前的顶层文章和 Notebook，不包含图片、数据集和示例目录。

## 每个实验单元的目标形态

```text
labs/<topic>/<lesson>/
├── README.md        # 新写的实验说明，可以链接原文，但不改原文
├── article.md       # 从旧文章移动或复制，内容不改
├── notebook.ipynb   # 从旧 Notebook 移动或复制，内容不改
├── assets/
└── data/
```

后续新文章和新实验可以继续按这个形态沉淀；已经迁移的旧文章和 Notebook 内容保持不变。
