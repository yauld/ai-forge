"""检查 AI Forge 的公共入口、相对链接和目录约定。"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
ENTRY_FILES = [
    ROOT / "README.md",
    ROOT / "labs" / "langchain" / "foundations" / "README.md",
    ROOT / "labs" / "langgraph" / "foundations" / "README.md",
    ROOT / "labs" / "mcp" / "foundations" / "README.md",
    ROOT / "labs" / "mcp" / "foundations" / "examples" / "README.md",
    ROOT / "labs" / "rag" / "foundations" / "README.md",
]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*]\((?:<([^>]+)>|([^) \t]+))")


def relative_link_errors(path: Path) -> list[str]:
    errors: list[str] = []
    content = path.read_text(encoding="utf-8")

    for match in MARKDOWN_LINK.finditer(content):
        target = unquote(match.group(1) or match.group(2))
        if (
            not target
            or target.startswith(("#", "http://", "https://", "mailto:"))
        ):
            continue

        target_path = (path.parent / target.split("#", 1)[0]).resolve()
        if not target_path.exists():
            errors.append(f"{path.relative_to(ROOT)} -> {target}")

    return errors


def main() -> int:
    errors: list[str] = []

    if (ROOT / "examples").exists():
        errors.append("根目录不应存在 examples/；示例应跟随所属专题")

    for path in ENTRY_FILES:
        if not path.exists():
            errors.append(f"公共入口不存在：{path.relative_to(ROOT)}")
            continue
        errors.extend(relative_link_errors(path))

    if errors:
        print("仓库检查失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"仓库检查通过：已检查 {len(ENTRY_FILES)} 个公共入口。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
