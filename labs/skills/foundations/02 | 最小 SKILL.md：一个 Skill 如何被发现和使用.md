# 02 | 最小 SKILL.md：一个 Skill 如何被发现和使用

写 Skill 最容易犯的错，是把它写成一段更长的提示词。

比如只写一句：

```text
你是一个擅长写周报的助手，请根据材料生成结构清晰的周报。
```

这句话能帮模型完成一次任务，但它还不是一个合格的 Skill。因为真实运行时里，Skill 往往不是一上来就完整塞进上下文。系统通常要先看 `name` 和 `description`，判断哪份 Skill 可能适合当前请求；命中以后，才读取完整 `SKILL.md` 正文。

所以，一个最小可用的 `SKILL.md` 至少要经得住两层检查：

- 发现层：只看 `name` 和 `description`，模型能不能选中正确 Skill；
- 执行层：读完正文，模型能不能知道输入、步骤、输出和边界。

本实验会接入本地 Ollama 中的 `qwen3-coder:30b`，让模型根据 3 个 Skill 的 metadata 做一次最小路由。这样能更接近真实环境：不是我们肉眼觉得 `description` 写得清楚，而是把它交给模型实际选一次。

## 一、实验目标与配套文件

实验目标是写出 3 个只有 `SKILL.md` 的纯指令型 Skill，并用本地模型验证它们是否能被正确发现。

配套文件位于：

```text
labs/skills/foundations/examples/stage2-minimal-skills/
```

目录结构如下：

```text
stage2-minimal-skills/
├── writing-weekly-report/
│   └── SKILL.md
├── formatting-commit-message/
│   └── SKILL.md
├── reviewing-roadmap/
│   └── SKILL.md
└── skill_router_with_ollama.py
```

这 3 个 Skill 分别覆盖三类常见任务：

| Skill | 任务类型 | 观察重点 |
| --- | --- | --- |
| `writing-weekly-report` | 把散乱材料整理成周报 | 如何说明输入材料和防编造边界 |
| `formatting-commit-message` | 把变更说明整理成提交信息 | 如何把格式要求拆成步骤 |
| `reviewing-roadmap` | 审查学习路线图或研究计划 | 如何避免泛泛提建议 |

`skill_router_with_ollama.py` 是本次实验的迷你 Skill Agent。它启动后进入交互式输入框，读者可以连续输入任务，观察 Agent 如何路由 Skill，并在命中后加载正文。

核心动作仍然只有三件事：

1. 扫描每个 `SKILL.md` 的 frontmatter；
2. 把 `name` 和 `description` 交给 `qwen3-coder:30b` 判断；
3. 模型命中 Skill 后，再读取对应正文的前几行作为“已加载”证据。

这个脚本还不是完整 runtime。它没有语义索引，没有多轮规划，也不会执行脚本。它只验证阶段二最核心的问题：`description` 是否足够支持发现。

## 二、运行前提

本实验使用项目已有依赖 `langchain-ollama`，并通过本地 Ollama 调用模型。

先确认 Ollama 服务已启动，并且本机已经有 `qwen3-coder:30b`：

```bash
ollama list
```

先进入实验目录：

```bash
cd labs/skills/foundations/examples/stage2-minimal-skills
```

启动迷你 Agent：

```bash
uv run python skill_router_with_ollama.py
```

进入后可以直接输入任务：

```text
task> 根据这些会议记录和任务更新，整理一份本周运营周报。
```

如果你的模型名不同，可以用参数覆盖：

```bash
uv run python skill_router_with_ollama.py --model your-local-model
```

## 三、最小结构：metadata 加正文

最小 `SKILL.md` 可以先拆成两部分：

```text
SKILL.md
├── YAML frontmatter：给系统发现 Skill 用
└── Markdown body：给 Agent 执行任务用
```

frontmatter 是文件开头被 `---` 包起来的 YAML 元数据。这个实验只读取两个字段：

```yaml
---
name: writing-weekly-report
description: 当用户要求把周度工作材料、会议记录、任务更新、指标快照、阻塞风险或零散进展整理成结构化周报时，使用这个 Skill。输出必须基于输入事实，标注不确定信息，不能编造进展、指标、负责人或日期。
---
```

