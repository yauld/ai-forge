from pathlib import Path
from typing import Literal, TypedDict

from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime


ROOT_DIR = Path(__file__).resolve().parents[5]


class RagDocument(TypedDict):
    # 检索结果进入 State 前先整理成稳定的字段，方便后续节点读取。
    source: str
    chunk_index: int
    start_index: int
    content: str
    similarity: float


class RagState(TypedDict, total=False):
    # State 保存一次问答执行中不断产生的业务数据。
    question: str
    retrieved_docs: list[RagDocument]
    context: str
    route: Literal["answer", "fallback"]
    answer: str


class RagContext(TypedDict):
    # Runtime Context 保存本次运行需要的配置和外部依赖。
    knowledge_base_path: str
    top_k: int
    min_similarity: float
    embedding_model: str
    answer_model: str
    ollama_base_url: str
    vectorstore: InMemoryVectorStore


def load_support_docs(knowledge_base_path: str) -> list[Document]:
    # 本例只有一个本地 txt 文件，直接加载为带 source 元数据的 Document。
    # 切分交给 RecursiveCharacterTextSplitter 处理。
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
    # 向量库只构建一次，后续多个问题复用同一个索引。
    docs = load_support_docs(knowledge_base_path)
    embeddings = OllamaEmbeddings(
        model=embedding_model,
        base_url=ollama_base_url,
    )
    return InMemoryVectorStore.from_documents(docs, embeddings)


def get_question(state: RagState) -> str:
    question = state.get("question")
    if not question:
        raise ValueError("RagState 必须包含非空 question")

    return question


def retrieve_docs(state: RagState, runtime: Runtime[RagContext]) -> RagState:
    context = runtime.context
    question = get_question(state)

    # 检索节点读取用户问题，查询向量库，并写回相关资料。
    results = context["vectorstore"].similarity_search_with_score(
        question,
        k=context["top_k"],
    )

    retrieved_docs: list[RagDocument] = []

    # 低于阈值的资料不进入后续回答流程。
    for doc, similarity in results:
        if similarity < context["min_similarity"]:
            continue

        source = str(doc.metadata.get("source", "unknown"))
        chunk_index = int(doc.metadata.get("chunk_index", -1))
        start_index = int(doc.metadata.get("start_index", -1))
        retrieved_docs.append(
            {
                "source": Path(source).name,
                "chunk_index": chunk_index,
                "start_index": start_index,
                "content": doc.page_content,
                "similarity": similarity,
            }
        )

    return {"retrieved_docs": retrieved_docs}


def route_after_retrieve(state: RagState) -> Literal["build_context", "fallback"]:
    # 有足够相关资料就继续回答，否则走兜底回复。
    if state.get("retrieved_docs"):
        return "build_context"

    return "fallback"


def build_context(state: RagState) -> RagState:
    # 把结构化检索结果整理成模型可直接阅读的上下文。
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
        "route": "answer",
    }


def answer(state: RagState, runtime: Runtime[RagContext]) -> RagState:
    context = runtime.context
    question = get_question(state)

    # 回答节点只基于用户问题和检索上下文生成回复。
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
    # 没有足够相关资料时，直接返回兜底回复。
    return {
        "route": "fallback",
        "context": "",
        "answer": (
            "当前知识库里没有找到足够相关的资料，建议转人工客服或补充更多问题信息。"
        ),
    }


def build_graph():
    graph_builder = StateGraph(RagState, context_schema=RagContext)

    # 最小 RAG 图：检索资料、整理上下文、生成回答，或进入 fallback。
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

    return graph_builder.compile()


def print_experiment_config(runtime_context: RagContext) -> None:
    print("实验配置")
    print(f"- 知识库：{runtime_context['knowledge_base_path']}")
    print(f"- Embedding 模型：{runtime_context['embedding_model']}")
    print(f"- 回答模型：{runtime_context['answer_model']}")
    print(
        f"- 检索参数：top_k={runtime_context['top_k']}, "
        f"min_similarity={runtime_context['min_similarity']}"
    )


def print_result(index: int, final_state) -> None:
    print("\n" + "-" * 72)
    print(f"问题 {index}：{final_state.get('question')}")
    print(f"路径：{final_state.get('route')}")
    print(f"最终回答：{final_state.get('answer')}")

    retrieved_docs = final_state.get("retrieved_docs", [])
    if not retrieved_docs:
        print("参考资料：无")
        return

    references = [
        (
            f"[{doc_index}] {doc['source']}#chunk-{doc['chunk_index']}"
            f"@{doc['start_index']}({doc['similarity']:.3f})"
        )
        for doc_index, doc in enumerate(retrieved_docs, start=1)
    ]
    print(f"参考资料：{'; '.join(references)}")


def main() -> None:
    graph = build_graph()

    # 这些配置会传入 Runtime Context；每次调用的初始 State 只放用户问题。
    knowledge_base_path = str(
        ROOT_DIR / "labs/rag/foundations/data/support_policy_retriever.txt"
    )
    embedding_model = "qwen3-embedding:latest"
    answer_model = "qwen3-coder:30b"
    ollama_base_url = "http://localhost:11434"

    # 启动时先把知识库加载、切分、向量化，并写入内存向量库。
    # 后面每个问题只查询这个 vectorstore，不重复构建索引。
    vectorstore = build_vectorstore(
        knowledge_base_path=knowledge_base_path,
        embedding_model=embedding_model,
        ollama_base_url=ollama_base_url,
    )

    runtime_context: RagContext = {
        "knowledge_base_path": knowledge_base_path,
        "top_k": 2,
        "min_similarity": 0.60,
        "embedding_model": embedding_model,
        "answer_model": answer_model,
        "ollama_base_url": ollama_base_url,
        "vectorstore": vectorstore,
    }

    questions = [
        "未发货订单能退款吗？",
        "电子发票在哪里下载？",
        "积分可以提现吗？",
    ]

    print_experiment_config(runtime_context)

    for index, question in enumerate(questions, start=1):
        initial_state: RagState = {"question": question}
        final_state = graph.invoke(initial_state, context=runtime_context)
        print_result(index, final_state)


if __name__ == "__main__":
    main()
