"""对比无 Token 与登录授权后访问远程 MCP Server 的结果。

先启动 remote_auth_server.py 和 remote_auth_resource_server.py，再运行：
    uv run labs/mcp/foundations/examples/remote_auth_client.py
"""

from __future__ import annotations

import asyncio

import httpx

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


MCP_URL = "http://127.0.0.1:8001/mcp"
AUTH_SERVER_URL = "http://127.0.0.1:9000"
CLIENT_ACCESS_KEY = "ai-forge-demo-client"
CLIENT_SECRET_KEY = "ai-forge-demo-secret"
REDIRECT_URI = "http://127.0.0.1:8765/callback"
SCOPE = "orders:read"
DEMO_USER = "reader@example.com"
DEMO_PASSWORD = "letmein"


async def request_access_token() -> str:
    """用演示账号完成登录和同意，再用授权码换取 access token。"""
    async with httpx.AsyncClient() as client:
        # 1. 发起授权请求。
        #
        # 真实 OAuth 中，这一步通常会打开浏览器，让用户看到登录页和授权页。
        # 本实验不渲染页面，所以 /authorize 只做两件事：
        # - 让 Authorization Server 先检查 client_id 和 scope 是否可接受；
        # - 返回一段提示，说明下一步需要用户登录并同意授权。
        #
        # 注意：这里还不会产生 access token，也不会调用 MCP Server。
        hint = await client.get(
            f"{AUTH_SERVER_URL}/authorize",
            params={
                "client_id": CLIENT_ACCESS_KEY,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE,
                "state": "ai-forge-demo",
            },
        )
        hint.raise_for_status()
        hint_payload = hint.json()
        print("1. 发起授权请求")
        print(f"   授权服务：{hint_payload['message']}")
        print(f"   申请权限：{hint_payload['requested_scope']}")

        # 2. 模拟用户登录并同意授权。
        #
        # 真实系统会在授权页面里完成这一步；本实验用 POST /authorize/approve
        # 表示用户已经输入账号密码，并点击“同意授权 orders:read”。
        #
        # Authorization Server 返回的是 authorization code。code 不是访问凭据，
        # 不能拿去调用 MCP Server；它只表示“这个用户刚刚同意过这次授权请求”。
        approve = await client.post(
            f"{AUTH_SERVER_URL}/authorize/approve",
            data={
                "client_id": CLIENT_ACCESS_KEY,
                "redirect_uri": REDIRECT_URI,
                "scope": SCOPE,
                "state": "ai-forge-demo",
                "username": DEMO_USER,
                "password": DEMO_PASSWORD,
                "consent": "yes",
            },
        )
        approve.raise_for_status()
        code = approve.json()["code"]
        print("2. 用户登录并同意")
        print("   已取得一次性 authorization code")

        # 3. 用 authorization code 换 access token。
        #
        # 这一步会同时提交：
        # - code：证明用户刚刚同意过；
        # - redirect_uri：证明这次换票和前面的授权请求是同一条链路；
        # - client_id/client_secret：证明是这个 Client 在换票。
        #
        # 换出来的 access_token 才会被放进 Authorization: Bearer ...，
        # 也才是 Resource Server 接受的访问凭据。
        token = await client.post(
            f"{AUTH_SERVER_URL}/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ACCESS_KEY,
                "client_secret": CLIENT_SECRET_KEY,
            },
        )
        token.raise_for_status()
        print("3. 授权码换 Token")
        print("   Token 端点已签发短期 access token")
        return token.json()["access_token"]


async def main() -> None:
    # 第一次请求故意不带 Token：认证中间件应在 MCP 初始化前返回 401。
    async with httpx.AsyncClient() as client:
        response = await client.post(MCP_URL, json={})
    print(f"无 Token：HTTP {response.status_code}")

    access_token = await request_access_token()

    # 第二次请求携带授权服务签发的 Token，再建立标准 MCP Session。
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {access_token}"}
    ) as authenticated_client:
        async with streamable_http_client(
            MCP_URL,
            http_client=authenticated_client,
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                result = await session.call_tool(
                    "get_order",
                    {"order_id": "O-1001"},
                )

    print(f"正确 Token：协议版本 {initialized.protocolVersion}")
    print(f"受保护 Tool：{result.structuredContent}")


if __name__ == "__main__":
    asyncio.run(main())
