"""Executor：根据已加载 Skill 编排脚本调用。"""

from __future__ import annotations

from typing import Any

from .script_runner import ScriptRunner
from .types import ExecutionResult, LoadedSkill, ScriptCallResult


class SkillExecutor:
    """教学版 Executor。

    它负责“这次要做什么”：选择脚本、组装参数、汇总结果。
    真正的脚本安全检查和 subprocess 执行交给 ScriptRunner。
    """

    def __init__(self, script_runner: ScriptRunner | None = None) -> None:
        self.script_runner = script_runner or ScriptRunner()

    def execute(
        self,
        loaded_skill: LoadedSkill,
        task: str,
        content: str,
        *,
        script_name: str | None = None,
        script_arguments: dict[str, Any] | None = None,
    ) -> ExecutionResult:
        selected_script = script_name or _default_script_name(loaded_skill)
        if selected_script is None:
            return ExecutionResult(
                status="no_script",
                summary=f"{loaded_skill.metadata.name} 没有声明可执行脚本。",
            )

        arguments = script_arguments if script_arguments is not None else {"content": content}
        script_call = self.script_runner.run(
            skill_dir=loaded_skill.metadata.skill_dir,
            declarations=loaded_skill.metadata.scripts,
            script_name=selected_script,
            arguments=arguments,
        )

        summary = (
            f"已加载 {loaded_skill.metadata.name}，并请求调用脚本 "
            f"{selected_script}，结果状态为 {script_call.status}。"
        )
        return ExecutionResult(
            status=_execution_status(script_call),
            summary=summary,
            script_calls=(script_call,),
        )


def _default_script_name(loaded_skill: LoadedSkill) -> str | None:
    if not loaded_skill.metadata.scripts:
        return None
    return loaded_skill.metadata.scripts[0].name


def _execution_status(script_call: ScriptCallResult) -> str:
    if script_call.status == "completed":
        return "completed"
    if script_call.status == "rejected":
        return "rejected"
    return "failed"
