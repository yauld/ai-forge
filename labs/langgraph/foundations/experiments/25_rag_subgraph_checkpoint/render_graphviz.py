from pathlib import Path

import pygraphviz as pgv
from langgraph.checkpoint.memory import InMemorySaver

from main import build_parent_graph


PARENT_GRAPH_PNG = Path(__file__).with_name("rag_subgraph_parent_graph.png")
XRAY_GRAPH_PNG = Path(__file__).with_name("rag_subgraph_xray_graph.png")

NODE_LABELS = {
    "__start__": "START",
    "__end__": "END",
    "normalize_question": "normalize_question\n整理用户问题",
    "rag_subgraph": "rag_subgraph\nRAG 子图模块",
    "format_response": "format_response\n格式化最终回复",
    "rag_subgraph:retrieve_docs": "retrieve_docs\n检索足够相关资料",
    "rag_subgraph:build_context": "build_context\n整理检索上下文",
    "rag_subgraph:answer": "answer\n基于资料回答",
    "rag_subgraph:fallback": "fallback\n无足够资料时兜底",
    "rag_subgraph:__end__": "RAG END",
}

NODE_COLORS = {
    "__start__": "#e5e7eb",
    "__end__": "#e5e7eb",
    "normalize_question": "#fef3c7",
    "rag_subgraph": "#dbeafe",
    "format_response": "#fef3c7",
    "rag_subgraph:retrieve_docs": "#dbeafe",
    "rag_subgraph:build_context": "#ecfccb",
    "rag_subgraph:answer": "#dcfce7",
    "rag_subgraph:fallback": "#fee2e2",
    "rag_subgraph:__end__": "#e5e7eb",
}

EDGE_LABELS = {
    ("rag_subgraph:retrieve_docs", "rag_subgraph:build_context"): "有足够相关资料",
    ("rag_subgraph:retrieve_docs", "rag_subgraph:fallback"): "无足够相关资料",
}


def normalize_node_id(node_id: str) -> str:
    # xray=True 展开子图后，节点名会带上子图前缀。
    return node_id.replace("\\3a", ":")


def add_nodes(graphviz_graph: pgv.AGraph, langgraph_graph) -> None:
    for raw_node_id in langgraph_graph.nodes:
        node_id = normalize_node_id(raw_node_id)
        shape = (
            "oval"
            if node_id in {"__start__", "__end__", "rag_subgraph:__end__"}
            else "box"
        )
        graphviz_graph.add_node(
            node_id,
            label=NODE_LABELS.get(node_id, node_id),
            shape=shape,
            style="rounded,filled",
            fillcolor=NODE_COLORS.get(node_id, "#f8fafc"),
            color="#334155",
            fontname="Helvetica",
            fontsize=14,
            margin="0.18,0.12",
        )


def add_edges(graphviz_graph: pgv.AGraph, langgraph_graph) -> None:
    for edge in langgraph_graph.edges:
        source = normalize_node_id(edge.source)
        target = normalize_node_id(edge.target)
        key = (source, target)
        graphviz_graph.add_edge(
            source,
            target,
            label=EDGE_LABELS.get(key, ""),
            color="#64748b",
            fontname="Helvetica",
            fontsize=11,
            arrowsize=0.8,
        )


def render_graph(langgraph_graph, output_path: Path) -> None:
    graphviz_graph = pgv.AGraph(strict=False, directed=True)
    graphviz_graph.graph_attr.update(
        rankdir="TB",
        bgcolor="white",
        pad="0.35",
        nodesep="0.48",
        ranksep="0.70",
        splines="polyline",
    )
    graphviz_graph.node_attr.update(fontname="Helvetica")
    graphviz_graph.edge_attr.update(fontname="Helvetica")

    add_nodes(graphviz_graph, langgraph_graph)
    add_edges(graphviz_graph, langgraph_graph)

    graphviz_graph.layout(prog="dot")
    graphviz_graph.draw(output_path)

    print(f"Graphviz PNG saved to: {output_path}")


def main() -> None:
    graph = build_parent_graph(checkpointer=InMemorySaver())

    # 普通视图：父图只把 rag_subgraph 看成一个模块节点。
    render_graph(graph.get_graph(), PARENT_GRAPH_PNG)

    # 展开视图：把 rag_subgraph 内部节点展开，便于观察子图细节。
    render_graph(graph.get_graph(xray=True), XRAY_GRAPH_PNG)


if __name__ == "__main__":
    main()
