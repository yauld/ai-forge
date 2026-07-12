"""Router：规则优先，模糊时可选 Ollama 判别。"""

from __future__ import annotations

import json
import re

from .types import RouteResult, SkillMetadata


class RuleFirstSkillRouter:
    """先用可解释规则命中，模糊时再交给本地模型。"""

    def __init__(self, model_name: str, use_model_fallback: bool = True) -> None:
        self.model_name = model_name
        self.use_model_fallback = use_model_fallback

    def route(self, task: str, skills: list[SkillMetadata]) -> RouteResult:
        rule_result = _route_by_rules(task, skills)
        if rule_result is not None:
            return rule_result

        if not self.use_model_fallback:
            return RouteResult(
                skill_name=None,
                reason="规则没有明确命中，且未启用模型兜底。",
                raw_response='{"skill": "none", "reason": "rule miss"}',
            )

        prompt = self._build_prompt(task, skills)
        model = _load_ollama(self.model_name)
        response = model.invoke(prompt)
        raw_response = str(response.content)
        parsed = _parse_json_response(raw_response)

        chosen = parsed.get("skill", "none")
        known_names = {skill.name for skill in skills}
        if chosen == "none":
            skill_name = None
        elif chosen in known_names:
            skill_name = chosen
        else:
            skill_name = None

        return RouteResult(
            skill_name=skill_name,
            reason=parsed.get("reason", ""),
            raw_response=raw_response,
        )

    def _build_prompt(self, task: str, skills: list[SkillMetadata]) -> str:
        candidates = [
            {"name": skill.name, "description": skill.description}
            for skill in skills
        ]
        return f"""你是一个 Skills runtime 的 Router。

请只根据 Skill 的 name 和 description，为用户任务选择一个最匹配的 Skill。
如果没有明确匹配项，返回 "none"。

只返回合法 JSON：
{{"skill": "<skill-name-or-none>", "reason": "<简短原因>"}}

可用 Skills：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

用户任务：
{task}
"""


def _route_by_rules(task: str, skills: list[SkillMetadata]) -> RouteResult | None:
    normalized = task.lower()
    known_names = {skill.name for skill in skills}

    task_keywords = ("会议纪要", "例会", "待办", "负责人", "截止时间", "任务提取")
    if "meeting-task-extractor" in known_names and any(
        keyword in normalized for keyword in task_keywords
    ):
        return RouteResult(
            skill_name="meeting-task-extractor",
            reason="规则命中会议纪要/待办提取相关关键词。",
            raw_response='{"skill": "meeting-task-extractor", "source": "rules"}',
        )

    weekly_keywords = ("周报", "本周完成", "下周计划")
    if "writing-weekly-report" in known_names and any(
        keyword in normalized for keyword in weekly_keywords
    ):
        return RouteResult(
            skill_name="writing-weekly-report",
            reason="规则命中周报写作相关关键词。",
            raw_response='{"skill": "writing-weekly-report", "source": "rules"}',
        )

    return None


def _load_ollama(model_name: str):
    from langchain_ollama import ChatOllama

    return ChatOllama(model=model_name, temperature=0)


def _parse_json_response(text: str) -> dict[str, str]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))
