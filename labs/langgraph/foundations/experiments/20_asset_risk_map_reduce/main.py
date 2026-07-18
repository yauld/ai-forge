"""用资产暴露风险检查演示 LangGraph Send 与 Map-Reduce。

这个实验刻意使用一组固定的模拟资产，不做真实网络扫描。重点不是发现真实漏洞，
而是观察：LangGraph 如何根据输入资产数量动态创建多个并行任务，并把每个任务的
检查结果合并回同一个 State。
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from asset_schemas import Asset, AssetTaskState, Finding, RiskScanState
from asset_schemas import SAMPLE_ASSETS
from graphviz_utils import DEFAULT_GRAPHVIZ_OUTPUT, DEFAULT_RUNTIME_GRAPHVIZ_OUTPUT
from graphviz_utils import render_graphviz, render_runtime_graphviz
from risk_rules import assess_asset_by_rules


DEFAULT_OLLAMA_MODEL = "qwen3-coder:30b"
llm = ChatOllama(model=DEFAULT_OLLAMA_MODEL, temperature=0)


def build_asset_prompt(asset: Asset, risk: str, rule_reason: str) -> list[Any]:
    """构造单资产研判提示词。"""
    asset_json = json.dumps(asset, ensure_ascii=False, indent=2)
    return [
        SystemMessage(
            content=(
                "你是企业安全工程师。请基于给定资产信息写一段简短研判。"
                "不要编造扫描结果，不要声称已经真实访问目标。"
            )
        ),
        HumanMessage(
            content=(
                "请用一小段话分析下面这个资产的暴露风险，并给出简短处置建议。\n\n"
                f"规则判定风险等级：{risk}\n"
                f"规则命中原因：{rule_reason}\n"
                f"资产信息：\n{asset_json}"
            )
        ),
    ]


def prepare_scan(state: RiskScanState) -> RiskScanState:
    """准备节点：确认本轮要处理的资产数量。

    这个节点不做安全分析，也不拆分任务，只负责在 trace 里留下一个清晰的起点。
    它返回后，LangGraph 会立刻调用 `send_each_asset_to_checker`，由那个函数根据
    `state["assets"]` 动态创建多个 Send。
    """
    assets = state.get("assets", [])
    return {
        # `trace` 配了列表拼接 reducer，所以这里返回一条列表记录即可。
        "trace": [f"[准备] 收到 {len(assets)} 个资产，下一步用 Send 动态分发检查任务。"],
    }


def send_each_asset_to_checker(state: RiskScanState) -> list[Send]:
    """Send 分发函数：资产列表里有几项，就创建几个 Map 任务。

    这个函数不是普通业务节点，而是 `add_conditional_edges` 使用的动态路由函数。
    它返回的每个 `Send("check_asset", {"asset": asset})` 都表示：

    - 目标节点是 `check_asset`；
    - 这个目标节点本次只接收一个资产；
    - 多个 Send 会形成多个可并行执行的 Map 分支。
    """
    send_tasks = []
    for asset in state.get("assets", []):
        # 注意：这里的 for 只是创建 Send 指令，不是在这里顺序执行 check_asset。
        send_tasks.append(Send("check_asset", {"asset": asset}))
    return send_tasks


async def check_asset(state: AssetTaskState) -> RiskScanState:
    """Map 节点：每次只检查一个资产，并返回一条 finding。

    由于 `send_each_asset_to_checker` 给每个资产都创建了一个 Send，这个节点在运行时
    会被调用多次。每次调用拿到的 state 都是局部状态，形如：

    `{"asset": 当前资产}`

    所以这个函数不用关心完整资产列表，只需要完成“一个资产 -> 一条 finding”。
    """
    asset = state["asset"]
    risk, rule_reason = assess_asset_by_rules(asset)
    response = await llm.ainvoke(build_asset_prompt(asset, risk, rule_reason))

    finding: Finding = {
        "host": asset["host"],
        "risk": risk,
        "rule_reason": rule_reason,
        "model_analysis": str(response.content).strip(),
    }
    return {
        # 每个 Map 分支都返回单元素列表。LangGraph 会用 RiskScanState.findings 上
        # 声明的 reducer，把多个分支的列表拼成一个完整 findings 列表。
        "findings": [finding],
        "trace": [f"[Map] {asset['host']} 检查完成，风险等级：{risk}。"],
    }


def build_reduce_prompt(findings: list[Finding]) -> list[Any]:
    """构造最终汇总提示词。"""
    findings_json = json.dumps(findings, ensure_ascii=False, indent=2)
    return [
        SystemMessage(
            content=(
                "你是企业安全负责人。请把多条资产检查结果汇总成一份简短风险报告。"
                "只使用输入中的事实，按优先级给出处置建议，不要使用 emoji 或装饰符号。"
            )
        ),
        HumanMessage(
            content=(
                "请输出三部分：\n"
                "1. 总体结论\n"
                "2. 风险分布\n"
                "3. 优先处置建议\n\n"
                f"资产检查结果：\n{findings_json}"
            )
        ),
    ]


async def summarize_risks(state: RiskScanState) -> RiskScanState:
    """Reduce 节点：把所有 Map 结果合成最终报告。

    运行到这里时，多个 `check_asset` 分支返回的 `findings` 已经被 reducer 合并完成。
    因此这个节点读取的是完整 findings 列表，而不是单个资产结果。
    """
    findings = sort_findings(state.get("findings", []))
    response = await llm.ainvoke(build_reduce_prompt(findings))
    final_report = str(response.content).strip()

    return {
        # Reduce 只写最终报告，不再返回 findings。
        # 如果这里再次返回 findings，会触发列表 reducer 再拼一次，导致结果重复。
        "final_report": final_report,
        "trace": [f"[Reduce] 已汇总 {len(findings)} 条资产检查结果。"],
    }


def sort_findings(findings: list[Finding]) -> list[Finding]:
    """按安全处置优先级展示检查结果。"""
    return sorted(findings, key=lambda item: {"高": 0, "中": 1, "低": 2}[item["risk"]])


def build_asset_risk_graph():
    """构建 Send + Map-Reduce 实验图。"""
    builder = StateGraph(RiskScanState)
    builder.add_node("prepare_scan", prepare_scan)
    builder.add_node("check_asset", check_asset)
    builder.add_node("summarize_risks", summarize_risks)

    builder.add_edge(START, "prepare_scan")
    builder.add_conditional_edges("prepare_scan", send_each_asset_to_checker, ["check_asset"])
    builder.add_edge("check_asset", "summarize_risks")
    builder.add_edge("summarize_risks", END)

    return builder.compile(name="Asset Risk Map Reduce")


def load_assets(path: str | None) -> list[Asset]:
    """读取资产输入；不传文件时使用实验内置样例。"""
    if path is None:
        return list(SAMPLE_ASSETS)
    return json.loads(Path(path).expanduser().read_text(encoding="utf-8"))


async def run_experiment(asset_file: str | None) -> None:
    """运行完整实验并打印 trace、Map 结果与 Reduce 报告。"""
    assets = load_assets(asset_file)
    graph = build_asset_risk_graph()

    print("实验：LangGraph Send 并行分发与 Map-Reduce")
    print(f"资产数量：{len(assets)}")
    print("模型提供方：ollama")
    print(f"模型：{DEFAULT_OLLAMA_MODEL}")
    print()

    final_state = await graph.ainvoke({"assets": assets, "findings": [], "trace": []})

    print("========== LangGraph Trace ==========")
    for item in final_state["trace"]:
        print(item)

    print()
    print("========== Map 结果 ==========")
    for finding in sort_findings(final_state["findings"]):
        print(
            f"- {finding['host']}｜{finding['risk']}｜"
            f"{finding['rule_reason']}｜{finding['model_analysis']}"
        )

    print()
    print("========== Reduce 汇总报告 ==========")
    print(final_state["final_report"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行 LangGraph Send + Map-Reduce 资产暴露风险检查实验。"
    )
    parser.add_argument(
        "--assets",
        help="可选，自定义资产 JSON 文件路径；不传则使用内置样例。",
    )
    parser.add_argument(
        "--graphviz",
        nargs="?",
        const=str(DEFAULT_GRAPHVIZ_OUTPUT),
        metavar="PNG_PATH",
        help=(
            "只导出当前 LangGraph 结构图，不运行模型。"
            f"不传路径时默认输出到 {DEFAULT_GRAPHVIZ_OUTPUT}。"
        ),
    )
    parser.add_argument(
        "--runtime-graphviz",
        nargs="?",
        const=str(DEFAULT_RUNTIME_GRAPHVIZ_OUTPUT),
        metavar="PNG_PATH",
        help=(
            "按本次资产输入导出运行时 Map-Reduce 示意图，会展开每个 Send 分支。"
            f"不传路径时默认输出到 {DEFAULT_RUNTIME_GRAPHVIZ_OUTPUT}。"
        ),
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.graphviz:
        render_graphviz(
            build_asset_risk_graph,
            Path(args.graphviz).expanduser(),
        )
        return
    if args.runtime_graphviz:
        render_runtime_graphviz(
            load_assets(args.assets),
            Path(args.runtime_graphviz).expanduser(),
        )
        return

    asyncio.run(
        run_experiment(
            asset_file=args.assets,
        )
    )


if __name__ == "__main__":
    main()
