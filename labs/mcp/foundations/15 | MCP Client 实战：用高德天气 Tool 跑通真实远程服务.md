# MCP Client 实战：用高德天气 Tool 跑通真实远程服务

前面的 MCP 实验大多围绕本地 Server 展开：我们自己写 Server，自己定义 Tool，
再让 Client 调用它。真实项目里还有另一类更常见的情况：

> Server 不是我们启动的本地进程，而是一个官方远程服务；我们自己的 AI 应用只负责
> 连接它、发现工具、调用工具，并把结果交给模型回答用户。

本文用高德官方 MCP Server 做一次完整实验。实验目标不是“查一次天气”这么简单，而是看清
一个自研 AI 应用后端如何扮演 Host：

```text
用户问题
  → 本地 Ollama 模型判断是否需要外部信息
  → Python Host 连接高德 MCP Server
  → tools/list 动态发现工具
  → 模型提出 tool call
  → Host 校验并执行 MCP tools/call
  → 工具结果回到模型
  → 模型生成最终回答
```

实验使用的具体问题是：

```text
明天去杭州西湖适合出门吗？请结合天气给出建议。
```

完成实验后，你应该能解释：

- 为什么接入远程 MCP Server 时不需要自己启动 Server；
- 高德 Web 服务 Key 如何安全进入 Python Host，而不是进入模型；
- `tools/list` 返回的工具目录如何变成模型可见的工具定义；
- 模型第一次为什么选择 `maps_weather`；
- Host 如何把模型提出的 tool call 转成真正的 MCP Tool 调用；
- 第二次模型为什么不再调用工具，而是根据 Tool 结果回答用户。

## 1. 实验边界

这次实验只做一个真实远程 MCP Client 闭环。为了让主线清楚，先明确不做什么。

本文会做：

| 步骤 | 作用 |
| --- | --- |
| 从 `.env` 读取 `AMAP_MCP_KEY` | 避免把高德 Key 写入代码和终端输出 |
| 使用 Streamable HTTP 连接高德 MCP Server | 连接官方远程 MCP endpoint |
| 调用 `initialize` 和 `tools/list` | 确认协议连接和工具发现成功 |
| 把 MCP Tool schema 交给 Ollama | 让本地模型基于真实工具定义选择工具 |
| 校验并执行模型提出的 tool call | 保持 Host 对外部调用的控制权 |
| 把 Tool 结果交回模型 | 让模型基于真实数据生成最终回答 |

本文不会做：

| 不做什么 | 原因 |
| --- | --- |
| 不自己实现高德天气 Server | 高德已经提供官方远程 MCP Server |
| 不直接调用高德天气 Web API | 本实验关注的是 MCP Client 调用链路 |
| 不使用 SSE | 高德 MCP 快速接入当前推荐 Streamable HTTP |
| 不把 Key 交给模型 | 模型只看工具定义和工具结果，不接触密钥 |
| 不做 Web UI | 命令行更容易观察 Host、模型和 MCP Client 的边界 |
| 不引入 LangGraph | 先把最小 Host loop 讲清楚，后续再工程化成状态图 |

如果你把本文代码改成 Web 服务，外层可以变成 FastAPI、Flask 或任意后端框架；
但核心链路仍然是本文这六步。

## 2. 配套文件

本实验新增两个脚本：

| 文件 | 作用 |
| --- | --- |
| `examples/amap_mcp_tools_probe.py` | 连接高德 MCP Server，打印 `tools/list` 返回的工具目录和参数 Schema |
| `examples/amap_mcp_agent_demo.py` | 模拟自研 AI 应用后端，用本地 Ollama 选择工具，再由 Host 调用高德 MCP Tool |

两个脚本的分工很接近真实开发流程。

第一步通常不是直接写业务逻辑，而是先探测远程 Server 到底暴露了什么能力：

```bash
uv run labs/mcp/foundations/examples/amap_mcp_tools_probe.py
```

确认工具目录后，再运行完整 AI 应用闭环：

```bash
uv run labs/mcp/foundations/examples/amap_mcp_agent_demo.py
```

