"""一个足够小但真实可调用的文本统计工具。"""

from __future__ import annotations


def count_text_stats(text: str) -> dict[str, int]:
    """统计输入文本规模，作为 Executor 调用工具的可观察证据。"""
    paragraphs = [part for part in text.split("\n\n") if part.strip()]
    non_empty_lines = [line for line in text.splitlines() if line.strip()]
    return {
        "characters": len(text),
        "non_empty_lines": len(non_empty_lines),
        "paragraphs": len(paragraphs),
    }

