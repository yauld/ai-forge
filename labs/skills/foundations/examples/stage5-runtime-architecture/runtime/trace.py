"""Trace：把 runtime 每一步转成可观察记录。"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .types import RuntimeTrace


class TraceRecorder:
    """记录一次 runtime 调用，方便读者观察模块协作路径。"""

    def __init__(self, task: str) -> None:
        self.trace = RuntimeTrace(task=task)

    def add_step(self, stage: str, message: str, **data: Any) -> None:
        self.trace.steps.append(
            {
                "stage": stage,
                "message": message,
                "data": _json_safe(data),
            }
        )

    def to_json(self) -> str:
        return json.dumps(_json_safe(asdict(self.trace)), ensure_ascii=False, indent=2)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value

