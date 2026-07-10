# 05 | 教学用 Skills runtime：扫描、路由、加载、执行如何分工

前面已经能写出一个最小 `SKILL.md`，也能让模型根据 `name` 和 `description` 选中合适的 Skill。

但这还只是“Skill 能不能被发现”的问题。真正做 Agent 工程时，还会遇到下一层问题：一个运行环境到底由谁扫描 Skill、谁负责路由、谁读取正文、谁调用工具、谁记录过程？

如果这些职责全塞进一个脚本，实验一开始会很快，但后面接入 references、scripts、MCP、LangGraph 或审计日志时，代码会变成一团。阶段 5 的目标就是先搭一个教学用 runtime 骨架：代码尽量轻，但模块边界要接近真实 Agent Host。

本实验要回答的问题是：

> 一个支持 Skills 的最小 runtime，如何把扫描、路由、加载、执行和记录拆成清晰的数据流？

## 一、实验目标与配套文件

本实验会实现一个可运行的 Skills runtime demo。它不是完整 Agent 产品，而是一个教学用骨架，用来观察一次请求如何经过 5 个模块：

```text
Registry -> Router -> Loader -> Executor -> Trace
```

配套代码位于：

```text
labs/skills/foundations/examples/stage5-runtime-architecture/
```

目录结构如下：

```text
stage5-runtime-architecture/
├── README.md
├── run_runtime_demo.py
├── runtime/
│   ├── app.py
│   ├── executor.py
│   ├── loader.py
│   ├── registry.py
│   ├── router.py
│   ├── trace.py
│   └── types.py
├── skills/
│   ├── formatting-commit-message/
│   │   └── SKILL.md
│   ├── reviewing-roadmap/
│   │   └── SKILL.md
│   └── writing-weekly-report/
│       └── SKILL.md
└── tools/
    └── text_stats.py
```

这几个模块的职责先定清楚：

| 模块 | 职责 | 本实验做什么 |
| --- | --- | --- |
| Registry | 建立 Skill 索引 | 扫描 `skills/*/SKILL.md`，解析 `name`、`description`、`tools` |
| Router | 选择 Skill | 调用本地 Ollama，根据 metadata 选择 Skill |
| Loader | 加载 Skill | 命中后读取对应 `SKILL.md` 正文 |
| Executor | 执行动作 | 根据 Skill 声明调用本地工具 |
| Trace | 记录过程 | 输出一次请求经过哪些模块、加载哪些文件、调用哪些工具 |

这也是阶段 5 和前面最小路由实验的区别：前面的实验重点是“description 能否支持发现”；这里重点是“发现之后，runtime 如何继续加载、执行和记录”。

## 二、运行前提

本实验使用项目依赖 `langchain-ollama` 调用本地 Ollama，并默认使用 `qwen3-coder:30b`。

先确认本地 Ollama 服务已启动，并且模型存在：

```bash
ollama list
```

在仓库根目录运行：

```bash
uv run python labs/skills/foundations/examples/stage5-runtime-architecture/run_runtime_demo.py
```

如果模型名不同，可以指定：

```bash
uv run python labs/skills/foundations/examples/stage5-runtime-architecture/run_runtime_demo.py --model your-local-model
```

也可以传入自己的任务和待分析内容：

```bash
uv run python labs/skills/foundations/examples/stage5-runtime-architecture/run_runtime_demo.py \
  --task "请审查这份学习路线图是否合理" \
  --content "阶段1：理解概念。阶段2：实现实验。阶段3：整理文章。"
```

## 三、一次请求会经历什么

默认任务写在 `run_runtime_demo.py` 中：

```python
DEFAULT_TASK = "请审查这份 Skills 学习路线图，看看阶段顺序、边界和产出物是否合理。"
```

默认内容是一小段 Skills 学习路线图：

```text
阶段 1：理解 Skills 在 Agent 架构中的定位。
阶段 2：编写最小 SKILL.md，并验证 name 和 description 能否支持路由。
阶段 3：区分 Action Skill 和 Reference Skill。
阶段 5：设计一个教学用 runtime，观察扫描、路由、加载、执行和 trace 如何协作。
```

入口脚本创建 runtime，并把 `skills/` 目录传进去：

```python
runtime = SkillRuntime(
    skills_root=example_root / "skills",
    model_name=args.model,
)
trace = runtime.run(task=args.task, content=args.content)
```

真正的数据流在 `runtime/app.py` 里：

