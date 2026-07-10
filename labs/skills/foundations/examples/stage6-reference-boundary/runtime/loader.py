"""Loader：命中 Skill 后读取 SKILL.md 正文。"""

from __future__ import annotations

from .types import LoadedSkill, SkillMetadata


class SkillLoader:
    """只负责加载 Skill 正文，不读取 references。"""

    def load(self, metadata: SkillMetadata) -> LoadedSkill:
        text = metadata.path.read_text(encoding="utf-8")
        body_start = text.find("\n---", 4)
        if body_start == -1:
            raise ValueError(f"{metadata.path} does not close YAML frontmatter")

        body = text[body_start + len("\n---") :].strip()
        return LoadedSkill(
            metadata=metadata,
            body=body,
            loaded_files=(metadata.path,),
        )
