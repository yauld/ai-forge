# 06 | 用模型驱动tool loop实现一个最小CityWalk Agent

## 想要做的事儿

问题：“我想在杭州西湖附近citywalk 3小时，想找咖啡、书店或展览，请推荐一个轻量路线。”

实现：模型用本地Ollama，地图能力来自高德MCP，然后，不用workflow，纯纯让模型自己驱动tool-calling loop来看它是如何观察-执行-观察-执行的。

LangGraph在这里只负责这个图：

```text
agent_llm -> run_mcp_tools -> agent_llm
```

## 图结构：

```text
START
  ↓
agent_llm
  ├─ 有tool call -> run_mcp_tools -> agent_llm
  ├─ tool call轮数过多 -> ask_model_to_finish -> agent_llm
  └─ 无tool call -> END
```

![最小CityWalk tool loop图结构](assets/amap_citywalk_tool_loop_graph.png)

## 用到的2个高德MCP工具

- maps_geo：把“杭州西湖”这样的目标区域解析成经纬度。
- maps_around_search：基于经纬度搜索附近POI，比如咖啡、书店、展览。

## 实验目录

新实验放在：

```text
labs/langgraph/foundations/experiments/19_amap_citywalk_tool_loop/
```

核心文件：

```text
agent.py      # LangGraph State、模型节点、工具节点和条件边
adapters.py   # Ollama与高德MCP的最小适配
cli.py        # 命令行入口、MCP连接、trace打印
README.md     # 实验说明
```

## 部分主干代码

State只保留三件事：

```python
class CityWalkToolLoopState(TypedDict):
    """LangGraph在模型节点与工具节点之间传递的最小状态。"""

    messages: Annotated[list[AnyMessage], add_messages]
    trace: list[str]
    tool_rounds: int
```

1、messages是Agent的上下文，里面会依次放入：
- SystemMessage：告诉模型它是CityWalk助手，以及有哪些工具；
- HumanMessage：用户问题；
- AIMessage：模型每一轮的回复，可能带tool call；
- ToolMessage：Host执行MCP工具后的结果。

2、trace只是为了终端观察，不参与模型推理。

3、tool_rounds只用来防止无限工具循环。

系统提示词尽量不墨迹：

```python
def build_system_prompt(model_tools: list[dict[str, Any]]) -> str:
    """构造系统提示词：让模型自己决定何时调用工具、何时回答。"""
    return (
        "你是一个CityWalk助手。\n"
        "需要地图事实时，请自己调用工具；不需要时直接回答。\n"
        "建议先用maps_geo获取目标区域坐标，再用maps_around_search搜附近POI。\n"
        "最终回答给出3个左右地点和一个简短行程建议；地点名称和地址只使用工具观察中出现过的信息，"
        "不要补充未搜索到的地点，不需要生成地图链接。\n\n"
        "当前可用工具：\n"
        f"{summarize_tools(model_tools)}"
    )
```

注意，， 这里没有告诉模型“必须先查咖啡，再查书店，再查展览”，然后，只给了工具使用建议，具体要不要调用、调用几次、什么时候停止，由模型自己判断。

模型节点很薄

```python
def make_agent_llm(model: Any):
    """创建模型节点。"""

    async def agent_llm(state: CityWalkToolLoopState) -> dict[str, Any]:
        """模型观察当前messages，并自己决定调用工具或最终回答。"""
        response = await model.ainvoke(state["messages"])
        trace_items = [
            f"[模型观察 {state['tool_rounds'] + 1}] {compact_text(response.content)}",
        ]

        tool_calls = getattr(response, "tool_calls", None) or []
        if tool_calls:
            trace_items.append(
                "[模型决策] Tool Calls："
                + json.dumps(tool_calls, ensure_ascii=False, default=str)
            )
        else:
            trace_items.append("[模型决策] 没有tool call，模型认为可以回答。")

        return {"messages": [response], "trace": append_trace(state, *trace_items)}

    return agent_llm
```

这个节点会把当前messages交给模型，模型如果返回tool_calls，后面就进入工具节点；如果不返回就结束。

工具节点也很薄：

```python
def make_run_mcp_tools(mcp_session: ClientSession, allowed_tools: set[str]):
    """创建工具执行节点。"""

    async def run_mcp_tools(state: CityWalkToolLoopState) -> dict[str, Any]:
        """Host执行模型刚刚选择的MCP工具，并把结果写回ToolMessage。"""
        last_message = state["messages"][-1]
        if not isinstance(last_message, AIMessage):
            raise RuntimeError("run_mcp_tools期望最后一条消息是AIMessage。")

        tool_messages: list[ToolMessage] = []
        trace_items: list[str] = []
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            arguments = tool_call["args"]
            trace_items.append(
                f"[Host行动] 执行 {tool_name}({json.dumps(arguments, ensure_ascii=False)})"
            )
            tool_result = await call_mcp_tool(
                mcp_session,
                allowed_tools,
                tool_name,
                arguments,
            )
            trace_items.append(f"[工具观察] {compact_json(tool_result)}")
            tool_messages.append(
                ToolMessage(
                    content=json.dumps(tool_result, ensure_ascii=False),
                    tool_call_id=tool_call["id"],
                )
            )

        return {
            "messages": tool_messages,
            "tool_rounds": state["tool_rounds"] + 1,
            "trace": append_trace(state, *trace_items),
        }

    return run_mcp_tools
```

