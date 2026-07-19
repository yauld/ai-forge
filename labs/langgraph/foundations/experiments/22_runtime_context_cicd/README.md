# LangGraph Runtime Context：CI/CD 发布流水线实验

这个实验用一个很小的 CI/CD 发布流水线说明：

```text
State = 这次发布任务本身的进展和结果
Runtime Context = 这次运行时的环境、身份和外部配置
```

实验流程：

```text
run_tests -> security_scan -> build_image -> deploy -> write_release_note
```

其中：

- `commit_sha`、`test_result`、`image_tag`、`deploy_status` 属于 State。
- `target_env`、`runner_id`、`docker_registry`、`kube_context`、`current_operator`、`dry_run` 属于 Runtime Context。
- 最后一个节点会调用本地 Ollama 的 `qwen3-coder:30b`，根据最终 State 写一段发布摘要。

运行前确认 Ollama 已启动，并且已经拉取模型：

```bash
ollama list
ollama pull qwen3-coder:30b
```

从仓库根目录运行：

```bash
uv run labs/langgraph/foundations/experiments/22_runtime_context_cicd/main.py
```

你会看到同一个初始 State 跑了两次：

```text
同一个 commit：abc123

第一次 Runtime Context：
- target_env = staging
- dry_run = true

第二次 Runtime Context：
- target_env = prod
- dry_run = false
```

对比重点：

1. 两次输入的发布对象都是 `commit_sha=abc123`。
2. Runtime Context 不同，所以部署行为不同。
3. 最终 State 里不会出现 `target_env`、`runner_id`、`kube_context` 这些配置字段。
4. Runtime Context 只在节点执行时被读取，用完不会变成 State。