## 3. 运行前准备

本实验需要三个前提。

第一，高德开放平台已经创建 Web 服务 Key，并且 Key 可访问高德 MCP Server。项目根目录
的 `.env` 中应有：

```dotenv
AMAP_MCP_KEY=你的高德Key
```

不要把真实 Key 写进文章、截图、Git 提交或命令行参数。当前仓库的 `.gitignore` 已经忽略
`.env`，本地运行时由脚本读取。

第二，本地 Ollama 已启动，并且已经有 `qwen3-coder:30b`：

```bash
ollama list
```

如果没有这个模型，可以先拉取：

```bash
ollama pull qwen3-coder:30b
```

第三，项目依赖已安装：

```bash
uv sync
```

如果你的网络环境无法访问 `https://mcp.amap.com/mcp`，工具探测阶段会失败；如果 Ollama
没有启动，完整闭环会在模型调用阶段失败。排查时先分开运行 `amap_mcp_tools_probe.py`
和 `ollama list`，不要一上来同时怀疑两边。

## 4. 整体数据流

这次实验里一共有五个角色：

| 角色 | 在实验里是谁 | 职责 |
| --- | --- | --- |
| 用户 | 命令行里的问题 | 提出自然语言需求 |
| Host | `amap_mcp_agent_demo.py` | 掌控流程、保存 Key、连接 MCP、校验工具调用 |
| LLM | 本地 `qwen3-coder:30b` | 判断要不要调用工具，拿结果后组织回答 |
| MCP Client | MCP Python SDK 的 `ClientSession` | 发送 `initialize`、`tools/list`、`tools/call` |
| MCP Server | 高德官方远程 MCP Server | 暴露地图、天气、路线等工具能力 |

关键边界是：

```text
模型不直接连接高德。
模型不持有 Key。
模型不发送 MCP 请求。
```

模型只输出“我想调用哪个工具、参数是什么”。真正的外部调用由 Host 完成。

用一条完整链路表示：

```text
.env
  → Python Host 读取 AMAP_MCP_KEY
  → Streamable HTTP 连接 https://mcp.amap.com/mcp?key=***
  → initialize
  → tools/list
  → 把工具定义交给 Ollama
  → Ollama 返回 maps_weather(city=杭州)
  → Host 校验 tool name 和 arguments
  → tools/call
  → 高德返回天气预报
  → ToolMessage 加回 messages
  → Ollama 生成最终回答
```

下面按这条线逐步看代码和现象。

## 5. 第一步：从 `.env` 读取高德 Key

高德 Key 是服务端密钥。实验脚本不会把它写死在代码里，而是从项目根目录 `.env` 读取：

```python
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[3]
DEFAULT_MCP_ENDPOINT = "https://mcp.amap.com/mcp"


def load_amap_mcp_url() -> str:
    """从项目 .env 读取高德 Key，并拼出远程 MCP URL。"""
    load_dotenv(REPO_ROOT / ".env")
    key = os.getenv("AMAP_MCP_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "缺少 AMAP_MCP_KEY。请先在项目根目录 .env 中配置高德 Web 服务 Key。"
        )
    return f"{DEFAULT_MCP_ENDPOINT}?key={key}"
```

这段代码有两个设计点。

第一，脚本只要求 `.env` 中有 `AMAP_MCP_KEY`，不要求再维护一个完整的
`AMAP_MCP_URL`。endpoint 是代码常量，Key 是本地密钥，职责更清楚。

第二，运行时打印连接地址时会打码：

```python
print(f"连接地址：{DEFAULT_MCP_ENDPOINT}?key=***")
```

真实 URL 会传给 MCP SDK，但不会进入终端日志。实验文稿、截图和后续调试记录里都不应该
出现真实 Key。

## 6. 第二步：通过 Streamable HTTP 连接高德 MCP Server

远程 MCP Server 的特征是：Client 不负责启动 Server，只按 URL 连接它。

本实验使用 MCP Python SDK 的 `streamable_http_client`：

