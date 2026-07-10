"""Executor：根据已加载 Skill 调用最小真实工具。"""

from __future__ import annotations

from tools.text_stats import count_text_stats

from .types import ExecutionResult, LoadedSkill, ToolCall


class SkillExecutor:
    """教学版 Executor。

    这里不会尝试解释完整 Skill 正文，只演示一个关键边界：
    Skill 声明可用工具，Executor 负责真正调用工具并收集结果。
    """

    def execute(self, loaded_skill: LoadedSkill, task: str, content: str) -> ExecutionResult:
        tool_calls: list[ToolCall] = []

        for tool_name in loaded_skill.metadata.tools:
            if tool_name == "text_stats":
                tool_calls.append(
                    ToolCall(
                        name=tool_name,
                        result=count_text_stats(content),
                    )
                )

        summary = (
            f"已加载 {loaded_skill.metadata.name}，并按 Skill 声明调用 "
            f"{len(tool_calls)} 个工具。"
        )
        return ExecutionResult(
            status="completed",
            summary=summary,
            tool_calls=tuple(tool_calls),
        )

