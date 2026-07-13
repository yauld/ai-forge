"""阶段 11 实验共享的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, TypedDict
import operator


@dataclass(frozen=True)
class SkillMetadata:
    """Registry 暴露给 Router 的最小 Skill 索引。"""

    name: str
    description: str
    path: Path
    skill_dir: Path


@dataclass(frozen=True)
class LoadedSkill:
    """Loader 命中后读取到的完整 Skill 内容。"""

    metadata: SkillMetadata
    body: str
    loaded_files: tuple[Path, ...]


@dataclass(frozen=True)
class RouteResult:
    """Router 对一次用户请求的模型判断结果。"""

    skill_name: str | None
    reason: str
    raw_response: str


class SkillGraphState(TypedDict, total=False):
    """LangGraph 在各节点之间传递的业务状态。

    这个 State 故意保留 Skills runtime 的中间结果，方便观察：
    路由看了哪些 metadata，加载了哪个正文，MCP 返回了什么，
    以及人工确认前后的状态如何被 checkpoint 保存。
    """

    task: str
    model_name: str
    skill_candidates: list[dict[str, str]]
    selected_skill: str
    route_reason: str
    route_raw_response: str
    skill_text: str
    loaded_files: list[str]
    mcp_tools: list[dict[str, Any]]
    tool_call_plan: dict[str, Any]
    tool_call_raw_response: str
    order_id: str
    tool_name: str
    tool_result: dict[str, Any]
    report_draft: str
    approval: str
    output_path: str
    write_result: dict[str, Any]
    final_answer: str
    trace: Annotated[list[dict[str, Any]], operator.add]
