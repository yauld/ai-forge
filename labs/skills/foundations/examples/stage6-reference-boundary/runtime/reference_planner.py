"""ReferencePlanner：使用 Ollama 决定本次需要读取哪个 reference。"""

from __future__ import annotations

import json
import re

from langchain_ollama import ChatOllama

from .types import LoadedSkill, ReferencePlan


class OllamaReferencePlanner:
    """把自然语言任务转换成 read_reference(file) 请求。"""

    def __init__(self, model_name: str) -> None:
        self.model = ChatOllama(model=model_name, temperature=0)

    def plan(self, task: str, loaded_skill: LoadedSkill) -> ReferencePlan:
        prompt = self._build_prompt(task, loaded_skill)
        response = self.model.invoke(prompt)
        raw_response = str(response.content)
        parsed = _parse_json_response(raw_response)

        return ReferencePlan(
            file=parsed.get("file", "weekly_report_template.md"),
            reason=parsed.get("reason", ""),
            raw_response=raw_response,
        )

    def _build_prompt(self, task: str, loaded_skill: LoadedSkill) -> str:
        return f"""你是一个 Skills runtime 的 ReferencePlanner。

当前已经命中的 Skill：
{loaded_skill.metadata.name}

Skill 正文：
{loaded_skill.body}

请根据用户任务判断本次应该读取哪个 reference 文件。
只返回合法 JSON：
{{"file": "<reference-file>", "reason": "<简短原因>"}}

规则：
- 如果用户明确指定了文件路径，原样放入 file 字段。
- 如果用户要求读取整个 references 目录，file 返回 "."。
- 如果用户没有指定 reference，file 返回 "weekly_report_template.md"。
- 你只负责表达“想读什么”，不要判断路径是否安全。

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