`name` 是稳定标识。它应该短、清楚、可读，让人和系统都能准确指向这个 Skill。

`description` 是发现入口。它不能只写“擅长写周报”，而要说明两件事：这个 Skill 处理什么任务，以及什么样的用户请求应该触发它。

正文是执行说明。它在 Skill 命中后才发挥作用，负责告诉 Agent：输入有哪些，先做什么后做什么，最后输出什么，哪些东西不能乱补。

这个分工很关键。`description` 决定“要不要读这份 Skill”，正文决定“读完以后怎么做”。把完整流程塞进 `description` 会让发现阶段变重；只在正文里写得很完整、但 `description` 含糊，又会导致系统根本不容易选中它。

## 四、迷你 Agent 怎么工作

脚本入口是：

```text
labs/skills/foundations/examples/stage2-minimal-skills/skill_router_with_ollama.py
```

启动后，脚本先扫描当前目录下一层的 `SKILL.md`：

```python
for skill_file in sorted(SKILLS_ROOT.glob("*/SKILL.md")):
    skills.append(parse_frontmatter(skill_file))
```

这里有意只读取 frontmatter，不读取正文。因为发现阶段真正能用的通常就是 `name` 和 `description`。

进入 `task>` 后，用户输入的任务会进入模型路由。脚本把候选 Skill 组织成 JSON，交给模型选择：

```python
candidates = [
    {"name": skill.name, "description": skill.description} for skill in skills
]
```

提示词要求模型只返回一个 JSON：

```json
{"skill": "<skill-name-or-none>", "reason": "<short reason>"}
```

如果没有任何 Skill 匹配，就返回 `none`。这个反向能力很重要：一个好的 Skill 系统不只是会命中，还要知道什么时候不该命中。

只有当模型选中某个 Skill 时，脚本才读取正文的前几行：

```python
if result.skill != "none":
    skill = skills_by_name[result.skill]
    for line in body_preview(skill, DEFAULT_BODY_PREVIEW_LINES):
        print(f"  {line}")
```

这一步模拟了“先发现，再加载”的流程。虽然脚本很小，但它已经能把 `description` 的质量暴露出来：写得太泛，会误触发；写得太窄，会漏掉真实请求。

### 这个实验和真实 App 的关系

这个脚本不是在复刻 Codex 或 Claude App 的内部实现，但它抓住了 Skills 路由里很重要的共同原则：

```text
先暴露少量 metadata
→ 根据用户请求判断是否相关
→ 命中后再加载更完整的说明或资源
```

真实产品通常会更复杂，可能混合规则触发、模型判断、关键词或向量召回、权限过滤、文件类型感知和上下文缓存。比如用户显式点名某个 Skill 时，可以直接触发；Skill 很多时，也可能先召回少量候选，再交给模型判断。

但核心思想是一致的：不要一开始把所有 Skill 正文都塞进上下文，而是先用轻量描述决定“要不要加载”。所以本实验的价值不在于还原某个产品的完整路由系统，而是用最小代码看清 `description` 为什么会影响 Skill 能否被发现。

## 五、三个 Skill 的设计

### 1. 周报生成

文件：

```text
labs/skills/foundations/examples/stage2-minimal-skills/writing-weekly-report/SKILL.md
```

它要处理的是把会议记录、任务进展、指标快照和风险信息整理成周报。

一个可能触发它的请求是：

```text
请根据这些会议记录和任务更新，整理一份本周运营周报。
```

但下面这种请求不应该直接命中它：

```text
查询公司差旅报销制度。
```

后者需要的是事实检索，不是周报整理。这个区别必须在 `description` 里露出来，否则 Skill 很容易变成一个“凡是办公任务都能用”的模糊提示词。

这个 Skill 的 `description` 包含三类信号：

- 任务目标：结构化周报；
- 输入形态：周度工作材料、会议记录、任务更新、指标快照、阻塞风险、零散进展；
- 边界要求：基于输入事实、标注不确定信息、不能编造进展。

正文则说明输入、处理步骤、默认输出结构和约束。尤其是约束部分明确要求：不能编造指标、负责人、日期和结果；信息不足时放到 `Needs Confirmation`。

### 2. Commit Message 格式化

文件：

