# Skills 系统学习路线图

> **当前定位**：这份 roadmap 只维护 Skills 专题已经形成的公众号稿、实验文稿和配套代码入口。
>
> 原先规划里的未完成阶段暂不继续扩写。后面如果重新启动 Skills 专题，再按新的研究问题单独规划。

Skills 这个专题不是把 `SKILL.md` 当成一段更长的 Prompt，而是把它当成一种 Agent 能力组织方式来理解：

```text
Skill 描述任务方法；
runtime 负责发现、路由、加载和执行；
references / scripts 扩展 Skill 的资料和确定性能力；
MCP 连接外部工具；
LangGraph 管复杂流程、状态和人工确认。
```

目前已经完成的内容，主要围绕这条主线展开。

---

## 当前成果总览

| 序号 | 主题 | 公众号稿 | 实验文稿 / 代码 | 状态 |
| --- | --- | --- | --- | --- |
| 01 | Skills 的定位 | [Skills 不是更长的 Prompt：它在 Agent 里到底负责什么.md](01%20%7C%20Skills%20不是更长的%20Prompt：它在%20Agent%20里到底负责什么.md) | [实验文稿](../../labs/skills/foundations/01%20%7C%20Skills%20的定位：它在%20Agent%20架构中解决什么问题.md) | 已完成 |
| 02 | 最小 `SKILL.md` | [让 Agent 找到正确 Skill：最小 SKILL.md 的两个关键字段.md](02%20%7C%20让%20Agent%20找到正确%20Skill：最小%20SKILL.md%20的两个关键字段.md) | [实验文稿](../../labs/skills/foundations/02%20%7C%20最小%20SKILL.md：一个%20Skill%20如何被发现和使用.md)<br>[代码](../../labs/skills/foundations/examples/stage2-minimal-skills/) | 已完成 |
| 03 | Action / Reference | [Skill 的两种常见设计形态：Action 与 Reference.md](03%20%7C%20Skill%20的两种常见设计形态：Action%20与%20Reference.md) | [代码](../../labs/skills/foundations/examples/stage3-skill-types/) | 已完成 |
| 05 | Skills runtime 分层 | [Agent 能力要跑起来，Skill Runtime 应至少得有这五层.md](05%20%7C%20Agent%20能力要跑起来，Skill%20Runtime%20应至少得有这五层.md) | [实验文稿](../../labs/skills/foundations/05%20%7C%20教学用%20Skills%20runtime：扫描、路由、加载、执行如何分工.md)<br>[代码](../../labs/skills/foundations/examples/stage5-runtime-architecture/) | 已完成 |
| 06 | Instruction-only / Executable | [Instruction-only Skill 与 Executable Skill.md](06%20%7C%20Instruction-only%20Skill%20与%20Executable%20Skill.md) | 暂无独立实验文稿 | 公众号稿完成 |
| 07 | 脚本型 Skill | 暂无独立公众号稿 | [实验文稿](../../labs/skills/foundations/07%20%7C%20脚本型%20Skill：如何安全执行%20scripts%20与校验参数.md)<br>[代码](../../labs/skills/foundations/examples/stage7-script-skill/) | 实验完成 |
| 10 | Skills + MCP | [Skill与MCP放在一起是咋协作的.md](10%20%7C%20Skill与MCP放在一起是咋协作的.md) | [实验文稿](../../labs/skills/foundations/10%20%7C%20Skills%20+%20MCP：如何让%20Skill%20指导%20MCP%20工具调用.md)<br>[代码](../../labs/skills/foundations/examples/stage10-mcp-skill/) | 已完成 |
| 11 | Skills + LangGraph | [从10个节点看Skill、MCP和LangGraph是咋协作的.md](11%20%7C%20从10个节点看Skill、MCP和LangGraph是咋协作的.md) | [实验文稿](../../labs/skills/foundations/11%20%7C%20Skills%20+%20LangGraph：如何把路由、执行和人工确认放进状态图.md)<br>[代码](../../labs/skills/foundations/examples/stage11-langgraph-skills/) | 已完成 |

补充说明：

- `labs/skills/foundations/examples/stage6-reference-boundary/` 已有 reference 路径边界实验样本，但目前没有对应的实验文稿或公众号稿入口，所以不再把它写成一个完整已完成阶段。
- 06 的公众号稿实际主题是 Instruction-only Skill 与 Executable Skill，不是旧 roadmap 里写的 references 按需加载。
- 07 已经有完整实验文稿和代码，但目前没有对应公众号稿。
- 11 的公众号稿以 10 个 LangGraph 节点为主线，旧稿名“Skill、MCP和LangGraph放在一起如何协作”不再作为主要入口。

---

## 建议阅读顺序

如果从公众号稿开始读，建议按下面顺序：

1. [Skills 不是更长的 Prompt：它在 Agent 里到底负责什么.md](01%20%7C%20Skills%20不是更长的%20Prompt：它在%20Agent%20里到底负责什么.md)
2. [让 Agent 找到正确 Skill：最小 SKILL.md 的两个关键字段.md](02%20%7C%20让%20Agent%20找到正确%20Skill：最小%20SKILL.md%20的两个关键字段.md)
3. [Skill 的两种常见设计形态：Action 与 Reference.md](03%20%7C%20Skill%20的两种常见设计形态：Action%20与%20Reference.md)
4. [Agent 能力要跑起来，Skill Runtime 应至少得有这五层.md](05%20%7C%20Agent%20能力要跑起来，Skill%20Runtime%20应至少得有这五层.md)
5. [Instruction-only Skill 与 Executable Skill.md](06%20%7C%20Instruction-only%20Skill%20与%20Executable%20Skill.md)
6. [Skill与MCP放在一起是咋协作的.md](10%20%7C%20Skill与MCP放在一起是咋协作的.md)
7. [从10个节点看Skill、MCP和LangGraph是咋协作的.md](11%20%7C%20从10个节点看Skill、MCP和LangGraph是咋协作的.md)