```python
skills = self.registry.scan()
route = self.router.route(task, skills)
loaded_skill = self.loader.load(metadata)
result = self.executor.execute(loaded_skill, task=task, content=content)
```

这几行就是本实验的主干。读代码时可以先抓住这条线，再进入每个模块看细节。

## 四、Registry：先把 Skill 变成索引

Registry 的入口在：

```text
runtime/registry.py
```

它扫描当前实验目录下的 Skill：

```python
for skill_file in sorted(self.skills_root.glob("*/SKILL.md")):
    metadata = self._parse_skill_metadata(skill_file)
    self._skills[metadata.name] = metadata
```

这里有两个重点。

第一，Registry 只读取 frontmatter，不读取正文。因为发现阶段需要的是索引信息：

```yaml
---
name: reviewing-roadmap
description: 当用户要求审查、改进或校验学习路线图、研究计划、内容路线图或分阶段技术学习计划时，使用这个 Skill。
tools:
  - text_stats
---
```

第二，Registry 产出的不是一段提示词，而是结构化数据：

```python
SkillMetadata(
    name=name,
    description=description,
    path=skill_file,
    skill_dir=skill_file.parent,
    tools=tools,
)
```

这个结构会继续交给 Router、Loader 和 Executor 使用。也就是说，Registry 是“手册库索引”，不是执行器。

## 五、Router：只凭 metadata 选择 Skill

Router 的入口在：

```text
runtime/router.py
```

它把 Registry 扫描到的 Skill 组织成候选列表：

```python
candidates = [
    {"name": skill.name, "description": skill.description}
    for skill in skills
]
```

然后调用本地 Ollama：

```python
response = self.model.invoke(prompt)
```

提示词要求模型只返回 JSON：

```json
{"skill": "<skill-name-or-none>", "reason": "<简短原因>"}
```

默认任务里出现了“审查”“学习路线图”“阶段顺序”“边界”“产出物”，这些信号和 `reviewing-roadmap` 的 description 对齐，所以模型应该选择：

```json
{
  "skill": "reviewing-roadmap",
  "reason": "用户要求审查学习路线图的阶段顺序、边界和产出物，与 reviewing-roadmap Skill 的描述完全匹配。"
}
```

这里不要急着读 `SKILL.md` 正文。Router 的边界就是选择 Skill，不负责执行。

## 六、Loader：命中后才读取正文

Loader 的入口在：

```text
runtime/loader.py
```

它接收 Router 选中的 `SkillMetadata`，再读取对应文件：

```python
text = metadata.path.read_text(encoding="utf-8")
body = text[body_start + len("\n---") :].strip()
```

这一步才会拿到 `reviewing-roadmap/SKILL.md` 的正文：

```text
1. 判断路线图是否有清晰目标和目标读者。
2. 检查阶段顺序是否符合认知递进，是否存在重复阶段。
3. 检查每个阶段是否有明确研究问题、实验内容和产出物。
4. 调用 `text_stats` 观察路线图文本规模，辅助判断内容是否过长或过碎。
5. 输出审查摘要，优先指出结构性问题，再给出可执行修改建议。
```

这个分工很重要：Router 只看 metadata，Loader 只在命中后读取正文。这样后续 Skill 变多时，runtime 不需要一开始把所有正文塞进上下文。

## 七、Executor：Skill 声明工具，runtime 负责调用

Executor 的入口在：

```text
runtime/executor.py
```

本实验让 `reviewing-roadmap` 声明一个工具：

```yaml
tools:
  - text_stats
```

Executor 会遍历这个工具列表：

```python
for tool_name in loaded_skill.metadata.tools:
    if tool_name == "text_stats":
        tool_calls.append(
            ToolCall(
                name=tool_name,
                result=count_text_stats(content),
            )
        )
```

真正的工具在：

```text
tools/text_stats.py
```

它只做一件事：统计输入文本规模。

```python
return {
    "characters": len(text),
    "non_empty_lines": len(non_empty_lines),
    "paragraphs": len(paragraphs),
}
```

这个工具很小，但它足以说明一个边界：Skill 不是工具本身。Skill 只是声明“这个流程可以用什么工具”；真正调用工具的是 runtime 的 Executor。

## 八、Trace：把过程变成可观察证据

Trace 的入口在：

```text
runtime/trace.py
```

每个阶段都会调用：

```python
recorder.add_step(...)
```

最终输出 JSON。下面是一次运行的关键结果，路径已改成相对路径，便于阅读：

