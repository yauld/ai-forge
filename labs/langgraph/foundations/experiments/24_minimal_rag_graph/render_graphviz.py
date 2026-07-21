from pathlib import Path

import pygraphviz as pgv

from main import build_graph


OUTPUT_PNG = Path(__file__).with_name("minimal_rag_graph.png")

NODE_LABELS = {
    "__start__": "START",
    "__end__": "END",
    "retrieve_docs": "retrieve_docs\n检索足够相关资料",
    "build_context": "build_context\n整理检索上下文",
    "answer": "answer\n基于资料回答",
    "fallback": "fallback\n无足够资料时兜底",
}

NODE_COLORS = {
    "__start__": "#e5e7eb",
    "__end__": "#e5e7eb",
    "retrieve_docs": "#dbeafe",
    "build_context": "#ecfccb",
    "answer": "#dcfce7",
    "fallback": "#fee2e2",
}

EDGE_LABELS = {
    ("retrieve_docs", "build_context"): "有足够相关资料",
    ("retrieve_docs", "fallback"): "无足够相关资料",
}


def add_nodes(graphviz_graph: pgv.AGraph, langgraph_graph) -> None:
    for node_id in langgraph_graph.nodes:
        shape = "oval" if node_id in {"__start__", "__end__"} else "box"
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
        key = (edge.source, edge.target)
        graphviz_graph.add_edge(
            edge.source,
            edge.target,
            label=EDGE_LABELS.get(key, ""),
            color="#64748b",
            fontname="Helvetica",
            fontsize=11,
            arrowsize=0.8,
        )


def main() -> None:
    langgraph_graph = build_graph().get_graph()

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
    graphviz_graph.draw(OUTPUT_PNG)

    print(f"Graphviz PNG saved to: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
