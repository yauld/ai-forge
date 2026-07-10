"""Router：使用 Ollama 根据 Skill metadata 选择 Skill。"""

from __future__ import annotations

import json
import re

from langchain_ollama import ChatOllama

from .types import RouteResult, SkillMetadata


class OllamaSkillRouter:
    """只根据 name / description 做路由。"""

    def __init__(self, model_name: str) -> None:
        self.model = ChatOllama(model=model_name, temperature=0)

    def route(self, task: str, skills: list[SkillMetadata]) -> RouteResult:
        prompt = self._build_prompt(task, skills)
        response = self.model.invoke(prompt)
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


def _parse_json_response(text: str) -> dict[str, str]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))