如果要看完整实验，建议转到：

- [Skills 实战专题 README](../../labs/skills/foundations/README.md)
- [stage2-minimal-skills](../../labs/skills/foundations/examples/stage2-minimal-skills/)
- [stage3-skill-types](../../labs/skills/foundations/examples/stage3-skill-types/)
- [stage5-runtime-architecture](../../labs/skills/foundations/examples/stage5-runtime-architecture/)
- [stage7-script-skill](../../labs/skills/foundations/examples/stage7-script-skill/)
- [stage10-mcp-skill](../../labs/skills/foundations/examples/stage10-mcp-skill/)
- [stage11-langgraph-skills](../../labs/skills/foundations/examples/stage11-langgraph-skills/)

---

## 已完成内容解决了什么

### 01：Skills 的定位

核心问题：

```text
Skills 到底应该放在 Agent 架构中的哪一层？
```

结论：

Skill 不是模型、不是 RAG 知识片段，也不是 MCP 工具。它更像一份任务能力包：描述某类任务什么时候触发、按什么流程执行、需要哪些资料或工具、结果如何验收。

### 02：最小 `SKILL.md`

核心问题：

```text
一个最小 SKILL.md 至少要写清哪些内容，才能被发现和使用？
```

结论：

`name` 和 `description` 是 Skill 被发现和路由的入口；正文负责承载执行步骤、输入输出、约束和示例。最小实验已经验证了扫描、候选选择和正文加载的基本链路。

### 03：Action Skill 与 Reference Skill

核心问题：

```text
Action 和 Reference 分别适合承载什么内容？
```

结论：

Action 偏任务步骤，回答“怎么做”；Reference 偏规则、标准和背景知识，回答“按什么判断”。它们是设计形态，不是必须写进 frontmatter 的官方类型字段。

### 05：Skills runtime 分层

核心问题：

```text
一个支持 Skills 的最小 runtime 应该如何拆分？
```

结论：

教学用 runtime 至少可以拆成五层：

```text
Registry -> Router -> Loader -> Executor -> Trace
```

Registry 扫描 Skill metadata，Router 根据 `name` / `description` 选择 Skill，Loader 命中后读取 `SKILL.md` 正文，Executor 执行动作，Trace 记录整条链路。

### 06：Instruction-only 与 Executable

核心问题：

```text
只写说明的 Skill，和带脚本 / 工具 / workflow 的 Skill，有什么区别？
```

结论：

Instruction-only Skill 主要依赖模型理解和执行；Executable Skill 会把某些动作交给脚本、API、MCP tool 或 workflow，适合对格式、稳定性和可重复性要求更高的任务。

### 07：脚本型 Skill

核心问题：

```text
如果 Skill 想声明自己的本地脚本，runtime 应该如何安全执行？
```

结论：

Skill 可以声明脚本，但不能直接执行脚本。真正执行脚本的是 runtime，并且要经过白名单、路径边界、参数 schema、超时控制和 trace 记录。

### 10：Skills + MCP

核心问题：

```text
Skill 如何指导模型使用 MCP Server 暴露的工具？
```

结论：

MCP 提供外部能力，Skill 描述这些能力应该在什么任务里使用、参数从哪里来、结果如何处理。Host 负责发现 MCP Tool、把 Tool schema 交给模型，并执行模型提出的 Tool Call。

### 11：Skills + LangGraph

核心问题：

```text
Skill 路由、MCP 工具调用和人工确认如何进入 LangGraph 状态图？
```

结论：

LangGraph 负责把任务拆成节点，并把中间结果放进 State。Skill 提供任务方法，MCP 提供外部工具，模型生成调用计划，Host 执行动作，checkpoint 支持暂停和恢复，human approval 控制真实副作用。

---

## 冻结的后续方向

下面这些方向曾经在旧 roadmap 中出现过，但目前没有继续更新计划。这里仅保留名称，避免路线图看起来像仍在维护的详细待办。

| 阶段 | 方向 | 当前处理 |
| --- | --- | --- |
| 08 | 多 Skill 路由：候选召回、误触发和规模化筛选 | 暂不更新 |
| 09 | Skill 组合：复合任务拆解和中间结果传递 | 暂不更新 |
| 12 | Skill 评测：触发、误触发和输出质量回归 | 暂不更新 |
| 13 | Skill 工程治理：版本、打包、日志与安全审查 | 暂不更新 |
| 14 | 综合实战：AI 数字运营助理端到端闭环 | 暂不更新 |

如果后续重新启动这些方向，建议不要继续沿用旧编号硬补，而是先确认新的研究问题、已有代码基础和目标读者，再单独开新的实验或公众号稿。

---

## 维护规则

- 本文件只记录已经存在的公众号稿、实验文稿和可打开的代码入口。
- 新增公众号稿后，优先补到“当前成果总览”和“建议阅读顺序”。
- 新增实验文稿或代码后，同步补到 `labs/skills/foundations/README.md`、根 `README.md` 和本文件。
- 未形成文章或明确入口的样本代码，可以在补充说明里标注，但不直接写成完整阶段。
- 暂不继续维护未完成阶段的详细实验计划。
