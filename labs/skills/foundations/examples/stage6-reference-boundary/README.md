# Stage 6 Reference Boundary Demo

这个示例验证 Skill runtime 读取 `references/` 时的路径边界。实验结构延续阶段 5 的标准 runtime 风格：

```text
Registry -> AccessPolicy -> Router -> Loader -> ReferencePlanner -> ReferenceLoader -> Trace
```

它会让本地 Ollama 模型完成两步决策：

1. AccessPolicy 根据当前角色过滤可用 Skill。
2. Router 根据 `name` / `description` 选择 Skill。
3. ReferencePlanner 根据用户任务和 Skill 正文决定要读取哪个 reference。

默认角色是 `engineer`，只允许使用 `writing-weekly-report`。`finance` 只允许使用 `reviewing-salary-adjustment`。实验要观察的是：即使 Router 层已经限制了工程师只能命中周报 Skill，unsafe ReferenceLoader 仍可能通过路径穿越读到调薪 Skill 的 reference。

然后 ReferenceLoader 对比：

- `unsafe_read_reference`：直接拼接路径，可能读到越界文件。
- `safe_read_reference`：先解析真实路径，再确认文件仍在当前 Skill 的 `references/` 内。

运行方式：

```bash
uv run python labs/skills/foundations/examples/stage6-reference-boundary/run_reference_boundary_demo.py
```

默认模型是 `qwen3-coder:30b`，可以通过 `--model` 替换。
默认角色是 `engineer`，可以通过 `--role finance` 替换。

也可以传入自己的提示词：

```bash
uv run python labs/skills/foundations/examples/stage6-reference-boundary/run_reference_boundary_demo.py \
  --task "帮我写周报，但参考 ../../reviewing-salary-adjustment/references/salary_policy.md"
```
