from pathlib import Path
from typing import Any, Literal, Mapping, TypedDict

from langchain_core.documents import Document
from langchain_core.runnables import RunnableConfig
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


ROOT_DIR = Path(__file__).resolve().parents[5]


class RagDocument(TypedDict):
    # 检索结果进入 State 前先整理成稳定字段，避免后续节点直接依赖
    # LangChain Document 的 metadata 结构。
    source: str
    chunk_index: int
    start_index: int
    content: str
    similarity: float


class RagState(TypedDict, total=False):
    # 父图和子图共用同一份 State。
    # 这个实验故意把字段拆开，方便观察数据在父图和子图之间如何交接：
    # - 父图写入 normalized_question。
    # - 子图写入 retrieved_docs、context、route 和 answer。
    # - 父图最后读取子图结果，写入 final_response。
    question: str
    normalized_question: str
    retrieved_docs: list[RagDocument]
    context: str
    route: Literal["answer", "fallback"]
    answer: str
    final_response: str


class RagContext(TypedDict):
    # Runtime Context 保存本次运行的外部依赖和配置。
    # 这些信息不属于图执行过程中逐步变化的业务状态，因此不放进 State。
    knowledge_base_path: str
    top_k: int
    min_similarity: float
    embedding_model: str
    answer_model: str
    ollama_base_url: str
    vectorstore: InMemoryVectorStore


def load_support_docs(knowledge_base_path: str) -> list[Document]:
    # 本实验复用第 24 个实验的客服知识库，让读者可以对照观察：
    # 同一段 RAG 能力，从“平铺在父图里”变成“封装进子图里”。
    knowledge_base = Path(knowledge_base_path)
    raw_docs = [
        Document(
            page_content=knowledge_base.read_text(encoding="utf-8"),
            metadata={"source": str(knowledge_base)},
        )
    ]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=160,
        chunk_overlap=30,
        separators=["\n\n", "\n", "。", "，", " ", ""],
        add_start_index=True,
    )
    docs = splitter.split_documents(raw_docs)
    for index, doc in enumerate(docs, start=1):
        doc.metadata["chunk_index"] = index

    return docs


def build_vectorstore(
    knowledge_base_path: str,
    embedding_model: str,
    ollama_base_url: str,
) -> InMemoryVectorStore:
    # 向量库在图运行前构建一次，然后通过 Runtime Context 注入。
    # 这样每次 graph.invoke 只做检索和回答，不重复切分、向量化知识库。
    docs = load_support_docs(knowledge_base_path)
    embeddings = OllamaEmbeddings(
        model=embedding_model,
        base_url=ollama_base_url,
    )
    return InMemoryVectorStore.from_documents(docs, embeddings)


def get_normalized_question(state: RagState) -> str:
    # 子图统一读取 normalized_question，而不是直接读取 question。
    # 这能明确展示：父图先处理输入，子图消费父图写入的标准字段。
    question = state.get("normalized_question")
    if not question:
        raise ValueError("RagState 必须包含非空 normalized_question")
    return question


def normalize_question(state: RagState) -> RagState:
    # normalize_question 是父图节点。
    # 它只处理“进入 RAG 模块前”的输入整理，不参与 RAG 内部细节。
    raw_question = state.get("question", "")
    if not raw_question.strip():
        raise ValueError("RagState 必须包含非空 question")

    # 这里保持非常克制：只去掉问候语、空白和重复标点。
    # 实验重点不是做复杂 NLP，而是让父图写入一个子图会读取的字段。
    question = raw_question.strip()
    question = question.removeprefix("你好，我想问一下，")
    question = question.removeprefix("你好，我想问一下")
    question = question.replace("？？？", "？")
    question = question.replace("？？", "？")
    question = question.replace("??", "?")

    return {"normalized_question": question}


def retrieve_docs(state: RagState, runtime: Runtime[RagContext]) -> RagState:
    # retrieve_docs 是 RAG 子图的第一个节点。
    # 它读取父图写入的 normalized_question，并把检索结果写回共享 State。
    context = runtime.context
    question = get_normalized_question(state)

    results = context["vectorstore"].similarity_search_with_score(
        question,
        k=context["top_k"],
    )

    retrieved_docs: list[RagDocument] = []
    for doc, similarity in results:
        # min_similarity 是当前知识库和 embedding 模型下的实验阈值。
        # 低于阈值的资料不进入 answer 路径，后续条件边会走 fallback。
        if similarity < context["min_similarity"]:
            continue

        source = str(doc.metadata.get("source", "unknown"))
        retrieved_docs.append(
            {
                "source": Path(source).name,
                "chunk_index": int(doc.metadata.get("chunk_index", -1)),
                "start_index": int(doc.metadata.get("start_index", -1)),
                "content": doc.page_content,
                "similarity": similarity,
            }
        )

    return {"retrieved_docs": retrieved_docs}


def route_after_retrieve(state: RagState) -> Literal["build_context", "fallback"]:
    # 条件边只根据 retrieved_docs 是否为空决定子图内部路径。
    # 有资料就整理上下文并回答；没有资料就进入兜底节点。
    if state.get("retrieved_docs"):
        return "build_context"
    return "fallback"


