"""故意污染 stdout，观察 Client 如何处理非法 MCP 消息。

这个脚本不是正确写法，而是一个反例实验：
stdio transport 会把 Server 子进程的 stdout 当作 MCP 协议通道。
因此，Server 写入 stdout 的每一行都应该是合法 JSON-RPC 消息。
"""

from shop_order_primitives_server import ensure_database, mcp


def main() -> None:
    ensure_database()

    # 这行普通日志会写入 Server 子进程自己的 stdout。
    # 但在 stdio 模式下，Client 正在从这个 stdout 读取 MCP 消息。
    # 所以 Client 会尝试把这句中文当成 JSON-RPC 解析，从而报告解析错误。
    #
    # 正确做法是把普通日志写入 stderr，例如：
    # print("Server 已启动", file=sys.stderr)
    print("这是一条不应该出现在 stdout 的普通日志", flush=True)

    # 这里仍然启动 stdio Server，用来观察 stdout 被污染后的表现。
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
