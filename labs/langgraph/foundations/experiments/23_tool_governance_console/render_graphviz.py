from pathlib import Path

import pygraphviz as pgv

from main import build_graph


OUTPUT_PNG = Path(__file__).with_name("tool_governance_graphviz.png")

NODE_LABELS = {
    "__start__": "START",
    "__end__": "END",
}

EDGE_LABELS = {
    ("approval_gate", "execute_tool"): "approved / readonly",
    ("approval_gate", "append_audit_log"): "denied / blocked",
    ("retry_or_fallback", "execute_tool"): "retry",
    ("retry_or_fallback", "append_audit_log"): "success / fallback",
}

NODE_COLORS = {
    "__start__": "#e5e7eb",
    "__end__": "#e5e7eb",
    "classify_request": "#fff7ed",
    "plan_action": "#fff7ed",
    "enforce_tool_policy": "#ecfccb",
    "approval_gate": "#fef9c3",
    "execute_tool": "#dcfce7",
    "handle_tool_error": "#dbeafe",
    "retry_or_fallback": "#ccfbf1",
    "append_audit_log": "#ffe4e6",
    "final_response": "#dcfce7",
}


def add_graph_nodes(graphviz_graph: pgv.AGraph, langgraph_graph) -> None:
    for node_id in langgraph_graph.nodes:
        label = NODE_LABELS.get(node_id, node_id)
        shape = "oval" if node_id in {"__start__", "__end__"} else "box"
        graphviz_graph.add_node(
            node_id,
            label=label,
            shape=shape,
            style="rounded,filled",
            fillcolor=NODE_COLORS.get(node_id, "#f8fafc"),
            color="#334155",
            fontname="Helvetica",
            fontsize=14,
            margin="0.16,0.10",
        )


def add_graph_edges(graphviz_graph: pgv.AGraph, langgraph_graph) -> None:
    for edge in langgraph_graph.edges:
        key = (edge.source, edge.target)
        label = EDGE_LABELS.get(key, "")
        is_side_path = key in {
            ("approval_gate", "append_audit_log"),
            ("retry_or_fallback", "execute_tool"),
        }
        graphviz_graph.add_edge(
            edge.source,
            edge.target,
            label=label,
            color="#64748b",
            fontname="Helvetica",
            fontsize=11,
            arrowsize=0.8,
            constraint="false" if is_side_path else "true",
            weight=1 if is_side_path else 8,
        )


def main() -> None:
    langgraph_graph = build_graph(use_checkpointer=False).get_graph()

    graphviz_graph = pgv.AGraph(strict=False, directed=True)
    graphviz_graph.graph_attr.update(
        rankdir="TB",
        bgcolor="white",
        pad="0.35",
        nodesep="0.45",
        ranksep="0.62",
        splines="polyline",
        concentrate="false",
    )
    graphviz_graph.node_attr.update(fontname="Helvetica")
    graphviz_graph.edge_attr.update(fontname="Helvetica")

    add_graph_nodes(graphviz_graph, langgraph_graph)
    add_graph_edges(graphviz_graph, langgraph_graph)

    graphviz_graph.layout(prog="dot")
    graphviz_graph.draw(OUTPUT_PNG)

    print(f"Graphviz PNG saved to: {OUTPUT_PNG}")


if __name__ == "__main__":
    main()
