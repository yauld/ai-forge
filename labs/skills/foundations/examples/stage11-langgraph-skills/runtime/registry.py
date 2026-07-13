"""Skill Registry：只负责扫描 Skill metadata。"""

from __future__ import annotations

from pathlib import Path

from .types import SkillMetadata


class SkillRegistry:
    """扫描 `skills/*/SKILL.md`，但不提前加载完整正文。"""

    def __init__(self, skills_root: Path) -> None:
        self.skills_root = skills_root
        self._skills: dict[str, SkillMetadata] = {}

    def scan(self) -> list[SkillMetadata]:
        self._skills.clear()
        for skill_file in sorted(self.skills_root.glob("*/SKILL.md")):
            metadata = _parse_skill_metadata(skill_file)
            self._skills[metadata.name] = metadata
        return self.list_skills()

    def get(self, name: str) -> SkillMetadata | None:
        return self._skills.get(name)

    def list_skills(self) -> list[SkillMetadata]:
        return list(self._skills.values())


def _parse_skill_metadata(skill_file: Path) -> SkillMetadata:
    frontmatter = _read_frontmatter(skill_file)
    name = frontmatter.get("name", "")
    description = frontmatter.get("description", "")

    if not name or not description:
        raise ValueError(f"{skill_file} must define name and description")

    return SkillMetadata(
        name=name,
        description=description,
        path=skill_file,
        skill_dir=skill_file.parent,
    )


def _read_frontmatter(skill_file: Path) -> dict[str, str]:
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_file} does not start with YAML frontmatter")

    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{skill_file} does not close YAML frontmatter")

    result: dict[str, str] = {}
    for raw_line in text[4:end].splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip().strip('"')
    return result
