"""Runtime App：串联 Registry、Router、Loader、Executor 和 Trace。"""

from __future__ import annotations

from pathlib import Path

from .executor import SkillExecutor
from .loader import SkillLoader
from .registry import SkillRegistry
from .router import OllamaSkillRouter
from .trace import TraceRecorder


class SkillRuntime:
    """阶段 5 的最小 Skills runtime。

    它的价值不在于功能复杂，而在于把 Agent Host 中几个核心职责拆开：
    发现 Skill、选择 Skill、加载 Skill、执行工具、记录过程。
    """

    def __init__(self, skills_root: Path, model_name: str) -> None:
        self.registry = SkillRegistry(skills_root)
        self.router = OllamaSkillRouter(model_name)
        self.loader = SkillLoader()
        self.executor = SkillExecutor()

    def run(self, task: str, content: str) -> TraceRecorder:
        recorder = TraceRecorder(task)

        skills = self.registry.scan()
        recorder.trace.registry_skills = [skill.name for skill in skills]
        recorder.add_step(
            "registry.scan",
            "扫描 Skills 目录，读取每个 Skill 的 metadata。",
            skills=recorder.trace.registry_skills,
        )

        route = self.router.route(task, skills)
        recorder.trace.selected_skill = route.skill_name
        recorder.trace.route_reason = route.reason
        recorder.add_step(
            "router.route",
            "调用 Ollama，根据 name / description 选择 Skill。",
            selected_skill=route.skill_name,
            reason=route.reason,
            raw_response=route.raw_response,
        )

        if route.skill_name is None:
            recorder.trace.status = "no_matching_skill"
            recorder.add_step("runtime.stop", "没有匹配 Skill，停止加载和执行。")
            return recorder

        metadata = self.registry.get(route.skill_name)
        if metadata is None:
            recorder.trace.status = "unknown_skill"
            recorder.add_step("runtime.stop", "Router 返回了 Registry 中不存在的 Skill。")
            return recorder

        loaded_skill = self.loader.load(metadata)
        recorder.trace.loaded_files = [str(path) for path in loaded_skill.loaded_files]
        recorder.add_step(
            "loader.load",
            "读取命中 Skill 的 SKILL.md 正文。",
            loaded_files=recorder.trace.loaded_files,
            declared_tools=list(loaded_skill.metadata.tools),
        )

        result = self.executor.execute(loaded_skill, task=task, content=content)
        recorder.trace.status = result.status
        recorder.trace.tool_calls = [
            {"name": call.name, "result": call.result} for call in result.tool_calls
        ]
        recorder.add_step(
            "executor.execute",
            "根据 Skill 声明调用真实本地工具。",
            summary=result.summary,
            tool_calls=recorder.trace.tool_calls,
        )

        return recorder