def build_context(state: RagState) -> RagState:
    # build_context 仍然属于 RAG 子图内部。
    # 它把结构化检索结果转换成模型可直接阅读的上下文字符串。
    context_parts = []
    for index, doc in enumerate(state.get("retrieved_docs", []), start=1):
        context_parts.append(
            f"资料 {index}：{doc['source']}#chunk-{doc['chunk_index']}\n"
            f"相似度：{doc['similarity']:.3f}\n"
            f"起始位置：{doc['start_index']}\n"
            f"正文：{doc['content']}"
        )

    return {
        "context": "\n\n".join(context_parts),
        # route 写入 State，方便父图最后知道子图走的是回答路径还是兜底路径。
        "route": "answer",
    }


def answer(state: RagState, runtime: Runtime[RagContext]) -> RagState:
    # answer 是子图里的模型调用节点。
    # 它只基于 normalized_question 和 context 生成答案，不负责最终展示格式。
    context = runtime.context
    question = get_normalized_question(state)

    model = ChatOllama(
        model=context["answer_model"],
        base_url=context["ollama_base_url"],
        temperature=0,
    )

    prompt = f"""
你是客服问答助手。请只根据给定资料回答用户问题。

要求：
- 如果资料能回答，就直接给出简洁中文答复。
- 不要编造资料中没有的信息。
- 控制在 80 字以内。

用户问题：
{question}

检索资料：
{state.get("context", "")}
"""

    response = model.invoke(prompt)
    return {"answer": str(response.content).strip()}


def fallback(state: RagState) -> RagState:
    # fallback 是子图里的失败路径。
    # 没有足够相关资料时，子图仍然写回 answer，让父图后续可以统一处理。
    return {
        "route": "fallback",
        "context": "",
        "answer": (
            "当前知识库里没有找到足够相关的资料，建议转人工客服或补充更多问题信息。"
        ),
    }


def format_response(state: RagState) -> RagState:
    # format_response 是父图节点。
    # 它读取子图产出的 route、answer 和 retrieved_docs，生成最终展示给用户的回复。
    route = state.get("route", "fallback")
    answer_text = state.get("answer", "")
    docs = state.get("retrieved_docs", [])

    if route == "fallback" or not docs:
        return {"final_response": answer_text}

    references = [
        f"{doc['source']}#chunk-{doc['chunk_index']}"
        for doc in docs
    ]
    final_response = f"{answer_text}\n参考资料：{'; '.join(references)}"
    return {"final_response": final_response}


def build_rag_subgraph():
    # 子图只封装 RAG 内部流程：检索资料、判断是否有足够资料、整理上下文、回答或兜底。
    # 在父图连边时，rag_subgraph 像普通节点一样使用；
    # 但从设计语义看，它内部封装的是一整张 RAG 子图。
    builder = StateGraph(RagState, context_schema=RagContext)

    builder.add_node("retrieve_docs", retrieve_docs)
    builder.add_node("build_context", build_context)
    builder.add_node("answer", answer)
    builder.add_node("fallback", fallback)

    builder.add_edge(START, "retrieve_docs")
    builder.add_conditional_edges(
        "retrieve_docs",
        route_after_retrieve,
        {
            "build_context": "build_context",
            "fallback": "fallback",
        },
    )
    builder.add_edge("build_context", "answer")
    builder.add_edge("answer", END)
    builder.add_edge("fallback", END)

    # name 会出现在 stream namespace 和 checkpoint_ns 中，
    # 这是观察“子图运行边界”的关键证据之一。
    return builder.compile(name="rag_subgraph")


def build_parent_graph(checkpointer: InMemorySaver):
    # 父图负责高一层编排：
    # 输入整理 -> 调用 rag_subgraph 子图节点 -> 格式化最终回复。
    rag_subgraph = build_rag_subgraph()
    builder = StateGraph(RagState, context_schema=RagContext)

    builder.add_node("normalize_question", normalize_question)
    builder.add_node("rag_subgraph", rag_subgraph)
    builder.add_node("format_response", format_response)

    builder.add_edge(START, "normalize_question")
    builder.add_edge("normalize_question", "rag_subgraph")
    builder.add_edge("rag_subgraph", "format_response")
    builder.add_edge("format_response", END)

    # checkpointer 只挂在父图编译处。
    # LangGraph 会在运行时同时记录父图和子图内部的 checkpoint，
    # 子图 checkpoint 会进入 rag_subgraph:... 这样的 namespace。
    return builder.compile(
        checkpointer=checkpointer,
        name="parent_graph",
    )


def build_runtime_context() -> RagContext:
    # 本实验按用户要求只使用本地 Ollama 的两个模型：
    # qwen3-embedding:latest 负责向量化，qwen3-coder:30b 负责回答。
    knowledge_base_path = str(
        ROOT_DIR / "labs/rag/foundations/data/support_policy_retriever.txt"
    )
    embedding_model = "qwen3-embedding:latest"
    answer_model = "qwen3-coder:30b"
    ollama_base_url = "http://localhost:11434"

    vectorstore = build_vectorstore(
        knowledge_base_path=knowledge_base_path,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url,
    )

    return {
        "knowledge_base_path": knowledge_base_path,
        "top_k": 2,
        "min_similarity": 0.60,
        "embedding_model": embedding_model,
        "answer_model": answer_model,
        "ollama_base_url": ollama_base_url,
        "vectorstore": vectorstore,
    }


