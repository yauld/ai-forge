# 24_minimal_rag_graph

这个实验演示如何把一个最小客服 RAG 问答链路接入 LangGraph。

实验重点不是检索算法本身，而是看清两个边界：

- State 保存本次任务的中间结果：`question`、`retrieved_docs`、`context`、`route`、`answer`。
- Runtime Context 保存本次运行的外部配置和依赖：知识库路径、`top_k`、最低相似度、Embedding 模型、回答模型、Ollama 地址和向量库。
- `min_similarity=0.60` 是当前示例知识库和 `qwen3-embedding:latest` 下的实验阈值，不是通用标准。

图结构：

```text
question
 -> retrieve_docs
 -> 有足够相关资料：build_context
 -> answer
 -> END

retrieve_docs
 -> 无足够相关资料：fallback
 -> END
```

运行：

```bash
uv run labs/langgraph/foundations/experiments/24_minimal_rag_graph/main.py
```

运行前需要本地 Ollama 已启动，并且已经拉取模型：

```bash
ollama pull qwen3-embedding:latest
ollama pull qwen3-coder:30b
```

实验会依次运行三个问题：

- `未发货订单能退款吗？`
- `电子发票在哪里下载？`
- `积分可以提现吗？`

在当前配置下，前两个问题会命中客服知识库并进入 `answer` 节点，第三个问题会进入 `fallback` 节点。
