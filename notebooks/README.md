# Notebooks

这里保存 AI Forge 的主要实战材料：Notebook、文章草稿、示例代码、截图资源和实验数据。

## 主题入口

| 主题 | 说明 | 入口 |
| --- | --- | --- |
| LangChain | 模型调用、Prompt、Tools、Memory、Agent、Middleware | [langchain](langchain) |
| LangGraph | StateGraph、Checkpoint、Human-in-the-loop、Durable Execution、Memory | [langgraph](langgraph) |
| RAG | 文档加载、切分、向量库、Retriever、最小问答链路 | [rag](rag) |
| MCP | Host、Client、Server、Tool、Resource、Prompt、通信过程 | [mcp](mcp) |
| Python | FastAPI 与 Python 工程基础 | [python](python) |
| Skills | Codex Skill 与工作流固化 | [skills](skills) |

## 阅读建议

- 如果你刚开始学习 AI Engineering，先读 LangChain，再读 LangGraph 和 RAG。
- 如果你已经在做 Agent 工程化，优先读 LangGraph、MCP 和 LangChain Middleware。
- 如果你来自公众号文章，优先进入文章底部给出的具体目录，再回到这里浏览完整路线。

## 运行建议

在仓库根目录安装依赖：

```bash
uv sync
```

启动 Notebook：

```bash
uv run jupyter notebook
```

运行示例脚本：

```bash
uv run python path/to/example.py
```
