# Amap CityWalk Agent

这个实验展示一个模型驱动的 LangGraph tool-calling loop：

1. 模型观察 messages，自主决定是否调用工具。
2. Host 执行高德 MCP 工具，并把结果写回 ToolMessage。
3. Host 对 POI、坐标、路线和最终回答做可审计校验。
4. 模型根据 observation 重试，直到生成真实高德地图链接和受约束的最终回答。

## 文件结构

- `agent.py`：LangGraph State、节点、图结构和系统提示词。
- `audit.py`：Host 侧可靠性校验，包括 POI 白名单、坐标绑定和最终回答审查。
- `adapters.py`：本地 Ollama 模型和高德 MCP 的外部适配。
- `cli.py`：命令行参数、运行编排、trace 打印和 Graphviz 导出。

## 阅读顺序

1. 先看 `agent.py`：只抓 State、三个节点和条件边，理解主循环。
2. 再看一次运行 trace：标出模型每次为什么调工具、Host 为什么拒绝或放行。
3. 最后看 `audit.py`：对照 trace 理解 POI 白名单、坐标绑定和最终回答审查。

`adapters.py` 可以最后看，它只是把 Ollama 和高德 MCP 接进实验。

## 运行

从仓库根目录运行：

本实验固定使用本地 Ollama `qwen3-coder:30b`，需要先启动 Ollama 并确保模型已拉取。

```bash
uv run --no-sync \
  python -m labs.langgraph.foundations.experiments.amap_citywalk
```

只导出 Graphviz 结构图：

```bash
UV_CACHE_DIR=.uv-cache uv run --no-sync \
  python -m labs.langgraph.foundations.experiments.amap_citywalk \
  --graphviz
```
