"""阶段 7：按故障层次运行 MCP 调试实验。

用法：

    uv run labs/mcp/foundations/examples/debug_client.py all
    uv run labs/mcp/foundations/examples/debug_client.py invalid-input
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Awaitable, Callable

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


HERE = Path(__file__).resolve().parent
# 使用脚本自身所在目录拼接绝对路径，避免 Host 从其他工作目录启动时找不到 Server。
DEBUG_SERVER = HERE / "debug_order_server.py"
BROKEN_STDOUT_SERVER = HERE / "broken_stdout_server.py"


async def connect(
    stack: AsyncExitStack,
    command: str,
    args: list[str],
) -> ClientSession:
    """启动 stdio Server，建立 Session，并完成 initialize。"""
    # command 和 args 故意由调用方传入：正常场景使用当前 Python 解释器，
    # 启动失败场景则可以替换成一个不存在的命令。
    parameters = StdioServerParameters(command=command, args=args, cwd=HERE)

    # stdio_client 负责启动 Server 子进程，并把它的 stdin/stdout
    # 包装成 Client 可读写的 MCP 消息流。
    read, write = await stack.enter_async_context(stdio_client(parameters))

    # ClientSession 在消息流之上提供 initialize、list_tools、call_tool 等方法。
    # Session 和子进程都交给同一个 AsyncExitStack，场景结束时统一清理。
    session = await stack.enter_async_context(ClientSession(read, write))

    # 能力发现和 Tool 调用必须发生在初始化握手之后。
    # 如果这里失败，排查范围仍在 Lifecycle，尚未进入具体 Tool。
    await session.initialize()
    return session


def print_result(result: object) -> None:
    """只打印判断故障层需要的最小结果。"""
    # 不直接打印完整 SDK 对象，避免大量元数据掩盖真正需要比较的字段：
    # isError 区分 Tool 执行成功与失败，structuredContent/content 保存具体结果。
    is_error = getattr(result, "isError", None)
    structured = getattr(result, "structuredContent", None)
    content = getattr(result, "content", None)
    print(f"isError: {is_error}")
    if structured is not None:
        print(f"structuredContent: {structured}")
    elif content:
        print(f"content: {content[0]}")


async def startup_failure() -> None:
    """进程层：Server 命令根本不存在。"""
    async with AsyncExitStack() as stack:
        # 进程无法创建时，不会产生 transport、initialize 或 tools/call。
        await connect(stack, "command-that-does-not-exist", [])


async def stdout_pollution() -> None:
    """Transport 层：普通文字混入 stdio 的 stdout。"""
    async with AsyncExitStack() as stack:
        # 这个反例 Server 会先向 stdout 写普通文字。
        # Client 会尝试把它解析为 JSON-RPC，从而留下 transport 层证据。
        await connect(stack, sys.executable, [str(BROKEN_STDOUT_SERVER)])


async def schema_mismatch() -> None:
    """执行层：输入符合 schema，但 Tool 实现违反了契约。"""
    async with AsyncExitStack() as stack:
        session = await connect(stack, sys.executable, [str(DEBUG_SERVER)])

        # 先保存 discovery 阶段真实拿到的 schema，再执行调用。
        # 这样可以证明 O-1001 是公开契约允许的输入，而不是 Client 传参错误。
        tools = await session.list_tools()
        tool = next(
            item for item in tools.tools if item.name == "get_order_with_contract_bug"
        )
        print(f"discovered inputSchema: {tool.inputSchema}")
        result = await session.call_tool(
            "get_order_with_contract_bug",
            {"order_id": "O-1001"},
        )
        print_result(result)


async def invalid_input() -> None:
    """调用边界：参数在进入 Tool 实现前被 schema 校验拒绝。"""
    async with AsyncExitStack() as stack:
        session = await connect(stack, sys.executable, [str(DEBUG_SERVER)])

        # schema 要求 O- 加四位数字；1001 会在 Tool 函数执行前被拒绝。
        result = await session.call_tool(
            "diagnose_order",
            {"order_id": "1001"},
        )
        print_result(result)


async def not_found() -> None:
    """业务层：调用成功，但合法的业务对象不存在。"""
    async with AsyncExitStack() as stack:
        session = await connect(stack, sys.executable, [str(DEBUG_SERVER)])

        # O-9999 格式合法，只是数据库中不存在。
        # 预期结果是 isError=False 和结构化的 not_found，而不是异常。
        result = await session.call_tool(
            "diagnose_order",
            {"order_id": "O-9999"},
        )
        print_result(result)


async def timeout() -> None:
    """Host 层：Host 不愿无限等待慢查询，主动设置超时。"""
    async with AsyncExitStack() as stack:
        session = await connect(stack, sys.executable, [str(DEBUG_SERVER)])

        # Server 模拟一秒查询，Host 只允许等待 0.2 秒。
        # deadline 属于 Host 策略；超时本身不能证明 Server 或数据库已经崩溃。
        async with asyncio.timeout(0.2):
            await session.call_tool(
                "diagnose_order",
                {"order_id": "O-1001", "delay_seconds": 1},
            )


async def database_failure() -> None:
    """执行层：Tool 已开始执行，但依赖的数据库失败。"""
    async with AsyncExitStack() as stack:
        session = await connect(stack, sys.executable, [str(DEBUG_SERVER)])

        # 参数能够通过 schema，异常由 Tool 实现主动制造，
        # 因而排查范围可以缩小到 execution 及其外部依赖。
        result = await session.call_tool(
            "simulate_database_failure",
            {"failure": "query"},
        )
        print_result(result)


# 场景名既是命令行参数，也是对应异步实验函数的路由表。
# 新增故障实验时，只需实现函数并在这里注册。
SCENARIOS: dict[str, Callable[[], Awaitable[None]]] = {
    "startup": startup_failure,
    "stdout": stdout_pollution,
    "schema-mismatch": schema_mismatch,
    "invalid-input": invalid_input,
    "not-found": not_found,
    "timeout": timeout,
    "database": database_failure,
}


async def run_scenario(name: str) -> None:
    """运行一个场景，并把异常类型作为诊断证据输出。"""
    print(f"\n=== {name} ===")
    try:
        await SCENARIOS[name]()
    except BaseException as exc:
        print(f"exception: {type(exc).__name__}")
        print(f"message: {exc}")
        # 异步上下文退出时可能把原始异常包装成 ExceptionGroup。
        # 继续打印叶子异常，避免真正的 TimeoutError 被外层类型遮住。
        pending = [exc]
        while pending:
            current = pending.pop()
            if isinstance(current, BaseExceptionGroup):
                pending.extend(current.exceptions)
            elif current is not exc:
                print(f"caused by: {type(current).__name__}: {current}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="运行 MCP 分层调试实验")
    parser.add_argument("scenario", choices=["all", *SCENARIOS], default="all")
    args = parser.parse_args()

    # dict 保留插入顺序，因此 all 会按照从进程、transport 到 execution
    # 的顺序运行，输出可以直接对应文章中的分层排查过程。
    names = SCENARIOS if args.scenario == "all" else [args.scenario]
    for name in names:
        print(f"name--->:{name}")
        await run_scenario(name)


if __name__ == "__main__":
    asyncio.run(main())
