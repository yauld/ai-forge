"""Skill Registry：扫描本地 Skills 目录并建立 metadata 索引。"""

from __future__ import annotations

from pathlib import Path

from .types import SkillMetadata


class SkillRegistry:
    """教学用最小 Registry。

    它只负责发现 Skill、解析 frontmatter，并提供稳定查询接口。
    更完整的目录校验、重复 name 检查和引用校验会留到后续阶段展开。
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
        tools = tuple(frontmatter.get("tools", []))

        if not name or not description:
            raise ValueError(f"{skill_file} must define name and description")

        return SkillMetadata(
            name=name,
            description=description,
            path=skill_file,
            skill_dir=skill_file.parent,
            tools=tools,
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