```python
async with streamable_http_client(mcp_url) as (read, write, _):
    async with ClientSession(read, write) as session:
        initialized = await session.initialize()
        tools_result = await session.list_tools()
```

这里有两层：

1. `streamable_http_client(mcp_url)` 建立 Streamable HTTP 通道；
2. `ClientSession(read, write)` 在通道之上发送标准 MCP 消息。

我们没有手写：

```python
httpx.post("https://mcp.amap.com/mcp?key=...")
```

因为这不是普通 REST API 调用，而是 MCP 协议通信。SDK 会处理 Streamable HTTP transport
和 MCP session 细节；业务代码只需要调用 `initialize`、`list_tools` 和 `call_tool`。

先运行工具探测脚本：

```bash
uv run labs/mcp/foundations/examples/amap_mcp_tools_probe.py
```

一次真实输出为：

```text
连接地址：https://mcp.amap.com/mcp?key=***
协议版本：2025-03-26
工具数量：15

1. maps_direction_bicycling
   描述：骑行路径规划用于规划骑行通勤方案，规划时会考虑天桥、单行线、封路等情况。最大支持 500km 的骑行路线规划

...

15. maps_weather
   描述：根据城市名称或者标准adcode查询指定城市的天气
```

这一步证明三件事：

- 高德 Key 能访问远程 MCP Server；
- Streamable HTTP 连接成功；
- `tools/list` 返回了当前 MCP Server 实际暴露的工具目录。

注意这里看到的是 15 个 MCP Tool，不等于高德控制台里 Web 服务 Key 可用的所有 API。
控制台显示的是 Key 的 Web API 权限范围；MCP Client 能调用什么，要以远程 Server
的 `tools/list` 返回为准。

## 7. 第三步：确认天气 Tool 的真实参数

工具名不能靠猜。即使你知道高德有天气能力，也应该先看 `tools/list` 返回的 Schema。

运行：

```bash
uv run labs/mcp/foundations/examples/amap_mcp_tools_probe.py --schema
```

其中 `maps_weather` 的参数 Schema 为：

```json
{
  "type": "object",
  "properties": {
    "city": {
      "type": "string",
      "description": "城市名称或者adcode"
    }
  },
  "required": [
    "city"
  ]
}
```

这说明调用天气工具时只需要传一个 `city`：

```json
{
  "city": "杭州"
}
```

也可以传标准 adcode，例如杭州是 `330100`。实验默认让模型从用户问题中抽取城市名，
所以它会生成 `{"city": "杭州"}`。

## 8. 第四步：把 MCP 工具定义交给本地 Ollama

`tools/list` 的接收方是 MCP Client，不是模型。Server 返回工具目录后，Host 需要决定
哪些工具进入模型上下文，以及用什么格式交给模型。

实验脚本先把 MCP Tool 转成 LangChain/Ollama 可识别的工具定义：

```python
def build_model_tools(tools: list[Any]) -> list[dict[str, Any]]:
    """把 MCP tools/list 的结果转换为 LangChain/Ollama 可见的工具定义。"""
    model_tools: list[dict[str, Any]] = []
    for tool in tools:
        model_tools.append(
            {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": to_jsonable(tool.inputSchema),
            }
        )
    return model_tools
```

然后绑定到本地模型：

```python
model = ChatOllama(model=model_name, temperature=0).bind_tools(model_tools)
```

这一步很关键。模型拿到的不是 Python 函数，也不是 MCP session，更不是高德 Key。
模型拿到的是一组工具说明：

```text
工具名
工具描述
参数 Schema
```

为了帮助模型理解当前可用能力，脚本还把工具目录压缩进 SystemMessage：

```python
SystemMessage(
    content=(
        "你是一个地图与出行助手，运行在用户自研 AI 应用的后端中。\n"
        f"今天是 {date.today().isoformat()}。\n"
        "你不能编造实时天气、地点或路线信息；需要外部信息时，"
        "必须使用 Host 提供的 MCP 工具。\n"
        "工具调用由 Host 执行，你只负责选择工具和参数。\n"
        "拿到工具结果后，请用中文给出简洁、实用的回答。\n\n"
        "当前可用 MCP 工具：\n"
        f"{summarize_tools(model_tools)}"
    )
)
```

