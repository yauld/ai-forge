# Stage 5 Runtime Architecture Demo

这个示例用于验证一个教学用 Skills runtime 的最小模块边界。

它会跑通一条真实链路：

```text
Registry -> Ollama Router -> Loader -> Executor -> Tool -> Trace
```

运行方式：

```bash
uv run python labs/skills/foundations/examples/stage5-runtime-architecture/run_runtime_demo.py
```

默认模型是 `qwen3-coder:30b`，可以通过 `--model` 替换。

