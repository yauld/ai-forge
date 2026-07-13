"""Router：让模型根据 Skill metadata 选择 Skill。"""

from __future__ import annotations

import json
import re

from langchain_ollama import ChatOllama

from .types import RouteResult, SkillMetadata


def route_skill(task: str, skills: list[SkillMetadata], model_name: str) -> RouteResult:
    """只把 Skill metadata 交给模型，让模型判断是否触发某个 Skill。"""

    candidates = [
        {"name": skill.name, "description": skill.description}
        for skill in skills
    ]
    prompt = f"""你是一个 Skills runtime 的 Router。

请只根据 Skill 的 name 和 description，为用户任务选择一个最匹配的 Skill。
如果没有明确匹配项，返回 "none"。

约束：
- 不能假设你已经读取了完整 SKILL.md。
- 不能根据工具结果判断，因为此时工具还没有执行。
- 只能返回合法 JSON，不要输出 Markdown。

JSON 格式：
{{"skill": "<skill-name-or-none>", "reason": "<简短原因>"}}

可用 Skills：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

用户任务：
{task}
"""

    model = ChatOllama(model=model_name, temperature=0)
    response = model.invoke(prompt)
    raw_response = str(response.content)
    parsed = _parse_json_response(raw_response)

    chosen = str(parsed.get("skill", "none"))
    known_names = {skill.name for skill in skills}
    if chosen == "none":
        skill_name = None
    elif chosen in known_names:
        skill_name = chosen
    else:
        skill_name = None

    return RouteResult(
        skill_name=skill_name,
        reason=str(parsed.get("reason", "")),
        raw_response=raw_response,
    )


def _parse_json_response(text: str) -> dict[str, object]:
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("模型路由结果必须是 JSON object")
    return parsed
