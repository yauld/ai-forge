"""Skill Registry：扫描本地 Skills 目录并建立 metadata 索引。"""

from __future__ import annotations

from pathlib import Path

from .types import SkillMetadata


class SkillRegistry:
    """教学用 Registry，职责与阶段 5 保持一致。"""

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
        stripped = raw_line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        result[key.strip()] = value.strip().strip('"')

    return result
