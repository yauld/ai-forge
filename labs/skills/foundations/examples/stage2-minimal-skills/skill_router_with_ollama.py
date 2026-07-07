"""使用本地 Ollama 模型运行一个迷你 Skill Agent。

脚本启动后进入交互模式。用户连续输入任务，Agent 根据
`name` / `description` 路由到合适的 Skill，并在命中后加载对应
`SKILL.md` 正文预览。
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path

from langchain_ollama import ChatOllama


DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_BODY_PREVIEW_LINES = 14

# 让实验保持自包含：脚本与 3 个示例 Skill 目录放在同一级。
# 因此当前文件所在目录就是本实验的“Skill 库”，扫描时不需要依赖仓库其他路径。
SKILLS_ROOT = Path(__file__).parent


@dataclass
class SkillMetadata:
    """发现阶段只需要 metadata，不需要完整正文。"""

    name: str
    description: str
    path: Path


@dataclass
class RouteResult:
    """一次路由的结构化结果。"""

    skill: str
    reason: str


def parse_frontmatter(skill_file: Path) -> SkillMetadata:
    """只读取发现阶段需要的 frontmatter 字段。"""
    text = skill_file.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{skill_file} does not start with YAML frontmatter")

    end = text.find("\n---", 4)
    if end == -1:
        raise ValueError(f"{skill_file} does not close YAML frontmatter")

    # 这里故意只处理示例中使用的 `key: value` 形式。
    # 阶段二关注的是“metadata 能否支持发现”，不是 YAML 解析器的完备性；
    # 后面做 Skill Registry 时，再切换到正式 YAML parser 会更合适。
    frontmatter = text[4:end].strip().splitlines()
    metadata: dict[str, str] = {}
    for line in frontmatter:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')

    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not name or not description:
        raise ValueError(f"{skill_file} must define name and description")

    return SkillMetadata(name=name, description=description, path=skill_file)


def load_skill_metadata() -> list[SkillMetadata]:
    """扫描直接子目录，只读取每个 SKILL.md 的 frontmatter。"""
    skills: list[SkillMetadata] = []
    # `*/SKILL.md` 对应最小 Skill 目录结构：
    # 每个 Skill 一个独立目录，目录顶层放一个 `SKILL.md`。
    # 这个阶段不递归扫描 references、scripts 或 assets，避免提前引入后续阶段的复杂度。
    for skill_file in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
        skills.append(parse_frontmatter(skill_file))
    return skills


def build_router_prompt(request: str, skills: list[SkillMetadata]) -> str:
    # 路由提示词只提供发现阶段真实可用的信息：`name` 和 `description`。
    # 如果模型能在这里选对 Skill，说明 description 已经包含足够的触发场景、
    # 输入形态和边界信号；如果选错，优先应该改 description，而不是改正文。
    candidates = [
        {"name": skill.name, "description": skill.description} for skill in skills
    ]
    return f"""你是一个 Skill 路由器，需要根据用户请求选择一个 Skill。

只有当某个 Skill 的 description 明确匹配用户请求时，才选择它。
如果没有任何 Skill 匹配，返回 "none"。

只返回合法 JSON，格式如下：
{{"skill": "<skill-name-or-none>", "reason": "<简短原因>"}}

可用 Skills：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

用户请求：
{request}
"""


def parse_json_response(text: str) -> dict[str, str]:
    """从模型响应中提取第一个 JSON 对象。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 本地模型有时会在 JSON 外面包一两句解释。
        # 教学实验里直接抽取第一个 JSON 对象，可以让实验继续跑下去；
        # 如果连 JSON 对象都找不到，就抛出异常，提醒读者路由输出已经失控。
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def route_request(
    request: str,
    skills: list[SkillMetadata],
    model: ChatOllama,
) -> RouteResult:
    prompt = build_router_prompt(request, skills)
    response = model.invoke(prompt)
    result = parse_json_response(str(response.content))

    # 模型只能从已发现的 Skill 名称里选择。
    # 如果它返回一个不存在的 Skill 名称，说明模型产生了幻觉；这里把结果降级为 `none`，
    # 防止后续加载一个并不存在的目录或文件。
    chosen_skill = result.get("skill", "none")
    known_names = {skill.name for skill in skills}
    if chosen_skill not in known_names and chosen_skill != "none":
        return RouteResult(
            skill="none",
            reason=f"模型返回了不存在的 Skill：{chosen_skill}",
        )

    return RouteResult(
        skill=chosen_skill,
        reason=result.get("reason", ""),
    )


def body_lines(skill: SkillMetadata) -> list[str]:
    """路由命中后，再读取完整正文。"""
    text = skill.path.read_text(encoding="utf-8")
    body_start = text.find("\n---", 4)
    body = text[body_start + len("\n---") :].strip()
    return body.splitlines()


def body_preview(skill: SkillMetadata, limit: int) -> list[str]:
    """读取正文前几行，作为“已加载 Skill”的可观察证据。"""
    return body_lines(skill)[:limit]


def print_agent_turn(
    request: str,
    skills: list[SkillMetadata],
    skills_by_name: dict[str, SkillMetadata],
    model: ChatOllama,
) -> RouteResult:
    """完成一次迷你 Agent 回合：接收任务、路由、按需加载 Skill。"""
    result = route_request(request, skills, model)
    print(f"用户任务：{request}")
    print(f"路由结果：{result.skill}")
    print(f"路由原因：{result.reason}")

    if result.skill == "none":
        print("加载结果：没有匹配 Skill，保持未加载状态。")
        return result

    skill = skills_by_name[result.skill]
    print(f"加载结果：已加载 {skill.name} 的正文 preview")
    print()
    for line in body_preview(skill, DEFAULT_BODY_PREVIEW_LINES):
        print(f"  {line}")
    return result


def run_interactive_agent(
    skills: list[SkillMetadata],
    skills_by_name: dict[str, SkillMetadata],
    model: ChatOllama,
) -> None:
    """进入交互模式，让读者像使用 Agent 一样连续输入任务。"""
    print("Mini Skill Agent 已启动。")
    print("直接输入任务，Agent 会先路由 Skill，再加载正文 preview。")
    print("按 Ctrl+C 或 Ctrl+D 结束。\n")

    while True:
        try:
            request = input("task> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n已退出。")
            return

        if not request:
            continue

        print_agent_turn(request, skills, skills_by_name, model)
        print()


def build_parser() -> argparse.ArgumentParser:
    """构建命令行入口：只保留模型选择参数，其他操作都在交互中完成。"""
    parser = argparse.ArgumentParser(
        description="启动一个使用本地 Ollama 模型的迷你 Skill Agent。",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # 这是本实验最重要的两阶段数据流：
    # 1. 先只加载 metadata，让模型根据 description 做路由；
    # 2. 只有路由命中后，才读取对应 Skill 的正文 preview。
    # 这样可以观察“发现”和“加载”两个动作的边界，而不是一开始就把所有正文塞给模型。
    skills = load_skill_metadata()
    skills_by_name = {skill.name: skill for skill in skills}

    model = ChatOllama(model=args.model, temperature=0)
    run_interactive_agent(skills, skills_by_name, model)


if __name__ == "__main__":
    main()
