# Skills 系统学习路线图

> **主线定位**：把 Skills 作为一种 Agent 能力组织模式来学习。
>
> 当前基础实验已经覆盖了 Skills 的定位、最小 `SKILL.md`、Action / Reference 设计形态，以及一个教学用 runtime 中扫描、路由、加载、执行和记录的基本分工。后续路线不再重复拆解这些基础环节，而是聚焦仍然值得实验验证的能力：资源边界、脚本执行、多 Skill 规模化、MCP / LangGraph 协同、评测与治理。

**可用环境**：熟悉 Python；本地可使用 Ollama（qwen3-coder:30b）。它们是实验实现选项，不限定 Skills 学习路线。
**前置知识**：LangChain、LangGraph、RAG、MCP（已学完）
**产出形式**：每个新增阶段至少 1 篇实验文章；当阶段需要验证运行机制时，再补充 1 份可运行代码。

---

## 贯穿案例：养成一个 AI 数字运营助理

把整个学习过程比作带一个新员工从入职到独当一面：

- **Skills** = 工作手册 / SOP，告诉 Agent 遇到某类任务时该按什么方法做。
- **RAG** = 公司知识库 / 制度文档，Agent 遇到不确定事实时去查。
- **MCP** = 办公系统权限和工具接口，Agent 用它连接文件、数据库、邮件、日历等外部系统。
- **LangGraph** = 工作流程图，让复杂任务按状态、分支和人工确认一步步推进。

这个案例从简单办公任务开始，逐步扩展到会议纪要、周报生成、文档处理、合同初筛、知识库查询、MCP 工具调用和审批流程编排。每个阶段都只回答一个清晰问题，避免为了凑完整框架而重复实验。

---

## 当前已经解决的问题

以下内容已经由现有实验覆盖，不再作为独立后续阶段规划：

| 内容 | 覆盖成果 | 结论 |
| --- | --- | --- |
| Skills 在 Agent 架构中的定位 | `labs/skills/foundations/01` | 已完成 |
| 最小 `SKILL.md`、`name` / `description` 与发现机制 | `labs/skills/foundations/02` | 已完成 |
| Action Skill / Reference Skill 的设计形态 | `drafts/skills/03` 与 `examples/stage3-skill-types/` | 已完成 |
| 渐进式披露的基本思想 | `labs/skills/foundations/02`、`labs/skills/foundations/05` | 已覆盖，不再单独做 |
| Skill 扫描、frontmatter 解析、Registry | `labs/skills/foundations/05` | 已覆盖，严格校验放入后续治理 |
| 基于 `name` / `description` 的路由 | `labs/skills/foundations/05` | 已覆盖 |
| 命中后读取 `SKILL.md` 正文 | `labs/skills/foundations/05` | 已覆盖 |
| Runtime 的 Registry / Router / Loader / Executor / Trace 分工 | `labs/skills/foundations/05` | 已完成 |

因此，原路线图里的“渐进式披露”“扫描器”“第一层路由”“第二层加载”等阶段不再保留为独立阶段。

---

## 后续阶段总览

| 阶段 | 主题 | 难度 | 价值 |
| --- | --- | --- | --- |
| 06 | references 按需加载：如何守住 Skill 内部资源边界 | ★★★ | 补齐阶段 05 未做的资源加载与路径安全 |
| 07 | 脚本型 Skill：如何安全执行 scripts 与校验参数 | ★★★★ | 验证 Skill 如何声明确定性本地能力 |
| 08 | 多 Skill 路由：如何在 Skill 变多后筛选候选项 | ★★★★ | 解决规模化后的召回、误触发和候选压缩 |
| 09 | Skill 组合：复合任务如何拆解并顺序传递结果 | ★★★★ | 从单 Skill 执行进入多能力协作 |
| 10 | Skills + MCP：如何用 Skill 约束外部工具调用 | ★★★★ | 连接已有 MCP 知识，验证权限与动作边界 |
| 11 | Skills + LangGraph：如何把路由、执行和人工确认放进状态图 | ★★★★★ | 连接已有 LangGraph 知识，处理复杂流程 |
| 12 | Skill 评测：如何验证触发、误触发与输出质量 | ★★★★ | 把 description 和正文修改变成可回归工程资产 |
| 13 | Skill 工程治理：如何管理版本、打包、日志与安全审查 | ★★★★ | 把 Skill 从提示词文件推进到可维护软件工件 |
| 14 | 综合实战：如何串联出一个 AI 数字运营助理 | ★★★★★ | 汇总前面能力，做端到端可演示闭环 |

