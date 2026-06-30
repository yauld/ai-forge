"""用同一组订单能力运行 stdio 或 Streamable HTTP。"""

from __future__ import annotations

import argparse

# 直接复用已经注册好 Tool、Resource 和 Prompt 的 MCP 实例。
# 这样切换 transport 时，变化的只有消息传输方式，业务能力保持完全一致。
from shop_order_primitives_server import ensure_database, mcp


def parse_args() -> argparse.Namespace:
    """读取 transport 选项，便于用同一入口对比两种运行方式。"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP 消息的传输方式（默认：stdio）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # 在 Server 接受请求前准备好示例数据；这一步与 transport 无关。
    ensure_database()

    # stdio 通过当前进程的标准输入输出通信；
    # streamable-http 则启动独立 HTTP 服务，默认暴露 /mcp 端点。
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
