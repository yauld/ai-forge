# Stage 10: Skills + MCP Minimal Demo

这个实验只演示正常协作路径：

```text
用户请求
  -> Host 扫描 Skill metadata
  -> Ollama 选择 Skill
  -> Host 加载完整 SKILL.md
  -> Ollama 按 Skill 说明提出 MCP Tool 调用
  -> Host 调用 MCP Server
  -> Ollama 基于 Tool 结果生成最终回答
```

运行命令：

```bash
uv run python labs/skills/foundations/examples/stage10-mcp-skill/host.py
```

默认使用本地 Ollama 模型：

```text
qwen3-coder:30b
```

也可以指定任务：

```bash
uv run python labs/skills/foundations/examples/stage10-mcp-skill/host.py \
  --task "帮我查一下订单 O-1002 的状态、商品和金额，并用一句话告诉我结果。"
```

本实验的关键边界：

- `SKILL.md` 提供任务方法和工具使用说明。
- `mcp_server.py` 提供真实可调用工具 `get_order`。
- `host.py` 负责把模型、Skill 和 MCP ClientSession 串起来。