Host只检查工具是不是被放行，放行就执行对应高德mcp工具

```python
async def call_mcp_tool(
    session: ClientSession,
    allowed_tools: set[str],
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Host侧执行模型请求的MCP工具。"""
    if tool_name not in allowed_tools:
        raise RuntimeError(f"模型请求了未放行的工具：{tool_name}")
    if not isinstance(arguments, dict):
        raise RuntimeError(f"工具参数必须是JSON object：{arguments!r}")

    result = await session.call_tool(tool_name, arguments)
    return extract_tool_payload(result)
```

graph中的条件边：

```python
def route_after_agent(
    state: CityWalkToolLoopState,
) -> Literal["run_mcp_tools", "ask_model_to_finish", "__end__"]:
    """根据模型是否发起tool call决定继续工具循环还是结束。"""
    last_message = state["messages"][-1]
    tool_calls = getattr(last_message, "tool_calls", None) or []
    if not tool_calls:
        return "__end__"
    if state["tool_rounds"] >= MAX_TOOL_ROUNDS:
        return "ask_model_to_finish"
    return "run_mcp_tools"
```

这里就是模型驱动tool loop的关键地方：有tool call就执行工具，没有就结束，另外也添加了一个工具轮数太多的兜底，提醒模型该收手了。

完整Graph：

```python
builder = StateGraph(CityWalkToolLoopState)
builder.add_node("agent_llm", make_agent_llm(model))
builder.add_node("run_mcp_tools", make_run_mcp_tools(mcp_session, allowed_tools))
builder.add_node("ask_model_to_finish", ask_model_to_finish)

builder.add_edge(START, "agent_llm")
builder.add_conditional_edges(
    "agent_llm",
    route_after_agent,
    {
        "run_mcp_tools": "run_mcp_tools",
        "ask_model_to_finish": "ask_model_to_finish",
        "__end__": END,
    },
)
builder.add_edge("run_mcp_tools", "agent_llm")
builder.add_edge("ask_model_to_finish", "agent_llm")

graph = builder.compile(name="Amap CityWalk Tool Loop")
```

## 实际运行的调性

实验启动后，先连接高德MCP，并把工具列表绑定给Ollama模型：

```text
连接地址：https://mcp.amap.com/mcp?key=***
模型提供方：ollama
模型：qwen3-coder:30b
用户问题：我想在杭州西湖附近citywalk 3小时，想找咖啡、书店或展览，请推荐一个轻量路线。

协议版本：2025-03-26
模型可见工具：["maps_around_search", "maps_geo"]
```

第一轮，模型没有直接回答，而是决定调用maps_geo：

```text
[模型观察 1] 本轮未输出文本，只给出tool call。
[模型决策] Tool Calls：[{"name": "maps_geo", "args": {"address": "杭州西湖"}, ...}]
[Host行动] 执行maps_geo({"address": "杭州西湖"})
[工具观察] {"results": [{"country": "中国", "province": "浙江省", "city": "杭州市", ... "location": "120.130396,30.259242", "level": "区县"}, ...]}
```

第二轮，模型观察到坐标后，决定搜咖啡：

```text
[模型观察 2] 本轮未输出文本，只给出tool call。
[模型决策] Tool Calls：[{"name": "maps_around_search", "args": {"keywords": "咖啡", "location": "120.130396,30.259242", "radius": "1000"}, ...}]
[Host行动] 执行maps_around_search({"keywords": "咖啡", "location": "120.130396,30.259242", "radius": "1000"})
[工具观察] {"pois": [{"id": "B0J06ZG937", "name": "暇意西餐咖啡厅", "address": "曙光路156号(西湖区社会治理中心旁边)", ...}, ...]}
```

后面模型继续搜书店和展览：

```text
[Host行动] 执行maps_around_search({"keywords": "书店", "location": "120.130396,30.259242", "radius": "1000"})
[工具观察] {"pois": [{"id": "B0J01A1B07", "name": "西湖书房(曙光路店)", "address": "曙光新村东1门旁", ...}, {"id": "B0LA27N0OU", "name": "晓风书屋(阅见西湖店)", "address": "曙光路184号阅见西湖", ...}, ...]}

[Host行动] 执行maps_around_search({"keywords": "展览", "location": "120.130396,30.259242", "radius": "1000"})
[工具观察] {"pois": [{"id": "B0LD3AHQ97", "name": "阅见西湖", "address": "曙光路184号", ...}, ...]}
```

最后一轮，模型没有再发tool call，直接回答：

```text
[模型观察 5] 根据您的需求，为您规划了一条轻量级的西湖CityWalk路线，包含咖啡、书店和展览，适合3小时内完成：...
[模型决策] 没有tool call，模型认为可以回答。
```

最终回答使用了工具观察中出现过的地点：

```text
1. 晓风书屋(阅见西湖店)
   - 地址：曙光路184号阅见西湖

2. 阅见西湖
   - 地址：曙光路184号

3. 暇意西餐咖啡厅
   - 地址：曙光路156号(西湖区社会治理中心旁边)
```

结束。

---

```text
GitHub仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/langgraph/foundations/19 | 用模型驱动tool loop实现一个最小CityWalk Agent.md

实验代码：
labs/langgraph/foundations/experiments/19_amap_citywalk_tool_loop/
```