```text
labs/skills/foundations/examples/stage2-minimal-skills/formatting-commit-message/SKILL.md
```

典型请求可能是：

```text
把 update stuff 改成规范一点的 commit message。
```

如果只是 Prompt，很容易写成“请生成一个清晰规范的提交信息”。问题是，“清晰规范”并不能执行。Agent 还需要知道：先判断变更意图，再选择类型，要不要 scope，body 什么时候需要，输入里如果混了无关改动该怎么办。

这个 Skill 的 `description` 补充了输入来源：

- 变更摘要；
- diff 摘要；
- 暂存文件列表；
- 粗糙提交说明。

正文里最关键的是类型选择和输出结构：

```text
type(scope): concise subject

Optional body explaining why the change was needed.
```

它没有假装自己能读取本地 Git 状态，也没有说可以直接执行 commit。它只负责把“提交信息怎么写”整理成可执行方法。

### 3. Roadmap 审查

文件：

```text
labs/skills/foundations/examples/stage2-minimal-skills/reviewing-roadmap/SKILL.md
```

典型请求是：

```text
帮我审查这份 RAG 学习路线图，看看阶段顺序和产出是否合理。
```

这类任务最容易被写成泛泛的“请提出专业建议”。但路线图审查真正要看的是结构：读者是谁，最终目标是什么，前置知识是否合理，阶段顺序是否从简单到复杂，每个阶段有没有明确研究问题和具体产出。

这个 Skill 的 `description` 放了几个相邻表达：学习路线图、研究计划、内容路线图、分阶段技术学习计划。这不是为了堆关键词，而是为了覆盖用户真实说法。

正文第一步是识别路线图的受众、最终目标和前置知识。没有这些信息，就无法判断某个阶段到底是太早、太晚，还是根本不该放在这条路线里。

## 六、实验输出与观察

启动迷你 Agent：

```bash
uv run python skill_router_with_ollama.py
```

启动后会进入交互框：

```text
Mini Skill Agent 已启动。
直接输入任务，Agent 会先路由 Skill，再加载正文 preview。
按 Ctrl+C 或 Ctrl+D 结束。

task>
```

### 1. 输入一个应该命中的任务

输入：

```text
task> 根据这些会议记录和任务更新，整理一份本周运营周报。
```

输出的关键部分如下：

```text
用户任务：根据这些会议记录和任务更新，整理一份本周运营周报。
路由结果：writing-weekly-report
路由原因：用户明确要求根据会议记录和任务更新整理结构化周报，这与 writing-weekly-report skill 的描述完全匹配。
加载结果：已加载 writing-weekly-report 的正文 preview

  # 周报生成

  使用这个 Skill，把零散的周度工作材料整理成一份清晰的周报。
```

这一步说明：普通任务会进入模型路由；模型只看 `name` 和 `description` 选中 `writing-weekly-report`；命中后，脚本才读取正文 preview。

### 2. 输入一个不应该命中的任务

输入：

```text
task> 给我解释 Git rebase 的原理。
```

输出的关键部分如下：

```text
用户任务：给我解释 Git rebase 的原理。
路由结果：none
路由原因：用户请求解释 Git rebase 的原理，这与三个可用 Skill 的功能描述均不匹配。
加载结果：没有匹配 Skill，保持未加载状态。
```

这一步验证反向边界：`formatting-commit-message` 的描述里虽然出现了 Git 和 commit message，但它不应该泛化到所有 Git 知识解释任务。模型返回 `none`，说明 `description` 没有写得太宽。

## 七、结论

这次实验把最小 `SKILL.md` 拆成了一个可观察流程：

```text
用户请求
  -> 读取所有 Skill 的 name / description
  -> qwen3-coder:30b 选择 Skill 或返回 none
  -> 命中后读取对应 SKILL.md 正文 preview
```

这个流程很小，但已经比纯手工判断更接近真实环境。它让我们看到：`description` 不是装饰字段，而是 Skill 能否被发现的入口；正文不是越长越好，而是要在命中以后提供可执行方法。

只写“你是一个擅长某任务的助手”，通常还停留在 Prompt。写清触发条件、输入形态、执行步骤、输出结构和边界，并能通过本地模型的正反向路由检查，才开始接近一个可复用的 Skill。
