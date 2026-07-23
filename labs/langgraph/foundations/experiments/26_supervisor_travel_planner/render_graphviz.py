from pathlib import Path

import pygraphviz as pgv


OUTPUT_DIR = Path(__file__).parent
ARCHITECTURE_PNG = OUTPUT_DIR / "supervisor_travel_planner_architecture.png"
RUNTIME_PNG = OUTPUT_DIR / "supervisor_travel_planner_runtime.png"

COLORS = {
    "terminal": "#eef2f7",
    "supervisor": "#fff2bf",
    "agent": "#dcecff",
    "optimizer": "#d9f5e5",
    "finish": "#f1f5f9",
    "border": "#475569",
    "dispatch": "#2563eb",
    "return": "#64748b",
    "complete": "#15803d",
}


def add_node(graph: pgv.AGraph, node_id: str, label: str, color: str, shape: str = "box") -> None:
    graph.add_node(
        node_id,
        label=label,
        shape=shape,
        style="rounded,filled",
        fillcolor=color,
        color=COLORS["border"],
        fontname="Helvetica",
        fontsize=14,
        margin="0.20,0.14",
    )


def base_graph(rankdir: str = "TB") -> pgv.AGraph:
    graph = pgv.AGraph(strict=False, directed=True)
    graph.graph_attr.update(
        rankdir=rankdir,
        bgcolor="white",
        pad="0.30",
        nodesep="0.65",
        ranksep="0.75",
        splines="ortho",
    )
    graph.node_attr.update(fontname="Helvetica")
    graph.edge_attr.update(fontname="Helvetica", arrowsize="0.8")
    return graph


def add_legend(graph: pgv.AGraph) -> None:
    graph.add_node(
        "legend",
        label="图例\\n蓝色实线：Supervisor 分配任务\\n灰色虚线：Agent 返回结果",
        shape="note",
        style="filled",
        fillcolor="#f8fafc",
        color="#cbd5e1",
        fontname="Helvetica",
        fontsize=11,
        fontcolor="#475569",
    )


def render_architecture(output_path: Path) -> None:
    """绘制中心调度关系，不把所有运行细节挤进一张图。"""
    graph = base_graph()
    add_node(graph, "start", "START", COLORS["terminal"], "oval")
    add_node(graph, "supervisor", "Supervisor\\n中心 Agent 统一调度", COLORS["supervisor"])
    add_node(graph, "attractions", "景点规划子Agent\\n规划初步行程", COLORS["agent"])
    add_node(graph, "budget", "预算约束子Agent\\n提取预算约束", COLORS["agent"])
    add_node(graph, "optimizer", "行程优化子Agent\\n生成最终方案", COLORS["optimizer"])
    add_node(graph, "finish", "Finish\\n输出最终结果", COLORS["finish"])
    add_node(graph, "end", "END", COLORS["terminal"], "oval")
    add_legend(graph)

    # 三个专业子Agent同层排列，突出它们都是 Supervisor 的下属角色。
    graph.add_subgraph(
        ["attractions", "budget", "optimizer"],
        name="agent_row",
        rank="same",
    )

    graph.add_edge("start", "supervisor", color=COLORS["border"])
    for agent in ["attractions", "budget", "optimizer"]:
        graph.add_edge(
            "supervisor",
            agent,
            color=COLORS["dispatch"],
            penwidth=1.4,
            fontcolor=COLORS["dispatch"],
        )
        graph.add_edge(
            agent,
            "supervisor",
            color=COLORS["return"],
            style="dashed",
            penwidth=1.2,
            constraint="false",
        )
    graph.add_edge("supervisor", "finish", color=COLORS["complete"], penwidth=1.4)
    graph.add_edge("finish", "end", color=COLORS["complete"], penwidth=1.4)

    graph.layout(prog="dot")
    graph.draw(output_path)
    print(f"Graphviz PNG saved to: {output_path}")


def render_runtime(output_path: Path) -> None:
    """绘制一条代表性运行路径，避免把可选顺序误画成固定流程。"""
    graph = base_graph()
    nodes = [
        ("start", "START", COLORS["terminal"], "oval"),
        ("supervisor_1", "Supervisor\\n选择预算约束子Agent", COLORS["supervisor"], "box"),
        ("budget", "预算约束子Agent\\n提取预算约束", COLORS["agent"], "box"),
        ("supervisor_2", "Supervisor\\n选择景点规划", COLORS["supervisor"], "box"),
        ("attractions", "景点规划子Agent\\n规划初步行程", COLORS["agent"], "box"),
        ("supervisor_3", "Supervisor\\n选择行程优化", COLORS["supervisor"], "box"),
        ("optimizer", "行程优化子Agent\\n生成最终方案", COLORS["optimizer"], "box"),
        ("supervisor_4", "Supervisor\\n确认任务完成", COLORS["supervisor"], "box"),
        ("finish", "Finish\\n输出最终结果", COLORS["finish"], "box"),
        ("end", "END", COLORS["terminal"], "oval"),
    ]
    for node_id, label, color, shape in nodes:
        add_node(graph, node_id, label, color, shape)

    for source, target in zip([node[0] for node in nodes], [node[0] for node in nodes][1:]):
        graph.add_edge(source, target, color=COLORS["border"], penwidth=1.3)

    graph.layout(prog="dot")
    graph.draw(output_path)
    print(f"Graphviz PNG saved to: {output_path}")


def main() -> None:
    render_architecture(ARCHITECTURE_PNG)
    render_runtime(RUNTIME_PNG)


if __name__ == "__main__":
    main()