这段提示词做了三件事：

1. 告诉模型它是地图与出行助手；
2. 明确实时天气、地点、路线不能编造；
3. 强调工具调用由 Host 执行，模型只负责选择工具和参数。

现在模型具备了选择 `maps_weather` 的信息，但还没有发生任何外部调用。

## 9. 第五步：模型第一次响应，提出 Tool Call

运行完整脚本：

```bash
uv run labs/mcp/foundations/examples/amap_mcp_agent_demo.py \
  --question '明天去杭州西湖适合出门吗？请结合天气给出建议。'
```

脚本会先打印远程连接和工具发现结果：

```text
连接地址：https://mcp.amap.com/mcp?key=***
本地模型：qwen3-coder:30b
用户问题：明天去杭州西湖适合出门吗？请结合天气给出建议。
协议版本：2025-03-26
发现工具：["maps_around_search", "maps_direction_bicycling", ..., "maps_weather"]
```

第一次调用模型时，`messages` 里只有：

```text
System: 角色、规则、当前日期、可用 MCP 工具目录
Human:  明天去杭州西湖适合出门吗？请结合天气给出建议。
```

模型看到“明天”“杭州西湖”“天气建议”，再结合工具目录中的 `maps_weather`，于是返回：

```text
模型回合 1：
  文本：
  Tool Calls：[{"name": "maps_weather", "args": {"city": "杭州"}, ...}]
```

注意这里的“文本”为空是正常的。模型还没有最终回答，因为它知道自己缺少实时天气数据。
它先提出一个工具调用意图：

```json
{
  "name": "maps_weather",
  "args": {
    "city": "杭州"
  }
}
```

这一步仍然没有真正访问高德天气。模型只是说：“Host，请帮我调用这个工具。”

## 10. 第六步：Host 校验并执行 MCP Tool

模型输出 tool call 后，Host 不能无条件执行。实验脚本至少做两道检查：

```python
async def call_mcp_tool(
    session: ClientSession,
    allowed_tools: set[str],
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Host 校验工具名后，才把调用发送给远程 MCP Server。"""
    if tool_name not in allowed_tools:
        raise RuntimeError(f"模型请求了未发现的工具：{tool_name}")
    if not isinstance(arguments, dict):
        raise RuntimeError(f"工具参数必须是 JSON object：{arguments!r}")

    result = await session.call_tool(tool_name, arguments)
    return extract_tool_payload(result)
```

第一道检查：模型请求的工具名必须来自 `tools/list`。如果模型幻觉出一个不存在的
`get_weather`，Host 会拒绝。

第二道检查：参数必须是 JSON object。MCP Tool 调用不是把一段自然语言直接丢给 Server，
而是发送结构化参数。

检查通过后，Host 才发起真正的 MCP 调用：

```python
result = await session.call_tool(tool_name, arguments)
```

终端输出为：

```text
执行 MCP Tool：maps_weather
参数：{"city": "杭州"}
```

随后高德 MCP Server 返回天气数据。实验脚本把高德返回的 JSON 文本整理成普通 dict：

```python
def extract_tool_payload(result: Any) -> dict[str, Any]:
    """提取 MCP Tool 结果，并兼容高德把 JSON 放在 TextContent.text 的情况。"""
    if result.structuredContent is not None:
        return to_jsonable(result.structuredContent)

    content = to_jsonable(result.content)
    if (
        isinstance(content, list)
        and len(content) == 1
        and isinstance(content[0], dict)
        and isinstance(content[0].get("text"), str)
    ):
        text = content[0]["text"].strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"content": content}
        if isinstance(parsed, dict):
            return parsed
        return {"content": parsed}

    return {"content": content}
```

一次真实返回的关键部分为：

```json
{
  "city": "杭州市",
  "forecasts": [
    {
      "date": "2026-07-15",
      "dayweather": "多云",
      "nightweather": "多云",
      "daytemp": "38",
      "nighttemp": "29"
    },
    {
      "date": "2026-07-16",
      "dayweather": "多云",
      "nightweather": "多云",
      "daytemp": "37",
      "nighttemp": "29"
    }
  ]
}
```

