"""导出 Handoff 客服工单实验的静态结构图和代表性运行路径图。"""

from pathlib import Path

import pygraphviz as pgv

from main import ALLOWED_HANDOFFS, build_graph


OUTPUT_DIR = Path(__file__).parent
ARCHITECTURE_PNG = OUTPUT_DIR / "handoff_support_ticket_architecture.png"
RUNTIME_PNG = OUTPUT_DIR / "handoff_support_ticket_runtime.png"

COLORS = {
    "terminal": "#eef2f7",
    "agent": "#dcecff",
    "finish": "#d9f5e5",
    "failed": "#fee2e2",
    "border": "#475569",
    "handoff": "#2563eb",
    "complete": "#15803d",
    "error": "#dc2626",
}


def add_node(
    graph: pgv.AGraph,
    node_id: str,
    label: str,
    color: str,
    shape: str = "box",
) -> None:
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


def base_graph() -> pgv.AGraph:
    graph = pgv.AGraph(strict=False, directed=True)
    graph.graph_attr.update(
        rankdir="TB",
        bgcolor="white",
        pad="0.30",
        nodesep="0.65",
        ranksep="0.75",
        splines="ortho",
    )
    graph.node_attr.update(fontname="Helvetica")
    graph.edge_attr.update(fontname="Helvetica", arrowsize="0.8")
    return graph


def node_style(node_id: str) -> tuple[str, str, str]:
    styles = {
        "__start__": ("START", COLORS["terminal"], "oval"),
        "refund_agent": ("refund_agent\n退款政策判断", COLORS["agent"], "box"),
        "technical_agent": ("technical_agent\n故障诊断", COLORS["agent"], "box"),
        "human_agent": ("human_agent\n例外审批", COLORS["agent"], "box"),
        "finish": ("finish\n流程正常结束", COLORS["finish"], "box"),
        "failed": ("failed\n移交被拒绝/前置条件缺失", COLORS["failed"], "box"),
        "__end__": ("END", COLORS["terminal"], "oval"),
    }
    return styles.get(node_id, (node_id, COLORS["agent"], "box"))


def render_architecture(output_path: Path) -> None:
    """绘制业务允许的移交结构，而不是宽泛的 Command 类型推断结果。"""
    # 仍然从编译图读取节点，确保图片与实际 StateGraph 的节点集合一致；
    # 边则使用业务白名单，避免 Command[HandoffTarget] 产生大量虚假的可能边。
    langgraph_graph = build_graph().get_graph()
    graph = base_graph()

    for node_id in langgraph_graph.nodes:
        label, color, shape = node_style(node_id)
        add_node(graph, node_id, label, color, shape)

    for source, targets in ALLOWED_HANDOFFS.items():
        for target in targets:
            graph.add_edge(
                source,
                target,
                color=(
                    COLORS["complete"]
                    if target == "finish"
                    else COLORS["handoff"]
                ),
                style="solid",
                penwidth=1.3,
            )

        # 非法目标、超出次数上限和缺少前置条件都会进入 failed。
        graph.add_edge(
            source,
            "failed",
            color=COLORS["error"],
            style="dashed",
            penwidth=1.2,
        )

    graph.add_edge("__start__", "refund_agent", color=COLORS["border"], penwidth=1.3)
    graph.add_edge("finish", "__end__", color=COLORS["complete"], penwidth=1.3)
    graph.add_edge("failed", "__end__", color=COLORS["error"], penwidth=1.3)

    graph.add_node(
        "legend",
        label=(
            "静态结构图\n"
            "蓝色：ALLOWED_HANDOFFS 允许的移交\n"
            "红色虚线：非法移交/前置条件失败\n"
            "绿色：正常结束"
        ),
        shape="note",
        style="filled",
        fillcolor="#f8fafc",
        color="#cbd5e1",
        fontname="Helvetica",
        fontsize=11,
        fontcolor="#475569",
    )

    graph.layout(prog="dot")
    graph.draw(output_path)
    print(f"Graphviz PNG saved to: {output_path}")


def render_runtime(output_path: Path) -> None:
    """绘制 README 中描述的正常运行路径。"""
    graph = base_graph()
    nodes = [
        ("start", "START", COLORS["terminal"], "oval"),
        ("refund_1", "refund_agent\n首次退款判断：缺少故障证据", COLORS["agent"], "box"),
        ("technical", "technical_agent\n完成故障诊断", COLORS["agent"], "box"),
        ("refund_2", "refund_agent\n拿到证据：需要例外审批", COLORS["agent"], "box"),
        ("human", "human_agent\n完成人工升级审批", COLORS["agent"], "box"),
        ("finish", "finish\n输出最终结果", COLORS["finish"], "box"),
        ("end", "END", COLORS["terminal"], "oval"),
    ]
    for node_id, label, color, shape in nodes:
        add_node(graph, node_id, label, color, shape)

    edges = [
        ("start", "refund_1", ""),
        ("refund_1", "technical", "1 缺少故障证据"),
        ("technical", "refund_2", "2 交回退款判断"),
        ("refund_2", "human", "3 升级人工审批"),
        ("human", "finish", "4 完成审批"),
        ("finish", "end", ""),
    ]
    for source, target, label in edges:
        graph.add_edge(
            source,
            target,
            xlabel=label,
            color=COLORS["complete"] if target == "end" else COLORS["handoff"],
            fontcolor=COLORS["handoff"],
            fontsize=12,
            penwidth=1.5,
        )

    graph.add_node(
        "legend",
        label="运行路径图\n蓝色实线：本次代表性成功路径",
        shape="note",
        style="filled",
        fillcolor="#f8fafc",
        color="#cbd5e1",
        fontname="Helvetica",
        fontsize=11,
        fontcolor="#475569",
    )

    graph.layout(prog="dot")
    graph.draw(output_path)
    print(f"Graphviz PNG saved to: {output_path}")


def main() -> None:
    render_architecture(ARCHITECTURE_PNG)
    render_runtime(RUNTIME_PNG)


if __name__ == "__main__":
    main()