```json
{
  "task": "请审查这份 Skills 学习路线图，看看阶段顺序、边界和产出物是否合理。",
  "registry_skills": [
    "formatting-commit-message",
    "reviewing-roadmap",
    "writing-weekly-report"
  ],
  "selected_skill": "reviewing-roadmap",
  "route_reason": "用户要求审查学习路线图的阶段顺序、边界和产出物，与 reviewing-roadmap Skill 的描述完全匹配。",
  "loaded_files": [
    "skills/reviewing-roadmap/SKILL.md"
  ],
  "tool_calls": [
    {
      "name": "text_stats",
      "result": {
        "characters": 185,
        "non_empty_lines": 5,
        "paragraphs": 2
      }
    }
  ],
  "status": "completed"
}
```

这份输出可以倒过来读：

- `registry_skills` 说明 Registry 确实发现了 3 个 Skill；
- `selected_skill` 说明 Router 选择了 `reviewing-roadmap`；
- `loaded_files` 说明 Loader 只加载了命中的 `SKILL.md`；
- `tool_calls` 说明 Executor 调用了真实本地工具；
- `status` 说明整条链路完成。

如果只看最终回答，很容易忽略中间过程。Trace 的价值就在于把 runtime 的关键动作留下证据，方便调试、评测和后续治理。

## 九、从输出反查代码

第一次读这个实验，可以按下面顺序看。

先看入口：

```text
run_runtime_demo.py
```

确认任务和内容从哪里来，以及 `SkillRuntime` 如何被创建。

再看主流程：

```text
runtime/app.py
```

这里串起了所有模块。只要看懂 `run()` 里几步，就掌握了整体数据流。

然后按 trace 的字段反查模块：

| Trace 字段 | 对应模块 | 说明 |
| --- | --- | --- |
| `registry_skills` | `runtime/registry.py` | 从 `skills/*/SKILL.md` 解析 metadata |
| `selected_skill` / `route_reason` | `runtime/router.py` | 调 Ollama 返回结构化路由结果 |
| `loaded_files` | `runtime/loader.py` | 命中后读取正文 |
| `tool_calls` | `runtime/executor.py` + `tools/text_stats.py` | 调用 Skill 声明的工具 |
| `steps` | `runtime/trace.py` | 记录每个阶段的可观察信息 |

这也是本实验推荐的阅读方式：不要先钻进某个函数，而是先看 trace，再按 trace 回到代码。

## 十、实验边界

这个 runtime 故意保持克制。

它已经做了：

- 本地 Skill 扫描；
- frontmatter 解析；
- Ollama 路由；
- 命中后加载正文；
- 根据 Skill 声明调用一个真实本地工具；
- 输出结构化 trace。

它还没有做：

- 完整 YAML 解析；
- 目录结构严格校验；
- 多工具参数 schema；
- references 按需加载；
- scripts 安全执行；
- 多轮会话状态；
- 权限确认和审计脱敏。

这些能力不是不重要，而是不应该在阶段 5 一次性做完。阶段 5 先把 runtime 插槽搭出来，后续再逐个增强模块：Registry 可以更严格，Router 可以更稳，Loader 可以支持 references，Executor 可以接入 scripts 或 MCP，Trace 可以变成审计日志。

## 十一、验收清单

完成本实验后，至少应该能确认下面几件事：

```text
1. 能运行 run_runtime_demo.py，并得到 JSON trace。
2. trace.registry_skills 中能看到 3 个 Skill。
3. trace.selected_skill 是 reviewing-roadmap。
4. trace.loaded_files 只包含命中的 reviewing-roadmap/SKILL.md。
5. trace.tool_calls 中出现 text_stats。
6. text_stats 返回 characters、non_empty_lines、paragraphs。
```

如果这些都成立，就说明阶段 5 的核心目标已经达成：一个教学用 Skills runtime 已经把发现、路由、加载、执行和记录拆成了清晰模块，并且整条链路可以运行。

## 小结

这一阶段的重点不是“做一个很强的 Agent”，而是把 Agent Host 里最容易混在一起的职责拆开。

`SKILL.md` 提供任务方法，Registry 建立索引，Router 决定是否启用，Loader 读取正文，Executor 调用工具，Trace 记录过程。

当这条链路清楚以后，后续扩展就不再是往一个脚本里继续堆功能，而是知道应该增强哪个模块。对于学习 Skills 来说，这比一次性写出复杂 runtime 更重要。