这里的天气数据是运行时从高德 MCP Server 返回的真实结果。你在其他日期运行时，日期和
天气值会不同，这是预期现象。

## 11. 第七步：把 Tool 结果交回模型

Host 拿到工具结果后，不能直接替模型回答。实验里继续遵守工具调用消息协议：

```python
messages.append(
    ToolMessage(
        content=json.dumps(tool_result, ensure_ascii=False),
        tool_call_id=tool_call["id"],
    )
)
```

这一步把“高德天气结果”放回对话上下文。第二次调用模型时，`messages` 已经变成：

```text
System: 角色、规则、当前日期、可用 MCP 工具目录
Human:  明天去杭州西湖适合出门吗？请结合天气给出建议。
AI:     请求调用 maps_weather(city=杭州)
Tool:   高德返回的杭州天气预报
```

所以第二轮模型不是凭空回答，而是在读取工具结果后组织最终内容。

真实输出为：

```text
模型回合 2：
  文本：根据天气预报，明天（7月16日）杭州天气为多云，白天温度约37℃，夜间29℃，风向为东南风，风力1-3级。西湖景区气温较高，建议做好防晒和防暑准备，携带足够的饮用水。若无特殊安排，出门游玩是合适的，但注意避开中午高温时段。
  Tool Calls：[]

最终回答：根据天气预报，明天（7月16日）杭州天气为多云，白天温度约37℃，夜间29℃，风向为东南风，风力1-3级。西湖景区气温较高，建议做好防晒和防暑准备，携带足够的饮用水。若无特殊安排，出门游玩是合适的，但注意避开中午高温时段。
```

第二轮 `Tool Calls：[]` 表示模型认为信息已经足够，不再请求工具。脚本看到空列表后，
把当前模型文本视为最终回答并结束。

## 12. 为什么要用循环

完整脚本里有一个循环：

```python
for round_index in range(1, MAX_TOOL_ROUNDS + 1):
    response = await model.ainvoke(messages)
    messages.append(response)

    tool_calls = response.tool_calls
    if not tool_calls:
        print(f"最终回答：{response.content}")
        return

    for tool_call in tool_calls:
        ...
        messages.append(ToolMessage(...))
```

这个循环不是写死“第一轮调用工具、第二轮总结”。它表达的是更通用的 Agent loop：

```text
调用模型
  → 如果模型请求工具，Host 执行工具并把结果放回 messages
  → 如果模型不再请求工具，当前回复就是最终回答
```

天气问题通常两轮就够：

```text
第 1 轮：模型请求 maps_weather
第 2 轮：模型根据天气结果回答
```

但如果问题更复杂，可能会需要多轮：

```text
用户：明天从杭州东站去西湖，适合骑车还是打车？

第 1 轮：调用 maps_geo，把杭州东站和西湖解析为经纬度
第 2 轮：调用 maps_weather，查杭州天气
第 3 轮：调用 maps_direction_driving 或 maps_direction_bicycling
第 4 轮：综合天气和路线结果回答
```

`MAX_TOOL_ROUNDS = 4` 是安全上限，防止模型不断请求工具导致无限循环。真实项目里还会继续
加入超时、重试、工具白名单、危险工具确认和审计日志。

## 13. 这是不是生产写法

本文的手写循环是规范的最小 Host loop，适合学习和小型 demo。它把最重要的边界暴露得很清楚：

```text
模型做选择，Host 做执行。
模型看工具说明，Host 持有 MCP Session。
模型不碰 Key，Host 管理外部调用。
```

如果要做更完整的应用，可以按复杂度演进：

| 场景 | 推荐方式 |
| --- | --- |
| 学习 MCP Client 和工具调用边界 | 手写循环 |
| 普通问答 + 少量工具调用 | LangChain 工具调用 |
| 多步骤任务、状态、重试、人工确认、可恢复执行 | LangGraph |