---

## 阶段 01：认识 Skills：Agent 能力包的定位

**状态**：已完成

对应成果：

- `labs/skills/foundations/01 | Skills 的定位：它在 Agent 架构中解决什么问题.md`

**核心问题**

Skills 到底应该放在 Agent 架构的哪一层？

**结论**

Skill 不是模型、不是 RAG 知识片段，也不是 MCP 工具。它更像一层“能力包”：描述某类任务什么时候触发、按什么流程执行、需要调用哪些资料或工具、结果如何验收。

---

## 阶段 02：最小 `SKILL.md`：一个 Skill 如何被发现和使用

**状态**：已完成

对应成果：

- `labs/skills/foundations/02 | 最小 SKILL.md：一个 Skill 如何被发现和使用.md`
- `drafts/skills/02 | 让 Agent 找到正确 Skill：最小 SKILL.md 的两个关键字段.md`
- `labs/skills/foundations/examples/stage2-minimal-skills/`

**核心问题**

一个最小 `SKILL.md` 至少要写清哪些内容，才能被发现和使用？

**结论**

`name` 和 `description` 是 Skill 发现的核心入口；正文负责承载执行步骤、输入输出、约束和示例。这个阶段已经覆盖了最小扫描与路由验证，不再拆出单独扫描器阶段。

---

## 阶段 03：Action Skill 与 Reference Skill

**状态**：已完成

对应成果：

- `drafts/skills/03 | Skill 的两种常见设计形态：Action 与 Reference.md`
- `labs/skills/foundations/examples/stage3-skill-types/`

**核心问题**

Action 与 Reference 分别适合承载什么内容，如何组合？

**结论**

Reference Skill 适合放长期规则、判断标准和背景知识；Action Skill 适合放任务步骤、输入输出和验收要求。两者是设计形态，不是必须写进 frontmatter 的官方类型字段。

---

## 阶段 05：教学用 Skills runtime：扫描、路由、加载、执行如何分工

**状态**：已完成

对应成果：

- `labs/skills/foundations/05 | 教学用 Skills runtime：扫描、路由、加载、执行如何分工.md`
- `drafts/skills/05 | Agent 能力要跑起来，Skill Runtime 应至少得有这五层.md`
- `labs/skills/foundations/examples/stage5-runtime-architecture/`

**核心问题**

一个支持 Skills 的最小 runtime 应该如何拆分扫描、路由、加载、执行和记录？

**结论**

阶段 05 已经实现了教学用 runtime 骨架：Registry 扫描 Skill metadata，Router 根据 `name` / `description` 选择 Skill，Loader 命中后读取 `SKILL.md` 正文，Executor 调用声明工具，Trace 记录整条链路。

**边界**

阶段 05 还没有做完整 YAML 解析、严格目录校验、references 按需加载、scripts 安全执行、多 Skill 规模化路由、评测和治理。这些才是后续路线图真正需要继续实验的内容。

---

## 阶段 06：references 按需加载：如何守住 Skill 内部资源边界

**状态**：待研究

**为什么值得做**

阶段 05 已经读取了命中的 `SKILL.md` 正文，但还没有处理 `references/`。而 references 的关键不只是“多读一个文件”，还包括路径边界、跨 Skill 访问限制和对抗输入验证。

**学习目标**

- 实现按需读取 `references/` 目录。
- 理解 references 与 RAG 的差异：references 是 Skill 内部资源，RAG 是外部知识检索。
- 建立基本路径安全边界，防止路径穿越和跨 Skill 读取。

**核心概念**

