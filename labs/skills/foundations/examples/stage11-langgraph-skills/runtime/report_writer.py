"""报告写入工具：代表需要人工确认保护的外部副作用。"""

from __future__ import annotations

from pathlib import Path


def write_report(output_path: Path, content: str) -> dict[str, object]:
    """写入报告文件，并返回结构化结果。"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    return {
        "written": True,
        "path": str(output_path),
        "bytes": len(content.encode("utf-8")),
    }
