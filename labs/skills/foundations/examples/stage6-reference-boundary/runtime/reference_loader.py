"""ReferenceLoader：对比不安全读取和安全读取。"""

from __future__ import annotations

from pathlib import Path

from .types import LoadedSkill, ReferenceReadResult


class ReferenceLoader:
    """读取当前 Skill 的 references，并负责路径边界检查。"""

    def unsafe_read(self, loaded_skill: LoadedSkill, file: str) -> ReferenceReadResult:
        """危险实现：直接把模型给出的路径拼到 references 根目录后面。"""
        references_root = loaded_skill.metadata.skill_dir / "references"
        path = references_root / file
        return _read_text(path)

    def safe_read(self, loaded_skill: LoadedSkill, file: str) -> ReferenceReadResult:
        """安全实现：解析真实路径后，确认它仍在当前 references 根目录内。"""
        references_root = (loaded_skill.metadata.skill_dir / "references").resolve()
        requested_path = (references_root / file).resolve()

        if not requested_path.is_relative_to(references_root):
            return ReferenceReadResult(
                status="blocked",
                path=str(requested_path),
                error="reference path escapes current skill references root",
            )

        if requested_path.is_dir():
            return ReferenceReadResult(
                status="blocked",
                path=str(requested_path),
                error="reference path must point to a file, not a directory",
            )

        return _read_text(requested_path)


def _read_text(path: Path) -> ReferenceReadResult:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - 实验 trace 需要保留具体失败原因。
        return ReferenceReadResult(
            status="blocked",
            path=str(path),
            error=f"{type(exc).__name__}: {exc}",
        )

    return ReferenceReadResult(
        status="allowed",
        path=str(path),
        preview=_preview(text),
    )


def _preview(text: str, max_chars: int = 120) -> str:
    compact = " ".join(line.strip() for line in text.splitlines() if line.strip())
    if len(compact) <= max_chars:
        return compact
    return f"{compact[:max_chars]}..."