- `references/`：保存长规范、模板、示例和检查清单。
- `read_reference(skill_name: str, file: str)`：只允许读取当前 Skill 内部的 reference 文件。
- 路径归一化：拒绝 `../`、绝对路径、符号链接逃逸和跨 Skill 访问。

**实验内容**

- 给 `reviewing-roadmap` 添加 `references/roadmap_review_checklist.md`。
- 让 runtime 在审查路线图时按需读取该 reference。
- 设计至少 2 个非法读取请求，验证会被拒绝。

**产出物**

- `stage6_reference_loading/`：带 references 的 Skill 样本和 runtime 增强代码。
- 一篇实验文章：说明 references 的加载边界、合法路径、非法路径和 trace 证据。

---

## 阶段 07：脚本型 Skill：如何安全执行 scripts 与校验参数

**状态**：待研究

**为什么值得做**

Skill 不应该只是一段提示词。对于可确定执行的任务，例如提取待办、整理标题、转换格式，脚本比模型更稳定。但脚本执行也会引入路径、参数、超时和权限风险。

**学习目标**

- 让 Skill 声明可调用的本地脚本。
- 明确脚本代码不进入模型上下文，runtime 只暴露受控调用接口。
- 建立脚本白名单、参数 schema、路径边界和超时控制。

**核心概念**

- `scripts/`：存放 Skill 私有辅助脚本。
- 脚本声明：Skill 可以说明可用脚本，但真正执行由 runtime 控制。
- 参数校验：模型不能把任意字符串直接拼成 shell 命令。
- 执行 trace：记录脚本名、参数摘要、退出码、关键输出和拒绝原因。

**实验内容**

- 编写一个文档处理 Skill，例如从 Markdown 中提取标题、摘要和待办项。
- 用 `scripts/extract_tasks.py` 完成确定性提取。
- 测试合法调用、未知脚本调用、非法路径参数和超时场景。

**产出物**

- `stage7_script_skill/`：完整脚本型 Skill 和安全执行 demo。
- 一篇实验文章：解释 Skill、脚本、runtime 权限边界如何分工。

---

## 阶段 08：多 Skill 路由：如何在 Skill 变多后筛选候选项

**状态**：待研究

**为什么值得做**

阶段 05 的 Router 可以处理少量 Skill，但当 Skill 数量变多时，把所有 `name` / `description` 都塞给模型会浪费上下文，也更容易误触发。这个阶段关注规模化后的候选筛选，而不是重复“只凭 description 选择一个 Skill”。

**学习目标**

- 为多 Skill 场景建立候选筛选机制。
- 对比关键词召回、语义召回和模型最终选择的边界。
- 记录漏召回、误召回和多候选冲突案例。

**核心概念**

- Top-K 候选：先压缩候选集，再让模型做最终选择。
- 关键词召回：简单、可解释，容易漏掉语义改写。
- 语义召回：能处理表达差异，但需要评测误召回。
- 路由评测集：正例、反例、多候选和模糊请求都要覆盖。

**实验内容**

- 准备 10 个以上 Skill metadata。
- 实现关键词召回和语义召回两个候选筛选器。
- 用同一组请求比较全量元数据路由、关键词 Top-K 和语义 Top-K。

**产出物**

- `stage8_multi_skill_routing/`：多 Skill 路由实验代码。
- 一份路由效果报告：包含命中率、漏召回、误召回和典型失败样例。

---

## 阶段 09：Skill 组合：复合任务如何拆解并顺序传递结果

**状态**：待研究

**为什么值得做**

真实任务经常不是命中一本手册就结束，而是需要连续调用多个 Skill。这个阶段验证最小顺序编排，不急着引入 LangGraph，先把“多 Skill 协作的数据怎么传”讲清楚。

**学习目标**

- 实现一个任务触发多个 Skill。
- 理解任务拆解、中间结果传递和顺序编排。
- 区分简单顺序编排和后续 LangGraph 状态机的边界。

**核心概念**

- 单 Skill 任务 vs 复合任务。
- 顺序调用：A 的输出成为 B 的输入。
- 中间结果：必须结构化记录，不能只依赖模型隐式记忆。

**实验内容**