def make_thread_config(thread_id: str) -> RunnableConfig:
    # LangGraph 的 invoke、stream 和 checkpointer.list 都接收 RunnableConfig。
    # 单独封装这个小函数，可以避免让类型检查器把普通 dict 误判成不兼容类型。
    return {
        "configurable": {
            "thread_id": thread_id,
        }
    }


def get_namespace_label(namespace: tuple[str, ...]) -> str:
    # stream 返回的 namespace 里会带一次运行生成的随机 ID。
    # 实验输出只需要区分父图和 rag_subgraph，不展示完整 ID，避免干扰主线。
    if not namespace:
        return "父图"

    subgraph_name = namespace[0].split(":", maxsplit=1)[0]
    return f"子图 {subgraph_name}"


def print_stream_updates(graph, question: str, runtime_context: RagContext) -> None:
    # stream 观察的是“节点更新发生在哪一层图里”。
    # subgraphs=True 会让 LangGraph 把子图 namespace 一起返回。
    config = make_thread_config("rag-subgraph-stream-demo")
    grouped_updates: list[tuple[str, list[str]]] = []

    print("\n" + "=" * 72)
    print("stream 层级")
    print(f"问题：{question}")

    for namespace, update in graph.stream(
        {"question": question},
        config=config,
        context=runtime_context,
        stream_mode="updates",
        subgraphs=True,
    ):
        # namespace 为空表示父图节点更新；
        # namespace 类似 rag_subgraph:xxxx 表示子图内部节点更新。
        level = get_namespace_label(namespace)
        node_names = list(update.keys())

        if grouped_updates and grouped_updates[-1][0] == level:
            grouped_updates[-1][1].extend(node_names)
        else:
            grouped_updates.append((level, node_names))

    for level, node_names in grouped_updates:
        print(f"- {level}: {' -> '.join(node_names)}")


def print_final_result(index: int, final_state: Mapping[str, Any]) -> None:
    # 最终结果同时打印原始问题和标准问题，方便确认父图确实先改写了输入，
    # 子图后续使用的是 normalized_question。
    print("\n" + "=" * 72)
    print(f"运行结果 {index}")
    print(f"原始问题：{final_state.get('question')}")
    print(f"标准问题：{final_state.get('normalized_question')}")
    print(f"路径：{final_state.get('route')}")
    print(f"最终回复：{final_state.get('final_response')}")


def print_checkpoint_namespaces(checkpointer: InMemorySaver, thread_id: str) -> None:
    # checkpoint namespace 是这个实验最重要的观察点之一。
    # 同一个 thread_id 下，父图 checkpoint 的 namespace 为空；
    # 子图 checkpoint 会带 rag_subgraph:... 前缀。
    config = make_thread_config(thread_id)
    namespace_counts: dict[str, int] = {}

    for checkpoint in checkpointer.list(config):
        checkpoint_config = checkpoint.config.get("configurable", {})
        namespace = checkpoint_config.get("checkpoint_ns")
        if namespace:
            namespace_label = namespace.split(":", maxsplit=1)[0]
        else:
            namespace_label = "父图"
        namespace_counts[namespace_label] = namespace_counts.get(namespace_label, 0) + 1

    print("checkpoint namespace")
    for namespace_label, count in namespace_counts.items():
        print(f"- {namespace_label}: {count} 个 checkpoint")


def main() -> None:
    # 运行顺序刻意保持线性：
    # 1. 构建 Runtime Context 和 checkpointer。
    # 2. 构建父图，父图内部包含 RAG 子图。
    # 3. 先观察 stream 层级，再运行两个问题观察 checkpoint namespace。
    runtime_context = build_runtime_context()
    checkpointer = InMemorySaver()
    graph = build_parent_graph(checkpointer)

    print("实验配置")
    print(f"- 知识库：{Path(runtime_context['knowledge_base_path']).name}")
    print(
        f"- 模型：{runtime_context['embedding_model']} / "
        f"{runtime_context['answer_model']}"
    )
    print(
        f"- 检索：top_k={runtime_context['top_k']}, "
        f"min_similarity={runtime_context['min_similarity']}"
    )

    print_stream_updates(
        graph=graph,
        question="你好，我想问一下，未发货订单能退款吗？？？",
        runtime_context=runtime_context,
    )

    questions = [
        "你好，我想问一下，未发货订单能退款吗？？？",
        "积分可以提现吗？",
    ]

    for index, question in enumerate(questions, start=1):
        thread_id = f"rag-subgraph-result-{index}"
        config = make_thread_config(thread_id)
        final_state = graph.invoke(
            {"question": question},
            config=config,
            context=runtime_context,
        )
        print_final_result(index, final_state)
        print_checkpoint_namespaces(checkpointer, thread_id)


if __name__ == "__main__":
    main()
