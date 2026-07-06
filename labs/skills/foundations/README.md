# Skills 实战专题

这个专题把 Skills 当作一种 Agent 能力组织模式来学习：它负责沉淀一类任务的触发条件、执行流程、参考资料和可执行脚本，让模型、工具、RAG、MCP 和 LangGraph 能按稳定的方法协作。

本系列会从最小的 `SKILL.md` 开始，逐步扩展到渐进式披露、Skill 路由、脚本执行、RAG 检索、MCP 工具约束、LangGraph 流程编排和工程治理。贯穿案例是一个“AI 数字运营助理”：先学会写周报和整理会议纪要，再学会查询知识库、调用办公系统，并在复杂任务中保留人工确认。

## 你会学到什么

- Skills 在 Agent 架构中的位置，以及它和 Prompt、Tools、RAG、MCP、LangGraph 的边界。
- 一个 `SKILL.md` 应该如何描述触发条件、执行步骤、参考资料和脚本能力。
- 为什么 Skills 需要渐进式披露，而不是把所有流程和资料一次性塞进上下文。
- 如何设计一个教学用本地 runtime，观察 Skill 扫描、路由、加载、执行和记录过程。
- 如何让 Skills 与已有的 RAG、MCP、LangGraph 知识连接起来，形成可复用、可评测、可治理的 Agent 能力。

## 适合读者

- 已经理解 Prompt、Tools、RAG、MCP 或 LangGraph，想进一步组织 Agent 工作流的开发者。
- 想把团队 SOP、写作规范、审查流程或办公自动化流程沉淀成可复用能力的人。
- 正在设计 Agent 工程化体系，希望区分“任务方法”“外部工具”“知识检索”和“流程编排”的人。

## 研究路线

表格同时记录已有成果和后续研究计划。已有文件可直接打开；尚未创建的文件使用计划名称占位。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [Skills 的定位：它在 Agent 架构中解决什么问题.md](01%20%7C%20Skills%20的定位：它在%20Agent%20架构中解决什么问题.md) | Skills 到底应该放在 Agent 架构的哪一层？ | 已完成 |
| 02 | `02 | SKILL.md 最小规范与第一个 Skill.md` | 一个 Skill 如何被发现和使用？ | 待研究 |
| 03 | `03 | Reference Skill 与 Action Skill.md` | 任务流程和背景资料应该如何拆分？ | 待研究 |
| 04 | `04 | 渐进式披露：metadata、正文和资源三层加载.md` | Skill 为什么要分层加载上下文？ | 待研究 |
| 05 | `05 | 教学用 Skills runtime 的最小架构.md` | 扫描、路由、加载、执行应该如何分工？ | 待研究 |
| 06 | `06 | Skill Registry：扫描 frontmatter 并校验目录结构.md` | 如何建立本地 Skill 元数据索引？ | 待研究 |
| 07 | `07 | 第一层路由：只凭 name 和 description 选择 Skill.md` | 如何用最小上下文完成 Skill 候选选择？ | 待研究 |
| 08 | `08 | 第二层加载：命中 Skill 后如何读取正文并完成任务.md` | Agent 何时才应该读取完整 `SKILL.md`？ | 待研究 |
| 09 | `09 | 第三层加载：按需读取 references 并守住路径边界.md` | Skill 如何安全使用附录资料？ | 待研究 |
| 10 | `10 | 脚本型 Skill：安全执行 scripts 与校验参数.md` | Skill 中的可执行能力应该如何约束？ | 待研究 |
| 11 | `11 | 关键词路由：多 Skill 场景下如何筛选候选项.md` | 多个 Skill 同时存在时如何减少误召回？ | 待研究 |
| 12 | `12 | 语义路由：用 Embeddings 改进 Skill 召回.md` | 如何借助向量检索提升 Skill 匹配质量？ | 待研究 |
| 13 | `13 | Skill 组合：复合任务如何拆解并传递结果.md` | 多个 Skill 如何协同完成一个任务？ | 待研究 |
| 14 | `14 | Skills + MCP：用 Skill 约束外部工具调用.md` | Skill 如何规定 MCP 工具使用边界？ | 待研究 |
| 15 | `15 | Skills + LangGraph：把路由、执行和人工确认放进状态图.md` | Skill 工作流如何进入显式状态机？ | 待研究 |
| 16 | `16 | Skill 评测：验证触发、误触发与输出质量.md` | 如何评估一个 Skill 是否真的可靠？ | 待研究 |
| 17 | `17 | Skill 工程治理：版本、打包、日志与安全审查.md` | Skills 如何进入团队级维护流程？ | 待研究 |
| 18 | `18 | 综合实战：串联 AI 数字运营助理.md` | 如何把 Skills、RAG、MCP 和 LangGraph 串成完整助理？ | 待研究 |

完整选题规划记录在 [Skills 系统学习路线图](../../../drafts/skills/skills_roadmap.md)。

## 配套材料

前几篇优先把概念边界讲清楚；从需要验证运行机制的阶段开始，再增加线性教学脚本，并逐步演进成 registry、router、loader、executor 和 trace 等模块。

阶段 1 的 Agent 职责边界图已直接写在正文中，使用 Mermaid 表示，便于阅读和后续维护。
