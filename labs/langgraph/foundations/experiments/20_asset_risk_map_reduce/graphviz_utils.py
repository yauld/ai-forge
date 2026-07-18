"""资产风险 Map-Reduce 实验的图像导出工具。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from asset_schemas import Asset


EXPERIMENT_DIR = Path(__file__).resolve().parent
DEFAULT_GRAPHVIZ_OUTPUT = EXPERIMENT_DIR / "asset_risk_map_reduce_graph.png"
DEFAULT_RUNTIME_GRAPHVIZ_OUTPUT = (
    EXPERIMENT_DIR / "asset_risk_map_reduce_runtime_graph.png"
)


def render_graphviz(build_graph: Any, output_path: Path) -> None:
    """导出 LangGraph 静态结构图。

    这张图只展示图里定义了哪些节点。Send 在运行时创建的多个分支不会在这里展开。
    """
    graph = build_graph()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(graph.get_graph().draw_png(None))
    print(f"LangGraph 静态结构图已生成：{output_path}")


def render_runtime_graphviz(assets: list[Asset], output_path: Path) -> None:
    """按本次输入资产生成运行时 Map-Reduce 示意图。

    LangGraph 的结构图只会画一个 check_asset 节点；这个函数刻意把每个 Send
    创建出来的逻辑分支展开，帮助读者看懂“4 个资产就是 4 个 Map 任务”。
    """
    import pygraphviz as pgv

    graph = pgv.AGraph(directed=True, strict=False)
    graph.graph_attr.update(rankdir="TB", splines="polyline", nodesep="0.45", ranksep="0.7")
    graph.node_attr.update(
        shape="box",
        style="rounded,filled",
        fontname="Helvetica",
        fontsize="12",
        color="#334155",
        penwidth="1.2",
    )
    graph.edge_attr.update(fontname="Helvetica", fontsize="10", color="#475569")

    graph.add_node("start", label="START", shape="ellipse", fillcolor="#bfdbfe")
    graph.add_node("prepare", label="prepare_scan\n读取资产列表", fillcolor="#fef08a")
    graph.add_node(
        "reducer",
        label="reducer\n合并 findings",
        shape="diamond",
        fillcolor="#d9f99d",
    )
    graph.add_node("summarize", label="summarize_risks\n生成风险报告", fillcolor="#fef08a")
    graph.add_node("end", label="END", shape="ellipse", fillcolor="#fed7aa")

    graph.add_edge("start", "prepare")
    graph.add_edge("prepare", "reducer", style="invis")

    for index, asset in enumerate(assets, start=1):
        host = asset["host"]
        map_node = f"map_{index}"
        finding_node = f"finding_{index}"
        graph.add_node(
            map_node,
            label=f"check_asset #{index}\n{host}",
            fillcolor="#fde68a",
        )
        graph.add_node(
            finding_node,
            label=f"finding #{index}\n{host}",
            fillcolor="#e0f2fe",
        )
        graph.add_edge("prepare", map_node, label=f"Send(asset_{index})", style="dashed")
        graph.add_edge(map_node, finding_node, label="Map")
        graph.add_edge(finding_node, "reducer", label="append")

    graph.add_edge("reducer", "summarize", label="Reduce input")
    graph.add_edge("summarize", "end")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.draw(str(output_path), prog="dot")
    print(f"运行时 Map-Reduce 示意图已生成：{output_path}")
