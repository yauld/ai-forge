"""运行阶段 5 的教学用 Skills runtime demo。"""

from __future__ import annotations

import argparse
from pathlib import Path

from runtime.app import SkillRuntime


DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_TASK = "请审查这份 Skills 学习路线图，看看阶段顺序、边界和产出物是否合理。"
DEFAULT_CONTENT = """# Skills 学习路线图

阶段 1：理解 Skills 在 Agent 架构中的定位。
阶段 2：编写最小 SKILL.md，并验证 name 和 description 能否支持路由。
阶段 3：区分 Action Skill 和 Reference Skill。
阶段 5：设计一个教学用 runtime，观察扫描、路由、加载、执行和 trace 如何协作。
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行一个模块化的教学用 Skills runtime。",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--content", default=DEFAULT_CONTENT)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    example_root = Path(__file__).parent

    runtime = SkillRuntime(
        skills_root=example_root / "skills",
        model_name=args.model,
    )
    trace = runtime.run(task=args.task, content=args.content)
    print(trace.to_json())


if __name__ == "__main__":
    main()