- 设计复合任务：“整理会议纪要 → 提取待办 → 按周报格式生成汇总”。
- 依次调用会议纪要 Skill、待办提取 Skill、周报 Skill。
- 记录每一步输入、输出、中间状态和失败处理。

**产出物**

- `stage9_skill_orchestration/`：最小顺序编排 demo。
- 一篇实验文章：说明复合任务中 Skill 边界、中间结果和 trace 设计。

---

## 阶段 10：Skills + MCP：如何用 Skill 约束外部工具调用

**状态**：待研究

**为什么值得做**

MCP 负责暴露外部工具，Skill 负责规定什么时候用、按什么顺序用、参数从哪里来、哪些动作必须确认。这个阶段要验证二者的职责边界，而不是重新讲 MCP 基础。

**学习目标**

- 理解 Skill 与 MCP 的协同方式。
- 用 Skill 指导模型调用 MCP 工具。
- 明确工具权限、参数边界和人工确认点。

**核心概念**

- MCP 是外部能力接口；Skill 是使用这些接口的操作手册。
- Action Skill 可以规定工具调用顺序、参数来源和结果处理方式。
- 危险动作必须经过 runtime 或 human-in-the-loop 约束。

**实验内容**

- 复用 MCP 专题中的文件系统或数据库 MCP Server。
- 编写一个 Skill：查询数据 → 生成报告 → 写入文件。
- 增加一个危险操作案例，例如覆盖已有文件前必须确认。

**产出物**

- `stage10_mcp_skill/`：Skill 指导 MCP 调用的实验代码。
- 一篇实验文章：说明 Skill、runtime、MCP Server 各自负责什么。

---

## 阶段 11：Skills + LangGraph：如何把路由、执行和人工确认放进状态图

**状态**：待研究

**为什么值得做**

简单顺序编排可以用普通 Python 完成；当任务出现分支、恢复、人工确认和多轮状态时，LangGraph 才有必要。这个阶段验证 Skills runtime 如何进入状态图，而不是为了用 LangGraph 而用。

**学习目标**

- 把 Skill 路由、加载和执行放入 LangGraph 状态图。
- 引入状态、分支、checkpoint 和 human-in-the-loop。
- 理解什么时候该用简单编排器，什么时候该用 LangGraph。

**核心概念**

- 路由节点：选择候选 Skill。
- 加载节点：读取正文和 references。
- 执行节点：调用脚本或 MCP 工具。
- 确认节点：发送邮件、写入文件、覆盖数据前暂停。
- Checkpoint：保存中间状态，支持恢复。

**实验内容**

- 将阶段 09 的组合编排和阶段 10 的 MCP 工具调用改造成 LangGraph 状态图。
- 至少包含路由、加载、执行、人工确认 4 类节点。
- 用一次“生成报告并确认写入”的任务验证流程。

**产出物**

- `stage11_langgraph_skills/`：LangGraph + Skills runtime demo。
- 状态图结构示意图和 human-in-the-loop 运行记录。

---

## 阶段 12：Skill 评测：如何验证触发、误触发与输出质量

**状态**：待研究

**为什么值得做**

没有评测，description 和正文的修改只能靠感觉。这个阶段把路由、拒触发、改写鲁棒性和输出验收变成可回归资产。

**学习目标**

- 为 Skill 建立可回归的评测集。
- 测试触发、拒触发、改写鲁棒性和输出质量。
- 让 description 和正文修改有可观察反馈。

**核心概念**

- 正例：应该触发某 Skill 的请求。
- 反例：不应该触发该 Skill 的请求。
- 改写样本：同一意图的不同表达。
- 输出验收：格式、字段、约束、关键内容是否满足要求。

**实验内容**

- 为 3–5 个 Skill 编写触发测试用例。
- 实现一个最小 eval runner。
- 修改某个 Skill 的 description，观察触发结果如何变化。

**产出物**

- `stage12_skill_evals/`：评测用例和 eval runner。
- 一份评测报告：包含失败样例、修正建议和回归结果。

---

## 阶段 13：Skill 工程治理：如何管理版本、打包、日志与安全审查

