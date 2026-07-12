"""阶段 10：用真实 Ollama 模型把 Skill 和 MCP Tool 串起来。

这个文件故意保持线性流程，方便观察正常协作链路：

1. Host 扫描 `skills/*/SKILL.md`，只读取 name / description。
2. Ollama 根据用户请求选择 Skill。
3. Host 加载完整 `SKILL.md`。
4. Host 连接 MCP Server，发现 `get_order` Tool。
5. Ollama 根据 Skill 正文提出 Tool 调用。
6. Host 执行 MCP Tool，再把结果交回 Ollama 生成最终回答。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_ollama import ChatOllama
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


HERE = Path(__file__).resolve().parent
SKILLS_ROOT = HERE / "skills"
SERVER = HERE / "mcp_server.py"
DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_TASK = "帮我查一下订单 O-1001 的状态、商品和金额，并用一句话告诉我结果。"


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    path: Path


def parse_frontmatter(markdown: str) -> dict[str, str]:
    """解析本实验需要的最小 frontmatter：name 和 description。"""
    match = re.match(r"^---\n(?P<body>.*?)\n---\n", markdown, flags=re.DOTALL)
    if not match:
        raise ValueError("SKILL.md 缺少 frontmatter")

    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def scan_skills(skills_root: Path) -> list[SkillMetadata]:
    """只扫描 Skill metadata，不把完整正文提前放进模型上下文。"""
    skills: list[SkillMetadata] = []
    for skill_file in sorted(skills_root.glob("*/SKILL.md")):
        content = skill_file.read_text(encoding="utf-8")
        frontmatter = parse_frontmatter(content)
        skills.append(
            SkillMetadata(
                name=frontmatter["name"],
                description=frontmatter["description"],
                path=skill_file,
            )
        )
    return skills


def parse_json_response(text: str) -> dict[str, Any]:
    """兼容模型在 JSON 外包了一点解释文本的情况。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def route_skill(model: ChatOllama, task: str, skills: list[SkillMetadata]) -> str:
    """让模型只根据 name / description 选择 Skill。"""
    candidates = [
        {"name": skill.name, "description": skill.description}
        for skill in skills
    ]
    prompt = f"""你是一个 Skills runtime 的 Router。

请只根据 Skill 的 name 和 description，为用户任务选择一个最匹配的 Skill。
如果没有明确匹配项，返回 "none"。

只返回合法 JSON：
{{"skill": "<skill-name-or-none>", "reason": "<简短原因>"}}

可用 Skills：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

用户任务：
{task}
"""
    response = model.invoke(prompt)
    parsed = parse_json_response(str(response.content))
    print("route_result:", json.dumps(parsed, ensure_ascii=False))
    return str(parsed.get("skill", "none"))


async def connect_mcp(stack: AsyncExitStack) -> ClientSession:
    """启动 stdio MCP Server，并完成 initialize。"""
    parameters = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER)],
        cwd=HERE,
    )
    read, write = await stack.enter_async_context(stdio_client(parameters))
    session = await stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


async def run_demo(task: str, model_name: str) -> None:
    """运行一次正常的 Skill + MCP 协作流程。"""
    model = ChatOllama(model=model_name, temperature=0) # type: ignore

    # 第 1 步：Host 扫描 Skill metadata。
    # 这里只读取 name / description，用来模拟 Skills 的“发现阶段”。
    # 完整 SKILL.md 正文会等到 Skill 被选中后再加载。
    skills = scan_skills(SKILLS_ROOT)
    print(
        "discovered_skills:",
        json.dumps(
            [{"name": skill.name, "description": skill.description} for skill in skills],
            ensure_ascii=False,
        ),
    )

    # 第 2 步：模型根据用户任务选择 Skill。
    # 这一步只看 metadata，不看 Skill 正文，也不接触 MCP 工具。
    selected_skill_name = route_skill(model, task, skills)
    selected_skill = next(
        (skill for skill in skills if skill.name == selected_skill_name),
        None,
    )
    if selected_skill is None:
        raise RuntimeError(f"没有匹配到可用 Skill：{selected_skill_name}")

    # 第 3 步：Host 加载被选中的完整 SKILL.md。
    # 从这里开始，Skill 正文才进入模型上下文，用来指导后续工具调用。
    skill_text = selected_skill.path.read_text(encoding="utf-8")
    print("loaded_skill:", selected_skill.name)

    async with AsyncExitStack() as stack:
        # 第 4 步：Host 启动并连接 MCP Server。
        # MCP Server 只暴露工具能力；它不知道当前命中了哪个 Skill。
        session = await connect_mcp(stack)
        listed_tools = await session.list_tools()
        available_tool_names = [tool.name for tool in listed_tools.tools]
        print("mcp_tools:", json.dumps(available_tool_names, ensure_ascii=False))

        # 本实验只有一个 Skill 和一个 Tool。这里仍然从 MCP Server 的真实 schema
        # 生成模型可见工具定义，避免为模型另写一套平行参数格式。
        model_tools = [
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            }
            for tool in listed_tools.tools
            if tool.name == "get_order"
        ]
        tool_enabled_model = model.bind_tools(model_tools)

        # 第 5 步：把 Skill 正文、用户任务和 MCP Tool schema 一起交给模型。
        # 模型此时不直接执行工具，只返回它想调用的 Tool 名称和参数。
        messages = [
            SystemMessage(
                content=(
                    "你正在作为 Host 中的执行模型工作。请严格按照下面的 Skill "
                    "说明完成任务。需要查询订单时，使用已提供的 MCP 工具。\n\n"
                    f"{skill_text}"
                )
            ),
            HumanMessage(content=task),
        ]

        first_response = await tool_enabled_model.ainvoke(messages)
        messages.append(first_response)
        print(
            "model_tool_calls:",
            json.dumps(first_response.tool_calls, ensure_ascii=False),
        )

        if not first_response.tool_calls:
            raise RuntimeError("模型没有提出 MCP Tool 调用，请检查 Ollama 工具调用能力。")

        for tool_call in first_response.tool_calls:
            # 第 6 步：Host 按模型提出的 Tool Call 调用 MCP Server。
            # 真正的外部动作发生在这里，而不是发生在 Skill 或模型内部。
            tool_name = tool_call["name"]
            arguments = tool_call["args"]
            result = await session.call_tool(tool_name, arguments)
            tool_result = result.structuredContent or {"content": result.content}
            print(
                "mcp_tool_result:",
                json.dumps(
                    {"tool": tool_name, "result": tool_result},
                    ensure_ascii=False,
                ),
            )
            messages.append(
                ToolMessage(
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=tool_call["id"],
                )
            )

        # 第 7 步：Host 把 MCP Tool 结果作为 ToolMessage 交回模型。
        # 模型基于真实工具结果生成最终自然语言回复。
        final_response = await tool_enabled_model.ainvoke(messages)
        print("final_answer:", final_response.content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行最小 Skills + MCP 正常协作实验。")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--task", default=DEFAULT_TASK)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    asyncio.run(run_demo(task=args.task, model_name=args.model))


if __name__ == "__main__":
    main()
