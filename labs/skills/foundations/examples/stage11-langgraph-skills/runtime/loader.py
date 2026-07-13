"""Loader：根据路由结果读取完整 Skill 正文。"""

from __future__ import annotations

from .types import LoadedSkill, SkillMetadata


class SkillLoader:
    """只负责读取文件内容，不参与路由和执行。"""

    def load(self, metadata: SkillMetadata) -> LoadedSkill:
        text = metadata.path.read_text(encoding="utf-8")
        body_start = text.find("\n---", 4)
        if body_start == -1:
            raise ValueError(f"{metadata.path} does not close YAML frontmatter")

        return LoadedSkill(
            metadata=metadata,
            body=text[body_start + len("\n---") :].strip(),
            loaded_files=(metadata.path,),
        )
