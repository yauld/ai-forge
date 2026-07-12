"""从会议纪要 Markdown 中提取简单待办项。

脚本从 stdin 读取 JSON：{"content": "..."}。
脚本向 stdout 输出 JSON object，供 ScriptRunner 解析。
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any


SKIP_KEYWORDS = ("暂不处理", "无需处理", "不处理", "已讨论")
ACTION_WORDS = ("负责", "需要", "需", "要")


def main() -> None:
    payload = json.loads(sys.stdin.read() or "{}")  # {'content': '# 本周例会\\n\\n- 张三负责整理竞品清单，下周三前完成\\n- 李四需要更新项目排期\\n- 已讨论预算问题，暂不处理\\n'}
    content = payload.get("content", "")
    tasks = extract_tasks(content)
    print(json.dumps({"tasks": tasks, "task_count": len(tasks)}, ensure_ascii=False))


def extract_tasks(content: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for line in content.splitlines():
        item = _parse_line(line)
        if item:
            tasks.append(item)
    return tasks


def _parse_line(line: str) -> dict[str, Any] | None:
    text = line.strip().lstrip("-*0123456789.、 ").strip()
    if not text or any(keyword in text for keyword in SKIP_KEYWORDS):
        return None

    pattern = r"^(?P<owner>[\u4e00-\u9fa5A-Za-z0-9_]{2,12}?)(?P<action>负责|需要|需|要)(?P<body>.+)$"
    match = re.match(pattern, text)
    if not match:
        return None

    body = match.group("body").strip()
    deadline = _extract_deadline(body)
    task = _clean_task(body, deadline)
    if not task:
        return None

    return {
        "owner": match.group("owner"),
        "task": task,
        "deadline": deadline,
    }


def _extract_deadline(text: str) -> str | None:
    patterns = [
        r"(今天|明天|后天|本周[一二三四五六日天]?|下周[一二三四五六日天]?|周[一二三四五六日天])",
        r"(\d{1,2}月\d{1,2}日)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None


def _clean_task(text: str, deadline: str | None) -> str:
    task = text
    if deadline:
        task = task.split(deadline, 1)[0]
    task = re.split(r"[，,。；;]", task, maxsplit=1)[0]
    task = re.sub(r"(前)?完成$", "", task)
    return task.strip()


if __name__ == "__main__":
    main()
