# Amap CityWalk Tool Loop

这个实验只演示一个点：如何用模型驱动的 LangGraph tool loop 实现一个最小 CityWalk Agent。

模型使用本地 Ollama，高德地图能力来自高德 MCP。模型自己决定何时调用工具，Host 只负责执行工具调用并把结果写回 `ToolMessage`。

## 流程

```text
START
  ↓
agent_llm
  ↓ 有 tool call
run_mcp_tools
  ↓
agent_llm
  ↓ 无 tool call
END
```

实验只暴露两个高德 MCP 工具：

- `maps_geo`：把用户输入的区域解析成坐标。
- `maps_around_search`：基于坐标搜索附近 POI。

不包含天气、地图链接生成、POI 白名单、坐标审计和最终回答兜底。那些属于可靠性工程，不是这个实验要说明的重点。

## 文件结构

- `agent.py`：LangGraph State、模型节点、工具节点和条件边。
- `adapters.py`：Ollama 与高德 MCP 的最小适配。
- `cli.py`：命令行参数、MCP 连接、运行编排和 trace 打印。

## 运行

从仓库根目录运行：

```bash
uv run --no-sync \
  python -m labs.langgraph.foundations.experiments.amap_citywalk_tool_loop
```

自定义问题：

```bash
uv run --no-sync \
  python -m labs.langgraph.foundations.experiments.amap_citywalk_tool_loop \
  --question "我想在上海衡山路附近散步 2 小时，找咖啡和书店"
```

只导出 Graphviz 结构图：

```bash
uv run --no-sync \
  python -m labs.langgraph.foundations.experiments.amap_citywalk_tool_loop \
  --graphviz
```
