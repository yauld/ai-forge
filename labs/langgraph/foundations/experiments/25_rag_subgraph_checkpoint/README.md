# 25_rag_subgraph_checkpoint

这个实验演示如何把第 24 个最小 RAG 图改造成一个可复用的 RAG 子图，并观察子图在 stream 输出和 checkpoint namespace 里的运行边界。

实验重点不是提升 RAG 效果，而是看清三个问题：

- 子图如何把一段稳定流程封装成父图里的一个节点。
- 父图和子图如何通过共享 State 字段传递数据。
- 启用 checkpointer 后，父图和子图的 checkpoint namespace 有什么区别。

## 图结构

父图负责业务编排：

```text
START
 -> normalize_question
 -> rag_subgraph
 -> format_response
 -> END
```

RAG 子图负责问答细节：

```text
START
 -> retrieve_docs
 -> 有资料：build_context
 -> answer
 -> END

retrieve_docs
 -> 无资料：fallback
 -> END
```

## State 交接

父图和子图共用一份 State。这个实验故意把交接字段设计得很直观：

```text
父图写入 normalized_question
子图读取 normalized_question

子图写入 retrieved_docs / context / route / answer
父图读取 route / answer / retrieved_docs

父图写入 final_response
```

这说明子图不是普通函数调用。它内部仍然是一张图，只是在父图里被当成一个节点使用。

## Checkpoint 观察

实验会使用 `InMemorySaver` 编译父图，并在运行时传入 `thread_id`。运行后会打印 checkpoint namespace。

你应该能看到两类 namespace：

```text
<parent>
rag_subgraph:...
```

`<parent>` 表示父图自己的 checkpoint；`rag_subgraph:...` 表示 RAG 子图内部节点产生的 checkpoint。这个输出是第 25 个主题的关键证据：子图有清晰的运行时边界，checkpoint 也会保留这个边界。

## 运行

运行前需要本地 Ollama 已启动，并且已经拉取模型：

```bash
ollama pull qwen3-embedding:latest
ollama pull qwen3-coder:30b
```

运行实验：

```bash
uv run labs/langgraph/foundations/experiments/25_rag_subgraph_checkpoint/main.py
```

导出实际 LangGraph 图结构图片，不调用 Ollama：

```bash
uv run labs/langgraph/foundations/experiments/25_rag_subgraph_checkpoint/render_graphviz.py
```

这个脚本会生成两张图：

```text
labs/langgraph/foundations/experiments/25_rag_subgraph_checkpoint/rag_subgraph_parent_graph.png
labs/langgraph/foundations/experiments/25_rag_subgraph_checkpoint/rag_subgraph_xray_graph.png
```

`rag_subgraph_parent_graph.png` 是父图普通视图，能看到：

- 父图入口：`START -> normalize_question`。
- RAG 子图作为一个模块节点：`normalize_question -> rag_subgraph`。
- 子图结束后回到父图：`rag_subgraph -> format_response -> END`。

`rag_subgraph_xray_graph.png` 是展开视图，能看到：

- `rag_subgraph` 内部的 `retrieve_docs`、`build_context`、`answer` 和 `fallback`。
- 子图内部两条路径：有足够相关资料时回答，无足够相关资料时兜底。
- 子图结束后回到父图的 `format_response`。

实验会依次运行两个问题：

- `你好，我想问一下，未发货订单能退款吗？？？`
- `积分可以提现吗？`

第一个问题用于观察命中知识库后的子图路径；第二个问题用于观察 fallback 路径。
