# 10 | LangGraph接入RAG：别把检索问答全塞进一条链

最小RAG的链式写法大致这样：

```text
用户问题 -> 检索资料 -> 拼Prompt -> 调模型回答
```

用LangGraph把最小RAG拆成一张小图：

```text
START
  ↓
retrieve_docs
  ├─ 有足够相关资料 -> build_context -> answer -> END
  └─ 无足够相关资料 -> fallback -> END
```

图结构：

![最小RAG图](../../labs/langgraph/foundations/experiments/24_minimal_rag_graph/minimal_rag_graph.png)

这里主要是看下graph里一般怎么接入rag，实现不复杂。

## 1. 准备知识库和测试问题

先准备一份很小的客服知识库，包含退款、发票、会员续费、商品质量问题等内容

然后测试三个问题

```text
1、未发货订单能退款吗？
2、电子发票在哪里下载？
3、积分可以提现吗？
```

预期效果应该是，前两个问题应该能检索到资料并回答，第三个问题不在知识库范围内，应该走fallback。

## 2. 定义State和Runtime Context

State保存这次问答过程中产生的数据

```python
class RagDocument(TypedDict):
    source: str
    chunk_index: int
    start_index: int
    content: str
    similarity: float


class RagState(TypedDict, total=False):
    question: str
    retrieved_docs: list[RagDocument]
    context: str
    route: Literal["answer", "fallback"]
    answer: str
```
稍微解释下

- question是用户问题
- retrieved_docs是结构化检索结果，
- context是给模型看的上下文，这里后续会包含从向量哭里检索出来的文档片段
- route记录走了正常回答还是fallback
- answer保存最终回答。

Runtime Context保存运行配置和外部依赖，内容包括

```python
class RagContext(TypedDict):
    knowledge_base_path: str
    top_k: int
    min_similarity: float
    embedding_model: str
    answer_model: str
    ollama_base_url: str
    vectorstore: InMemoryVectorStore
```

- top_k是每次检索最多返回几个相关片段
- min_similarity是最低相似度阈值，低于这个分数的资料不进入回答流程
- embedding_model：使用的Embedding模型
- vectorstore：已经构建好的向量库对象，用它根据用户问题检索相关资料

两份存储的区别：

1、问答过程中产生的东西放State

2、运行时需要的配置和依赖放Runtime Context

## 3. 启动时先建向量库

启动时建一次向量库，后面多个问题都可以复用（写入到内存，暂时不用本地存储）

```python
def build_vectorstore(
    knowledge_base_path: str,
    embedding_model: str,
    ollama_base_url: str,
) -> InMemoryVectorStore:
    docs = load_support_docs(knowledge_base_path)
    embeddings = OllamaEmbeddings(
        model=embedding_model,
        base_url=ollama_base_url,
    )
    return InMemoryVectorStore.from_documents(docs, embeddings)
```

文本切分用RecursiveCharacterTextSplitter

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=160,
    chunk_overlap=30,
    separators=["\n\n", "\n", "。", "，", " ", ""],
    add_start_index=True,
)
docs = splitter.split_documents(raw_docs)
```

add_start_index=True能保留chunk在原文里的起始位置，后面展示参考资料时有用。

## 4. 写检索节点retrieve_docs

检索节点做的四件事：读取问题、查询向量库、过滤低相关资料、写回State。

```python
def retrieve_docs(state: RagState, runtime: Runtime[RagContext]) -> RagState:
    context = runtime.context
    question = get_question(state)

    results = context["vectorstore"].similarity_search_with_score(
        question,
        k=context["top_k"],
    )

    retrieved_docs: list[RagDocument] = []
    for doc, similarity in results:
        if similarity < context["min_similarity"]:
            continue

        retrieved_docs.append(
            {
                "source": Path(str(doc.metadata.get("source", "unknown"))).name,
                "chunk_index": int(doc.metadata.get("chunk_index", -1)),
                "start_index": int(doc.metadata.get("start_index", -1)),
                "content": doc.page_content,
                "similarity": similarity,
            }
        )

    return {"retrieved_docs": retrieved_docs}
```

这里的min_similarity=0.60只是当前知识库和embedding模型下的实验阈值，不是通用标准。（换知识库或模型后要重新观察和选择你要使用啥分数）

## 5. 写条件边：有资料才回答

检索后不要直接回答，先判断有没有足够相关资料

```python
def route_after_retrieve(state):
    if state.get("retrieved_docs"):
        return "build_context"

    return "fallback"
