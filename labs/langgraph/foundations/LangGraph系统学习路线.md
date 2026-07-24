---
title: LangGraph 系统学习路线
date: 2026-07-13
tags:
  - LangGraph
  - LangChain
  - Agent
  - 学习路线
summary: "整理当前 foundations 已完成的 27 个 LangGraph 编号实验，覆盖从执行模型到多 Agent 工作流的学习路线。"
---

# LangGraph 系统学习路线

## 写作定位

这条路线建立在已经系统学习过 LangChain 与 RAG 的基础上。

LangChain 更像是“模型、工具、记忆、Agent 的应用层积木”；RAG 解决的是“知识如何被检索进上下文”；LangGraph 要解决的是另一个问题：

```text
当 Agent 不再只是一次模型调用，
而是一个会循环、会分支、会暂停、会恢复、会多人协作的长期流程时，
谁来控制执行顺序、状态变化和恢复机制？
```

这组笔记不写成 API 速查，而是按**从执行模型到工程控制，再到真实 Agent 工作流**的顺序组织。当前专题范围固定为已有的 27 个实验主题，编号覆盖 01–27（16 号分为 A/B 两个部分）；每篇文章都围绕一个清晰问题，并尽量提供可运行、可观察、可复盘的实验。

## 当前版本基线

当前仓库以 `pyproject.toml` 和 `uv.lock` 为准：

```text
langgraph：1.2.0
langgraph-checkpoint：4.1.0
langgraph-checkpoint-sqlite：3.1.0
langgraph-checkpoint-postgres：3.1.0
langgraph-prebuilt：1.1.0
langgraph-sdk：0.3.14
```

写作和实验时先检查当前项目依赖和已有实验代码，再决定 API 写法。涉及 streaming、durable execution、runtime context、platform 等可能变化的能力时，再查官方文档确认当前推荐方式。

当前项目中 `ToolNode` 和 `tools_condition` 仍从 `langgraph.prebuilt` 导入，不要直接照搬其他版本教程里的导入路径。

## 当前专题范围

foundations 当前已经完成 27 个实验主题，编号覆盖 01–27（16 号包含 A/B 两个部分），本专题现阶段以这些内容为完整学习范围，不再展开 28 及之后的路线规划。

| 阶段 | 实验 | 已覆盖能力 |
| --- | --- | --- |
| 开发环境与 Graph 基础 | 01–10 | CLI、本地 Agent Server、Studio、本地 Graph、State、Node、Edge、条件边、工具节点、Reducer、Graphviz |
| 可恢复执行与记忆 | 11–17 | checkpoint、thread_id、time travel、Postgres、interrupt、durable execution、短期状态、跨会话长期画像 |
| 执行观察与控制流 | 18–22 | Streaming、模型驱动 tool loop、Send 并行分发、Command、Runtime Context |
| Agent 工程与协作 | 23–27 | 工具调用治理、RAG、子图、Supervisor 多 Agent、Handoff 多 Agent |

这条路线已经形成从基础到综合 Agent 工作流的完整闭环：

```text
Graph 基础
 -> 状态持久化与恢复
 -> 执行观察与控制流
 -> 工具治理、RAG、子图
 -> Supervisor 与 Handoff 多 Agent
```

## 学习阶段

| 阶段 | 目标 | 判断标准 |
| --- | --- | --- |
| 第一阶段 | 看懂图如何运行、如何定义状态和组织流程 | 能独立搭建基础 Graph |
| 第二阶段 | 理解 checkpoint、暂停、恢复与长期记忆 | 能解释状态如何保存、回退和延续 |
| 第三阶段 | 观察执行过程，掌握循环、并行、跳转和运行时配置 | 能写出可调试的复杂 Graph |
| 第四阶段 | 把工具、RAG、子图和多 Agent 组织成业务工作流 | 能判断控制权应交给模型还是图结构 |

## 已完成文章

这些文章构成当前专题的完整内容。后续仅在发现版本口径、API 用法或路线依赖不一致时做小幅修订，不新增 28 及之后的实验规划。

