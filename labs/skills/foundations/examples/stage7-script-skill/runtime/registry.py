"""Skill Registry：扫描本地 Skills 目录并建立 metadata 索引。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .types import ScriptDeclaration, SkillMetadata


class SkillRegistry:
    """教学用最小 Registry。

    它只负责发现 Skill、解析 frontmatter，并提供稳定查询接口。
    脚本路径和参数是否安全不在这里判断，留给 ScriptRunner。
    """

    def __init__(self, skills_root: Path) -> None:
        self.skills_root = skills_root
        self._skills: dict[str, SkillMetadata] = {}

    def scan(self) -> list[SkillMetadata]:
        self._skills.clear()
        for skill_file in sorted(self.skills_root.glob("*/SKILL.md")):
            metadata = self._parse_skill_metadata(skill_file)
            self._skills[metadata.name] = metadata
        return self.list_skills()

    def list_skills(self) -> list[SkillMetadata]:
        return list(self._skills.values())

    def get(self, name: str) -> SkillMetadata | None:
        return self._skills.get(name)

    def _parse_skill_metadata(self, skill_file: Path) -> SkillMetadata:
        frontmatter = _read_frontmatter(skill_file)
        name = frontmatter.get("name", "")
        description = frontmatter.get("description", "")
        script_items = frontmatter.get("scripts", [])

        if not name or not description:
            raise ValueError(f"{skill_file} must define name and description")
        if not isinstance(name, str) or not isinstance(description, str):
            raise ValueError(f"{skill_file} name and description must be strings")
        if not isinstance(script_items, list):
            raise ValueError(f"{skill_file} scripts must be a list")

        return SkillMetadata(
            name=name,
            description=description,
            path=skill_file,
            skill_dir=skill_file.parent,
            scripts=tuple(_parse_script_declaration(item, skill_file) for item in script_items),
        )


def _parse_script_declaration(item: str, skill_file: Path) -> ScriptDeclaration:
    try:
        raw = json.loads(item)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{skill_file} contains invalid script JSON: {item}") from exc

    if not isinstance(raw, dict):
        raise ValueError(f"{skill_file} script declaration must be a JSON object")

    name = raw.get("name")
    path = raw.get("path")
    input_schema = raw.get("input_schema", {})
    timeout_seconds = raw.get("timeout_seconds", 3)

    if not isinstance(name, str) or not isinstance(path, str):
        raise ValueError(f"{skill_file} script declaration requires string name and path")
    if not isinstance(input_schema, dict):
        raise ValueError(f"{skill_file} script input_schema must be an object")
    if not isinstance(timeout_seconds, (int, float)):
        raise ValueError(f"{skill_file} script timeout_seconds must be a number")

    return ScriptDeclaration(
        name=name,
        path=path,
        input_schema=input_schema,
        timeout_seconds=float(timeout_seconds),
    )


def _read_frontmatter(skill_file: Path) -> dict[str, str | list[str]]:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_file} does not start with YAML frontmatter")

    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{skill_file} does not close YAML frontmatter")

    # 教学版 parser 只覆盖本实验用到的 `key: value` 和简单列表。
    # 这样读者能把注意力放在 Registry 职责，而不是 YAML 解析细节。
    result: dict[str, str | list[str]] = {}
    current_list_key: str | None = None
    for raw_line in text[4:end].splitlines():
        line = raw_line.rstrip()
        if not line:
            continue

        stripped = line.strip()
        if stripped.startswith("- ") and current_list_key:
            values = result.setdefault(current_list_key, [])
            if isinstance(values, list):
                values.append(stripped[2:].strip())
            continue

        current_list_key = None
        if ":" not in stripped:
            continue

        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip().strip('"')
        if value:
            result[key] = value
        else:
            result[key] = []
            current_list_key = key

    return result
