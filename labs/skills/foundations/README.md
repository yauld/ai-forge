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

这里仅列已经完成、可以直接打开的内容。每完成一篇实验文章，再补充一行新的记录。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [Skills 的定位：它在 Agent 架构中解决什么问题.md](01%20%7C%20Skills%20的定位：它在%20Agent%20架构中解决什么问题.md) | Skills 到底应该放在 Agent 架构的哪一层？ | 已完成 |
| 02 | [最小 SKILL.md：一个 Skill 如何被发现和使用.md](02%20%7C%20最小%20SKILL.md：一个%20Skill%20如何被发现和使用.md) | 一个最小 `SKILL.md` 至少要写清哪些内容，才能被发现和使用？ | 已完成 |
| 03 | [Skill 的两种常见设计形态：Action 与 Reference.md](../../../drafts/skills/03%20%7C%20Skill%20的两种常见设计形态：Action%20与%20Reference.md)<br>[配套实验样本](examples/stage3-skill-types/) | Action 与 Reference 分别适合承载什么内容，如何组合？ | 已完成 |