```

这个分支决定了图的基本边界，即有资料才回答，没资料就fallback，也体现了langchain与langgraph环境下使用rag的实现区别。

## 6. 写build_context、answer和fallback

build_context把结构化检索结果整理成模型可读的上下文

```python
def build_context(state: RagState) -> RagState:
    context_parts = []
    for index, doc in enumerate(state.get("retrieved_docs", []), start=1):
        context_parts.append(
            f"资料 {index}：{doc['source']}#chunk-{doc['chunk_index']}\n"
            f"相似度：{doc['similarity']:.3f}\n"
            f"起始位置：{doc['start_index']}\n"
            f"正文：{doc['content']}"
        )

    return {"context": "\n\n".join(context_parts), "route": "answer"}
```

answer只根据用户问题和检索上下文回答

```python
model = ChatOllama(
    model=context["answer_model"],
    base_url=context["ollama_base_url"],
    temperature=0,
)
```

但是Prompt里要写清楚，只根据给定资料回答，不要编造资料中没有的信息，这个约束还是挺重要的，不然模型会放飞自己。

fallback不调用模型，直接兜底就行。

```python
def fallback(state: RagState) -> RagState:
    return {
        "route": "fallback",
        "context": "",
        "answer": "当前知识库里没有找到足够相关的资料，建议转人工客服或补充更多问题信息。",
    }
```

RAG的底线：没有依据时，不要不懂装懂。

## 7. 把节点连成图

图本身不大

```python
graph_builder = StateGraph(RagState, context_schema=RagContext)

graph_builder.add_node("retrieve_docs", retrieve_docs)
graph_builder.add_node("build_context", build_context)
graph_builder.add_node("answer", answer)
graph_builder.add_node("fallback", fallback)

graph_builder.add_edge(START, "retrieve_docs")
graph_builder.add_conditional_edges(
    "retrieve_docs",
    route_after_retrieve,
    {
        "build_context": "build_context",
        "fallback": "fallback",
    },
)
graph_builder.add_edge("build_context", "answer")
graph_builder.add_edge("answer", END)
graph_builder.add_edge("fallback", END)

graph = graph_builder.compile()
```

到这里，一个最小LangGraph RAG就搭好了。

## 8. 运行并观察三条路径

启动时配置知识库、模型和向量库：

```python
knowledge_base_path = "support_policy_retriever.txt"
embedding_model = "qwen3-embedding:latest"
answer_model = "qwen3-coder:30b"
ollama_base_url = "http://localhost:11434"

vectorstore = build_vectorstore(
    knowledge_base_path=knowledge_base_path,
    embedding_model=embedding_model,
    ollama_base_url=ollama_base_url,
)

runtime_context = {
    "knowledge_base_path": knowledge_base_path,
    "top_k": 2,
    "min_similarity": 0.60,
    "embedding_model": embedding_model,
    "answer_model": answer_model,
    "ollama_base_url": ollama_base_url,
    "vectorstore": vectorstore,
}
```

每次调用时，初始State只放问题：

```python
initial_state = {"question": question}
final_state = graph.invoke(initial_state, context=runtime_context)
```

看下关键输出的效果

```text
问题 1：未发货订单能退款吗？
路径：answer
最终回答：未发货订单可以申请退款，系统会自动拦截发货流程，退款通常在1-3个工作日内原路退回。
参考资料：[1] support_policy_retriever.txt#chunk-1@0(0.730); [2] support_policy_retriever.txt#chunk-2@109(0.626)

问题 2：电子发票在哪里下载？
路径：answer
最终回答：电子发票可在订单详情页下载。进入"我的订单 -> 订单详情 -> 发票信息"查找发票入口。
参考资料：[1] support_policy_retriever.txt#chunk-3@208(0.732)

问题 3：积分可以提现吗？
路径：fallback
最终回答：当前知识库里没有找到足够相关的资料，建议转人工客服或补充更多问题信息。
参考资料：无
```

## 9. 五条核心边界

1、State保存用户问题、检索结果、上下文和最终回答。

2、Runtime Context保存知识库、模型、检索参数和向量库。

3、向量库启动时构建一次，不要每个问题重复建索引。

4、检索节点只负责找资料。

5、没有足够相关资料就fallback，不让模型硬答。

---

实验细节

```text
GitHub 仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/langgraph/foundations/24 | LangGraph + RAG：把最小问答链路接入图.md

实验代码：
labs/langgraph/foundations/experiments/24_minimal_rag_graph/
```