| 序号 | 文件 | 核心问题 | 状态 |
| --- | --- | --- | --- |
| 01 | LangGraph 入门第一步：从开发环境搭建到可视化跑通 | 如何搭建环境并运行第一个可视化 Graph？ | 已完成 |
| 02 | LangGraph 启动原理：CLI 如何找到并加载 Graph | CLI 如何找到并加载 Graph？ | 已完成 |
| 03 | LangGraph Studio 数据流：云端界面如何连接本地 Graph | Studio 如何连接本地 Graph？ | 已完成 |
| 04 | LangGraph 核心三件套：用一个订单计算器看清 Node、State、Edge | 如何用最小例子理解 State、Node、Edge？ | 已完成 |
| 05 | LangGraph 常用语法：类型提示与 Lambda | LangGraph 示例中常见 Python 语法如何工作？ | 已完成 |
| 06 | LangGraph 基础骨架：State、Node、Edge、Graph 是什么 | State、Node、Edge 和 Graph 如何组成流程？ | 已完成 |
| 07 | LangGraph 条件边：让流程根据 State 分支 | 如何根据 State 动态选择分支？ | 已完成 |
| 08 | LangGraph 工具节点：tools、ToolNode、Runnable 是什么 | Tools、ToolNode 与 Runnable 如何协作？ | 已完成 |
| 09 | LangGraph 状态更新与 Reducer | 并发或连续更新时如何合并 State？ | 已完成 |
| 10 | Graphviz 与 LangGraph：安装、绘图与导出 | 如何绘制和导出 Graph 结构？ | 已完成 |
| 11 | LangGraph checkpoint：状态快照到底是什么 | checkpoint 保存了什么？ | 已完成 |
| 12 | LangGraph 多轮对话：checkpoint 和 thread_id | checkpoint 与 thread_id 如何支撑多轮会话？ | 已完成 |
| 13 | 用 checkpoint 查看、回退和修正 LangGraph 状态 | 如何查看、回退和修改历史状态？ | 已完成 |
| 14 | LangGraph checkpoint 如何持久化到 Postgres | 如何把 checkpoint 持久化到 Postgres？ | 已完成 |
| 15 | LangGraph Human-in-the-loop：让 Agent 在人工审批后继续执行 | 如何暂停 Agent，并在人工审批后继续执行？ | 已完成 |
| 16A | LangGraph Durable Execution：节点失败后从断点恢复 | 节点失败后如何从断点恢复？ | 已完成 |
| 16B | LangGraph 内容安全混合方案：Workflow 与 Agent 的 MVP 实现 | Workflow 与 Agent 如何组合成内容安全 MVP？ | 已完成 |
| 17 | LangGraph 记忆系统：让个人助理跨会话记住用户 | 如何让个人助理跨会话记住用户？ | 已完成 |
| 18 | LangGraph Streaming：用 v2 格式看见图每一步怎么跑 | 如何观察每个节点的状态更新和模型输出？ | 已完成 |
| 19 | 用模型驱动 tool loop 实现一个最小 CityWalk Agent | 如何用模型驱动 tool loop？ | 已完成 |
| 20 | LangGraph Send：并行分发与 Map-Reduce | 如何动态分发任务并汇总结果？ | 已完成 |
| 21 | LangGraph Command：节点里同时更新状态和决定下一步 | 如何在节点里同时更新 State 并决定下一步？ | 已完成 |
| 22 | LangGraph Runtime Context：不要把配置塞进 State | 哪些信息属于业务状态，哪些信息应作为运行时配置？ | 已完成 |
| 23 | LangGraph 工具调用治理：让工具执行可控、可恢复、可审计 | 如何约束、恢复并审计工具调用？ | 已完成 |
| 24 | LangGraph + RAG：把最小问答链路接入图 | 如何把最小 RAG 问答链路拆成图节点？ | 已完成 |
| 25 | LangGraph 子图：把复杂 Agent 拆成模块 | 何时拆分子图，如何观察父子图边界？ | 已完成 |
| 26 | Supervisor 多 Agent：中心 Agent 如何统一调度多个角色 | 如何由中心 Agent 统一调度多个专业 Agent？ | 已完成 |
| 27 | Handoff 多 Agent：多个 Agent 如何自主移交控制权 | 多个 Agent 如何根据结果自主移交控制权？ | 已完成 |

## 学习判断

完成这 27 个实验后，可以从基础 Graph 一直走到工具治理、RAG、子图和多 Agent 协作。真正重要的不是记住所有 API，而是形成这个判断：

```text
这个问题应该交给模型自由判断，
还是应该交给图结构明确控制？
```

这就是 LangGraph 最值得学习的地方。

## 官方资料入口

后续如需核对当前行为，优先检查项目锁定版本和已有代码，再查官方文档：

- LangGraph 概览：https://docs.langchain.com/oss/python/langgraph/overview
- Graph API 指南：https://docs.langchain.com/oss/python/langgraph/use-graph-api
- Streaming 指南：https://docs.langchain.com/oss/python/langgraph/streaming
- Persistence 指南：https://docs.langchain.com/oss/python/langgraph/persistence
- Durable Execution 指南：https://docs.langchain.com/oss/python/langgraph/durable-execution
- Interrupts 指南：https://docs.langchain.com/oss/python/langgraph/interrupts
- Memory 指南：https://docs.langchain.com/oss/python/langgraph/add-memory
- Subgraphs 指南：https://docs.langchain.com/oss/python/langgraph/use-subgraphs
