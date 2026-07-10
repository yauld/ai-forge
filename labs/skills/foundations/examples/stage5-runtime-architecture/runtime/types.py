"""Runtime 各模块共享的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SkillMetadata:
    """Registry 暴露给 Router 的最小 Skill 索引。"""

    name: str
    description: str
    path: Path
    skill_dir: Path
    tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteResult:
    """Router 对一次用户请求的选择结果。"""

    skill_name: str | None
    reason: str
    raw_response: str


@dataclass(frozen=True)
class LoadedSkill:
    """Loader 命中后读取到的 Skill 正文。"""

    metadata: SkillMetadata
    body: str
    loaded_files: tuple[Path, ...]


@dataclass(frozen=True)
class ToolCall:
    """Executor 调用一个工具后的记录。"""

    name: str
    result: dict[str, Any]


@dataclass(frozen=True)
class ExecutionResult:
    """Executor 完成 Skill 执行后的结果。"""

    status: str
    summary: str
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass
class RuntimeTrace:
    """记录一次请求经过 runtime 的完整路径。"""

    task: str
    registry_skills: list[str] = field(default_factory=list)
    selected_skill: str | None = None
    route_reason: str = ""
    loaded_files: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    status: str = "started"
    steps: list[dict[str, Any]] = field(default_factory=list)

