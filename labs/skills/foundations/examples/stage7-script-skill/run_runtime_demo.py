"""运行阶段 7 的脚本型 Skills runtime demo。"""

from __future__ import annotations

import argparse
from pathlib import Path

from runtime.app import SkillRuntime


DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_TASK = "请从这份会议纪要中提取待办事项、负责人和截止时间。"
DEFAULT_CONTENT = """# 本周例会

- 张三负责整理竞品清单，下周三前完成
- 李四需要更新项目排期
- 已讨论预算问题，暂不处理
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="运行一个带受控 scripts 执行的教学用 Skills runtime。",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--task", default=DEFAULT_TASK)
    parser.add_argument("--content", default=DEFAULT_CONTENT)
    parser.add_argument(
        "--scenario",
        choices=("legal", "unknown-script", "invalid-args", "path-escape"),
        default="legal",
        help="选择要演示的脚本执行场景。",
    )
    parser.add_argument(
        "--model-fallback",
        action="store_true",
        help="规则没有明确命中时，启用 Ollama 路由兜底。",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    example_root = Path(__file__).parent

    runtime = SkillRuntime(
        skills_root=example_root / "skills",
        model_name=args.model,
        use_model_fallback=args.model_fallback,
    )

    script_name = None
    script_arguments = None
    if args.scenario == "unknown-script":
        script_name = "delete_everything"
    elif args.scenario == "invalid-args":
        script_arguments = {"content": 123}
    elif args.scenario == "path-escape":
        script_name = "escape_probe"

    trace = runtime.run(
        task=args.task,
        content=args.content,
        script_name=script_name,
        script_arguments=script_arguments,
    )
    print(trace.to_json())


if __name__ == "__main__":
    main()
