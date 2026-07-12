"""Loader：根据路由结果读取命中的 Skill 正文。"""

from __future__ import annotations

from .types import LoadedSkill, SkillMetadata


class SkillLoader:
    """只负责加载文件内容，不参与路由判断。"""

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