**状态**：待研究

**为什么值得做**

当 Skill 要在团队里复用时，它就不只是 Markdown 文件，而是需要版本、打包、审查、日志和安全边界的软件工件。

**学习目标**

- 建立 Skill 生命周期管理方法。
- 处理版本、打包、分发、日志和安全审查。
- 明确团队共享 Skill 的风险边界。

**核心概念**

- 版本管理：记录 description、正文、references、scripts 的变化。
- 打包分发：压缩 Skill 文件夹，迁移到其他项目。
- 运行日志：记录命中、加载、脚本调用、MCP 调用、拒绝原因。
- 安全审查：来源、脚本、路径、网络请求、危险工具、敏感数据。

**实验内容**

- 为已有 Skill 增加版本字段或变更记录。
- 编写 Skill 打包脚本。
- 用安全清单审查一个脚本型 Skill。
- 设计 3 个对抗输入：路径穿越、未知脚本、诱导危险操作。

**产出物**

- `stage13_skill_governance/`：打包、日志和审查 demo。
- `security_checklist.md`：Skill 安全审查清单。
- 一份 Skill 审查报告。

---

## 阶段 14：综合实战：AI 数字运营助理上线

**状态**：待研究

**为什么值得做**

前面的阶段分别验证了资源加载、脚本、路由、组合、MCP、LangGraph、评测和治理。最后需要一个端到端案例，检验这些能力能否组合成一个可演示、可复现、可扩展的工作流。

**学习目标**

- 把前面阶段的能力整合成一个完整闭环系统。
- 验证 Skills runtime 与 RAG、MCP、LangGraph 的协同。
- 形成可演示、可复现、可扩展的综合实验。

**实验内容**

设计并实现一个端到端案例：

> “帮我处理一份合同 PDF：提取关键条款 → 结合公司知识库判断是否存在风险条款 → 查询历史合同或审批记录 → 按公司格式生成初筛报告 → 人工确认后写入指定位置或准备邮件草稿。”

注意：该案例定位为“内部流程初筛”，不输出法律结论。

该案例需要用到：

- 阶段 07 的脚本型 Skill。
- 阶段 08 的多 Skill 路由。
- 阶段 10 的 Skills + MCP 协同。
- 阶段 11 的 LangGraph 流程编排。
- 阶段 12 的评测。
- 阶段 13 的日志与安全审查。

**产出物**

- 一套完整可运行的教学版迷你 Skills runtime。
- 一篇总结性实验文章。
- 一份后续扩展计划：更多 MCP Server、更多 Skill 库、团队共享与权限治理。

---

## 长期注意事项

- 本路线图学习的是 Skills 作为 Agent 能力组织模式的设计思想；Python + Ollama 是可用实验环境，不等同于路线图的强制技术栈。
- 教学用 runtime 是为了拆解和验证扫描、路由、加载、执行、评测、治理等机制，不要把本地实现误认为官方唯一规范。
- 每个阶段都要保留最小可复现证据：输入、命令、关键输出、失败样例、结论和边界。
- `name` 与 `description` 是 Skill 发现和路由的核心接口，每次修改都要同步更新触发正例、反例和误触发记录。
- 不要把 Skill 写成大 Prompt：Skill 描述任务流程，RAG 管事实知识，MCP / tools 管外部动作，LangGraph 管复杂状态流。
- 安全约束从资源加载阶段就开始验证，包括路径边界、脚本白名单、参数校验、危险动作确认和敏感数据处理。
- 每个阶段只回答一个核心研究问题，避免提前混入后续阶段能力。
- 失败样例要沉淀为评测资产，用于后续回归测试和 description 调优。

---

## 后续落地提醒

- 专题入口已落地到 `labs/skills/foundations/README.md`；后续阶段继续在该 README 中同步状态与入口。
- 每完成一个阶段，要同步更新专题 README、根 README 以及本 roadmap 的状态。
- 涉及代码执行的实验，读者命令统一使用 `uv run ...`。
- 涉及安全边界的实验，不能只演示合法路径，至少要设计 1–3 个对抗输入并说明在哪一层被拒绝。