也就是说，本文不是为了替代 LangGraph，而是先把底层控制流讲清楚。等这个 Host loop
稳定后，再把它拆成 LangGraph 节点会更自然：

```text
user_input
  → discover_tools
  → llm_decide
  → tool_guard
  → mcp_call
  → llm_respond
```

这样做的好处是：你知道每个节点从哪里来，而不是一开始就把协议、模型和工具执行都藏进框架。

## 14. 常见问题

### 14.1 控制台显示 19 个服务，为什么 `tools/list` 只有 15 个 Tool

高德控制台里的“可使用服务”表示这个 Web 服务 Key 可以调用的 Web API 权限范围。
MCP Server 的 `tools/list` 表示当前远程 MCP Server 实际封装并暴露给 MCP Client 的工具。

两者不是同一层级：

```text
Web 服务 Key 可用 API
  → 高德 MCP Server 选择其中一部分封装成 MCP Tool
  → MCP Client 通过 tools/list 看到这些 Tool
```

所以实验以 `tools/list` 为准。

### 14.2 为什么不直接调用天气 API

直接调用天气 API 可以查天气，但那样学到的是高德 Web API，不是 MCP。

本文要观察的是：

```text
Client 如何发现 Tool
模型如何基于 Tool schema 生成 tool call
Host 如何通过 MCP Client 发起 tools/call
Tool Result 如何回到模型上下文
```

这些都是 MCP 应用中的关键动作。

### 14.3 为什么模型第二轮 `Tool Calls` 是空列表

因为第二轮模型已经看到工具结果，可以回答用户了。

第一轮上下文里没有天气数据，所以模型请求 `maps_weather`。第二轮上下文里已经有
高德返回的天气预报，所以模型不再请求工具，而是生成最终文本。脚本看到 `tool_calls`
为空，就把这条回复当作最终回答。

### 14.4 如果模型选错工具怎么办

当前实验做了最基本的工具名校验：

```text
模型请求的 tool_name 必须来自 tools/list
```

但真实项目里还应该继续做：

- 按场景过滤工具，不把所有工具都交给模型；
- 校验参数是否符合 schema；
- 对导航、打车、URI 生成等工具加确认；
- 限制调用轮数和调用频率；
- 记录脱敏审计日志；
- 对工具异常做可解释错误返回。

本文暂时只保留最小边界，让主线聚焦“天气 Tool 如何被使用”。

## 15. 验收清单

完成实验后，可以用这份清单自查：

| 检查项 | 预期现象 |
| --- | --- |
| `.env` 中配置了 `AMAP_MCP_KEY` | 脚本不报缺少 Key |
| 运行 `amap_mcp_tools_probe.py` | 能看到协议版本和工具数量 |
| 工具目录中包含 `maps_weather` | 描述为根据城市名称或 adcode 查询天气 |
| 运行 `amap_mcp_tools_probe.py --schema` | `maps_weather` 参数包含必填 `city` |
| 运行 `amap_mcp_agent_demo.py` | 第一轮模型提出 `maps_weather` tool call |
| Host 执行工具调用 | 终端打印 `执行 MCP Tool：maps_weather` |
| 工具结果返回 | 能看到 `city` 和 `forecasts` |
| 第二轮模型不再请求工具 | `Tool Calls：[]` |
| 最终回答引用天气结果 | 回答中包含天气、温度和出行建议 |

如果这些都成立，就说明你已经完成了一个真实远程 MCP Server 的最小 AI 应用闭环。

## 小结

这次实验的重点不是高德天气本身，而是“自研 AI 应用如何使用远程 MCP Tool”。

一条可靠的链路应该是：

```text
Key 留在 Host
Host 连接 MCP Server
Host 通过 tools/list 发现工具
模型基于工具定义提出 tool call
Host 校验并执行 tools/call
模型基于 Tool 结果回答用户
```

把这条链路跑通以后，再接更多高德工具、更多 MCP Server，或者把手写循环升级成
LangGraph 状态图，都会更稳。因为你已经看清了最核心的边界：

> MCP 提供外部能力，模型提出调用意图，Host 负责真正执行。
