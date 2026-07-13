"""运行阶段 11：LangGraph + Skills runtime 实验。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from langgraph.types import Command

from graph import DEFAULT_CHECKPOINT_PATH, DEFAULT_MODEL, DEFAULT_OUTPUT_PATH, compile_graph


DEFAULT_TASK = "帮我查询订单 O-1001，生成一份简短订单报告，确认后写入本地报告文件。"
DEFAULT_THREAD_ID = "stage11-order-report-demo"


def run_pause(args: argparse.Namespace) -> None:
    graph, connection = compile_graph(args.checkpoint_path)
    try:
        result = graph.invoke(
            {
                "task": args.task,
                "model_name": args.model,
                "output_path": str(args.output_path),
                "trace": [],
            },
            _config(args.thread_id), # type: ignore
        )
        _print_result("pause_result", result)
        snapshot = graph.get_state(_config(args.thread_id)) # type: ignore
        print("checkpoint_next:", snapshot.next)
        print("checkpoint_values_keys:", sorted(snapshot.values.keys()))
    finally:
        connection.close()


def run_resume(args: argparse.Namespace, approval: str) -> None:
    graph, connection = compile_graph(args.checkpoint_path)
    try:
        result = graph.invoke(Command(resume=approval), _config(args.thread_id)) # type: ignore
        _print_result("resume_result", result)
        snapshot = graph.get_state(_config(args.thread_id)) # type: ignore
        print("checkpoint_next:", snapshot.next)
        print("final_answer:", snapshot.values.get("final_answer", ""))
    finally:
        connection.close()


def _config(thread_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": thread_id}}


def _print_result(label: str, result: dict[str, Any]) -> None:
    printable = {
        "selected_skill": result.get("selected_skill"),
        "route_reason": result.get("route_reason"),
        "route_raw_response": result.get("route_raw_response"),
        "mcp_tools": result.get("mcp_tools"),
        "tool_call_plan": result.get("tool_call_plan"),
        "tool_call_raw_response": result.get("tool_call_raw_response"),
        "order_id": result.get("order_id"),
        "tool_result": result.get("tool_result"),
        "report_draft": result.get("report_draft"),
        "approval": result.get("approval"),
        "write_result": result.get("write_result"),
        "final_answer": result.get("final_answer"),
        "trace": result.get("trace", []),
        "__interrupt__": _serialize_interrupts(result.get("__interrupt__")),
    }
    print(label + ":", json.dumps(printable, ensure_ascii=False, indent=2))


def _serialize_interrupts(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []

    serialized: list[dict[str, Any]] = []
    for item in value:
        serialized.append(
            {
                "id": getattr(item, "id", ""),
                "value": getattr(item, "value", str(item)),
            }
        )
    return serialized


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 Stage 11 LangGraph + Skills 实验。")
    parser.add_argument(
        "action",
        choices=("pause", "approve", "reject"),
        help="pause 首次运行并停在人工确认；approve/reject 从 checkpoint 恢复。",
    )
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--thread-id", default=DEFAULT_THREAD_ID)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--checkpoint-path", type=Path, default=DEFAULT_CHECKPOINT_PATH)
    parser.add_argument("--approval", default="批准，写入报告。")
    parser.add_argument("--rejection", default="拒绝，报告还需要人工复核。")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.action == "pause":
        run_pause(args)
    elif args.action == "approve":
        run_resume(args, args.approval)
    else:
        run_resume(args, args.rejection)


if __name__ == "__main__":
    main()
