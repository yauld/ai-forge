---
title: LangGraph 系统学习路线
date: 2026-07-13
tags:
  - LangGraph
  - LangChain
  - Agent
  - 学习路线
summary: "基于当前 foundations 已完成内容，重新整理从执行模型到生产级 Agent 工作流的 LangGraph 学习路线。"
---

# LangGraph 系统学习路线

## 写作定位

这条路线建立在已经系统学习过 LangChain 与 RAG 的基础上。

LangChain 更像是"模型、工具、记忆、Agent 的应用层积木"；RAG 解决的是"知识如何被检索进上下文"；LangGraph 要解决的是另一个问题：

```text
当 Agent 不再只是一次模型调用，
而是一个会循环、会分支、会暂停、会恢复、会多人协作的长期流程时，
谁来控制执行顺序、状态变化和恢复机制？
```

这组笔记不要写成 API 速查，而要按**从执行模型到工程控制，再到真实 Agent 工作流**的顺序展开。每篇文章都应回答一个清晰问题，并尽量有可运行、可观察、可复盘的实验。

---

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

写作和实验时遵守两个规则：

1. 先检查当前项目依赖和已有实验代码，再决定 API 写法。
2. 涉及 streaming、durable execution、runtime context、platform 等可能变化的能力时，再查官方文档确认当前推荐方式。

当前项目中 `ToolNode` 和 `tools_condition` 仍从 `langgraph.prebuilt` 导入。不要直接照搬其他版本教程里的导入路径。

---

## 当前完成情况

foundations 已经完成了第一轮很扎实的基础实验：

| 范围 | 已完成文件 | 已覆盖能力 |
| --- | --- | --- |
| 开发环境与启动链路 | 01-03 | CLI、本地 Agent Server、Studio、本地 Graph、数据边界 |
| Graph API 基础 | 04、06、07、08、09、10 | State、Node、Edge、条件边、工具节点、Reducer、Graphviz |
| 可恢复执行 | 11、12、13、14、15、16A | checkpoint、thread_id、time travel、Postgres、interrupt、durable execution |
| 综合场景 | 16B | Workflow + Agent 的内容安全 MVP |
| 记忆系统 | 17 | thread 内短期状态、跨会话长期画像、记忆审计 |

这说明我们已经不是从零开始。接下来最重要的不是继续堆功能，而是把新路线里缺失的关键控制能力补齐：

```text
streaming v2
显式循环
Send 并行分发
Command 节点返回值
runtime context
工具控制、RAG、子图、多 Agent
生产化与平台化
```

---

## 总路线

后续路线分成 5 轮。

```text
第一轮：已完成基础闭环（01-17）
第二轮：补齐执行观察与控制流（18-22）
第三轮：进入真实 Agent 工程模式（23-27）
第四轮：补齐生产化与平台化能力（28-31）
第五轮：做项目实战模板（32-33）
```

每一轮的目标不同：

| 轮次 | 目标 | 判断标准 |
| --- | --- | --- |
| 第一轮 | 看懂图如何运行、如何保存状态、如何暂停恢复 | 已完成，作为后续文章的知识基础 |
| 第二轮 | 能观察每一步、写循环、并行、动态跳转和运行时配置 | 能自己写出可调试的复杂 Graph |
| 第三轮 | 把工具、RAG、子图、多 Agent 组织成业务工作流 | 能把 LangChain / RAG 能力纳入图结构控制 |
| 第四轮 | 面向生产可靠性、测试、观测、迁移和部署 | 能判断一个图上线前缺什么 |
| 第五轮 | 形成自己的安全 Agent 工程模板 | 能复用到真实安全分析或自动化流程 |

---

## 已完成文章

这些文章暂时不重写。后续只在发现版本口径、API 用法或路线依赖不一致时做小幅修订。

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

---

## 后续推荐文章顺序

### 18 | LangGraph Streaming：用 v2 格式看见图每一步怎么跑

**建议文件**

`18 | LangGraph Streaming：用 v2 格式看见图每一步怎么跑.ipynb`

**为什么先做这篇**

后续循环、并行、HITL、前端事件都需要先看懂图执行过程中到底发生了什么。没有 streaming，复杂图只能看最终结果，调试会很痛苦。

**核心问题**

```text
invoke 只给最终结果，stream 如何让我们看见每个节点的状态更新？
```

**这一篇讲**

- `invoke()` 和 `stream()` 的区别
- `stream_mode="updates"`：每步状态增量
- `stream_mode="values"`：每步完整状态快照
- 多 stream mode 时为什么统一使用 `version="v2"`
- `messages` 模式如何观察模型 token 输出
- `custom` 模式和 `get_stream_writer()` 如何推送自定义进度事件
- 如何用 streaming 对照节点执行顺序和 State 变化

**建议实验**

复用第 04 篇订单计算器，先用 `updates` 观察：

```text
user input -> assistant -> tools -> assistant -> END
```

再加一个不依赖模型的自定义 State 小图，用 `custom` 推送：

```text
classify -> draft -> polish
```

**验收标准**

- 能解释 `updates` 和 `values` 的差异。
- 能写出 `version="v2"` 的统一事件处理逻辑。
- 能说明 `get_stream_writer()` 来自 `langgraph.config`，不是 runtime context。

---

### 19 | 用模型驱动 tool loop 实现一个最小 CityWalk Agent

**建议文件**

`19 | 用模型驱动tool loop实现一个最小CityWalk Agent.md`

**核心问题**

```text
如何用模型驱动 tool-calling loop，让 Agent 自己决定何时调用工具、何时回答？
```

**建议实验**

使用高德 MCP 做一个最小 CityWalk Agent：

```text
agent_llm
 -> 有 tool call：run_mcp_tools
 -> 工具结果写回 ToolMessage
 -> 回到 agent_llm
 -> 无 tool call：END
```

这一篇刻意只暴露 `maps_geo` 和 `maps_around_search` 两个工具，不做天气、地图链接、POI 白名单和坐标审计，把重点放在模型驱动的工具循环本身。

**验收标准**

- 能看到模型观察、发起 tool call、工具返回、再次观察的循环。
- 能解释 Host 为什么仍然要做工具白名单检查。
- 能用工具轮数上限防止模型一直调用工具不结束。

---

### 20 | LangGraph Send：并行分发与 Map-Reduce

**建议文件**

`20 | LangGraph Send：并行分发与 Map-Reduce.md`

**核心问题**

```text
一个任务如何拆成多个并行子任务，再把结果合并回来？
```

**这一篇讲**

- fan-out / fan-in 的执行模型
- `Send` 如何动态生成多个并行任务
- 每个并行任务如何带不同输入
- reducer 为什么是并行汇总的前提
- 并发结果的顺序不确定性
- 并行任务失败、成本和限流的基本风险

**建议实验**

围绕安全分析做一个并行汇总：

```text
输入资产
 -> dispatch_checks
 -> 同时检查漏洞、暴露面、弱口令、情报命中
 -> reduce_findings
 -> risk_summary
```

字段设计上使用 `Annotated[list, operator.add]` 汇总 findings。

**验收标准**

- 能说明 `Send` 和普通条件边的区别。
- 能证明 reducer 正确合并多个并行结果。
- 能指出并行结果不应该依赖固定顺序。

---

### 21 | LangGraph Command：节点里同时更新状态和决定下一步

**建议文件**

`21 | LangGraph Command：节点里同时更新状态和决定下一步.md`

**核心问题**

```text
当一个节点既做判断，又要写入判断结果时，应该如何跳转？
```

**这一篇讲**

- 条件边和 `Command` 的边界
- `Command(update=..., goto=...)` 作为节点返回值
- 决策和状态更新天然绑定时，为什么 `Command` 更自然
- `Command` 的类型标注写法
- 与第 15 篇 `Command(resume=...)` 的区别

**必须强调**

`Command` 有两种用途，语法相似但含义不同：

```text
节点返回值：Command(update=..., goto=...)
恢复中断：Command(resume=...) 作为 invoke / stream 的顶层输入
```

这篇只讲第一种。第二种已经在第 15 篇出现，后续工具审批和项目实战会再次使用。

**建议实验**

做一个输入校验流程：

```text
validate_request
 -> 如果信息完整：Command(update={"valid": True}, goto="process")
 -> 如果信息缺失：Command(update={"missing_fields": [...]}, goto="ask_for_more")
```

**验收标准**

- 能说清条件边和 `Command` 各适合什么场景。
- 能避免把 `Command(resume=...)` 写进节点返回值。
- 能在 streaming 输出中观察 `Command` 导致的跳转。

---

### 22 | LangGraph Runtime Context：不要把配置塞进 State

**建议文件**

`22 | LangGraph Runtime Context：不要把配置塞进 State.md`

**状态**

已完成。配套实验位于：

`experiments/22_runtime_context_cicd/`

**核心问题**

```text
哪些信息属于业务状态，哪些信息应该作为运行时配置注入？
```

**这一篇讲**

- State 和 runtime context 的职责边界
- `context_schema` 如何声明运行时上下文
- 节点函数如何接收 `Runtime`
- `runtime.context` 如何读取模型提供商、环境、用户身份等配置
- `runtime.store` 和长期记忆 / 跨线程数据的关系
- `config.configurable` 与 `context_schema` 的取舍
- `get_stream_writer()` 与 runtime context 不是一回事

**建议实验**

使用 CI/CD 发布流水线做一个最小实验：

```text
同一张图
 -> staging dry-run 使用测试 registry 和测试集群配置
 -> prod real deploy 使用生产 registry 和生产集群配置
 -> 观察 Runtime Context 改变运行行为，但不进入最终 State
```

**验收标准**

- 能解释为什么模型选择、租户 ID、环境配置不应该写进 State。
- 能用 `context=...` 调用同一张图得到不同运行行为。
- 能把 State、checkpoint、store、runtime context 四者区分清楚。

---

### 23 | LangGraph 工具调用治理：让工具执行可控、可恢复、可审计

**建议文件**

`23 | LangGraph 工具调用治理：让工具执行可控、可恢复、可审计.md`

**状态**

已完成。配套实验位于：

```text
experiments/23_tool_governance_console
```

**核心问题**

```text
真实业务里的工具调用，如何避免变成模型随意触发的黑箱动作？
```

**这一篇讲**

- Node 中直接调用工具 vs 使用 `ToolNode`
- 模型决定工具调用 vs 图结构决定工具调用
- 工具错误如何进入状态，而不是直接让整图崩掉
- 工具重试、降级和错误路由的基本模式
- 工具权限和危险动作审批如何结合 `interrupt()`
- 工具输入输出如何进入审计日志
- 如何限制某个节点能用的工具集合

**实验设计**

复用安全场景：

```text
用户问题
 -> classify_request
 -> plan_action
 -> enforce_tool_policy
 -> approval_gate
 -> execute_tool
 -> handle_tool_error
 -> retry_or_fallback
 -> append_audit_log
 -> final_response
```

实验覆盖只读查询、高风险动作批准、高风险动作拒绝、工具失败重试降级、只读请求被错误规划成写工具后被策略节点拦截五条路径。

**验收标准**

- 能解释什么时候不该让模型自由选择工具。
- 能记录工具调用审计信息。
- 能把高风险工具动作放到人工审批之后。

---

### 24 | LangGraph + RAG：把检索流程做成可控图

**建议文件**

`24 | LangGraph + RAG：把检索流程做成可控图.ipynb`

**核心问题**

```text
RAG 能不能不只是一条 retrieve -> answer 的链，而是一张可检查、可重试、可兜底的图？
```

**这一篇讲**

- RAG 链路中的 rewrite、retrieve、grade、answer、verify
- 检索结果不足时如何重写查询或走兜底路径
- 文档评分结果应该放进独立 State 字段，而不是塞进 messages
- 如何记录检索证据和最终回答的对应关系
- 什么时候用图控制，什么时候让模型自由组织回答

**建议实验**

复用已有 RAG 学习成果，做最小可控 RAG 图：

```text
question
 -> rewrite_query
 -> retrieve
 -> grade_docs
 -> 文档足够：answer
 -> 文档不足：rewrite_query / fallback
 -> verify
 -> END
```

**验收标准**

- 能看到检索不足时的重试路径。
- 能解释每个检索证据如何支撑最终回答。
- 能避免把业务知识长期塞进 memory。

---

### 25 | LangGraph 子图：把复杂 Agent 拆成模块

**建议文件**

`25 | LangGraph 子图：把复杂 Agent 拆成模块.ipynb`

**核心问题**

```text
复杂工作流什么时候应该拆子图，子图和父图如何共享状态？
```

**这一篇讲**

- 什么是 subgraph
- 子图适合封装什么
- 父图和子图共享 State key 的规则
- 子图 checkpoint namespace 与父图的关系
- 子图如何降低复杂度
- 什么时候不该过早拆子图

**建议实验**

把安全分析拆成几个子图：

```text
主图
 -> asset_profile_subgraph
 -> vulnerability_subgraph
 -> report_subgraph
```

**验收标准**

- 能说明父图和子图哪些 State 字段共享。
- 能看到 checkpoint namespace 中的子图痕迹。
- 能判断一个节点集合是否值得拆成子图。

---

### 26 | LangGraph 多 Agent：让多个角色协作

**建议文件**

`26 | LangGraph 多 Agent：让多个角色协作.ipynb`

**核心问题**

```text
什么时候需要多 Agent，而不是多个普通节点？
```

**这一篇讲**

- supervisor 模式
- handoff 模式
- 多 Agent 和多节点工作流的区别
- `Command(goto=...)` 在 handoff 中的作用
- 多 Agent 的成本、延迟和失控风险
- 如何给每个 Agent 设定清晰职责边界

**建议实验**

```text
Supervisor
 -> Research Agent
 -> Risk Analyst Agent
 -> Report Writer Agent
 -> Final Review
```

可以先用确定性函数模拟角色，再替换为真实模型调用。

**验收标准**

- 能解释为什么不是所有任务都该拆成多 Agent。
- 能比较 supervisor 和 handoff 的控制权差异。
- 能把每个 Agent 的输入输出边界写清楚。

---

### 27 | LangGraph Functional API：什么时候不用 StateGraph

**建议文件**

`27 | LangGraph Functional API：什么时候不用 StateGraph.ipynb`

**定位**

选修篇。补齐官方另一种 API 范式，但不打断 Graph API 主线。

**这一篇讲**

- Graph API 和 Functional API 的区别
- `@entrypoint` / `@task` 的基本用法
- `@task` 对 durable execution 的意义
- Functional API 适合线性流程和快速改造
- Graph API 适合显式状态、复杂分支、复杂协作
- 两种 API 的迁移思路

**验收标准**

- 能判断什么时候不必上 `StateGraph`。
- 能解释 `@task` 为什么适合包住副作用。
- 不把前面主线实验重写成另一套平行体系。

---

### 28 | LangGraph 生产化一：错误处理、重试、缓存、超时与异步并发

**建议文件**

`28 | LangGraph 生产化一：错误处理、重试、缓存、超时与异步并发.ipynb`

**核心问题**

```text
外部模型、向量库和业务 API 都可能失败，图怎样保持可控？
```

**这一篇讲**

- 节点级异常处理
- 工具失败兜底
- `RetryPolicy`
- `CachePolicy` 和自定义 `key_func`
- `timeout` / `TimeoutPolicy`
- async node
- `max_concurrency`
- 成本控制和限流思路

**验收标准**

- 能让某个节点失败后按预期重试或进入兜底分支。
- 能证明缓存命中减少重复昂贵调用。
- 能用并发限制控制并行任务数量。

---

### 29 | LangGraph 生产化二：测试、评估、观测与图迁移

**建议文件**

`29 | LangGraph 生产化二：测试、评估、观测与图迁移.md`

**核心问题**

```text
图上线后，如何知道它没有悄悄坏掉？状态结构变化后，旧 thread 怎么办？
```

**这一篇讲**

- 节点函数单测
- 条件路由测试
- 中断和恢复集成测试
- 固定输入下验证最终 State
- LangSmith tracing 的配置与边界
- 日志应该记录哪些状态变化
- 图结构变化后旧 checkpoint 的迁移风险
- State key 新增、删除、重命名的兼容性问题

**验收标准**

- 至少给出节点、路由、HITL 恢复三类测试。
- 能说明观测数据和业务审计日志的区别。
- 能列出修改 State Schema 前的检查清单。

---

### 30 | LangGraph Platform / Agent Server：什么时候需要部署能力

**建议文件**

`30 | LangGraph Platform 与 Agent Server：什么时候需要部署能力.md`

**核心问题**

```text
本地 LangGraph、Agent Server、LangGraph Platform 到底分别解决什么问题？
```

**这一篇讲**

- 本地 Graph 和本地 Agent Server 的关系
- `langgraph dev` 与平台部署的区别
- `langgraph.json` 的应用结构
- assistants：同一张图的不同配置实例
- threads：有状态会话容器
- runs：一次图执行
- blocking run、streaming run、background run
- 什么时候本地服务就够，什么时候才需要平台能力

**验收标准**

- 能准确区分本地 Studio 调试和云端部署。
- 能解释 assistants、threads、runs 的关系。
- 不把 LangSmith Studio 误写成已经部署了项目。

---

### 31 | LangGraph 平台能力：Auth、Cron、Webhook 与外部系统集成

**建议文件**

`31 | LangGraph 平台能力：Auth、Cron、Webhook 与外部系统集成.md`

**核心问题**

```text
企业环境里，Agent 如何接入权限、调度、通知和前端？
```

**这一篇讲**

- authentication 和 authorization 的区别
- 多租户数据隔离
- cron 定时运行 Agent
- webhook 运行完成后通知外部系统
- webhook 安全
- 前端如何消费 streaming 事件
- 审计日志和权限边界

**验收标准**

- 能画出请求从用户到 thread / run 的权限链路。
- 能说明 cron 和 webhook 分别解决什么问题。
- 能给出前端消费 streaming 事件的最小数据边界。

---

### 32 | 项目实战：安全 Agent 的 LangGraph 最小闭环

**建议文件**

`32 | 项目实战：安全 Agent 的 LangGraph 最小闭环.md`

**核心问题**

```text
能否用一张小而完整的图，把前面核心能力串起来？
```

**项目目标**

```text
用户输入一个资产或问题
 -> 判断任务类型
 -> 查询资产信息
 -> 检索相关安全知识
 -> 分析风险
 -> 必要时请求人工确认
 -> 输出处置建议
```

**应该覆盖**

- 自定义 State
- reducer
- 条件边
- 显式循环
- `Send`
- `Command(update=..., goto=...)`
- `Command(resume=...)`
- 工具节点
- RAG 节点
- checkpoint
- interrupt / resume
- streaming v2
- runtime context
- 错误处理

**验收标准**

- 能跑通合法路径、风险审批路径和工具失败路径。
- 能用 streaming 观察每一步。
- 能回查 checkpoint 和审计日志。

---

### 33 | 项目实战：生产级安全分析工作流

**建议文件**

`33 | 项目实战：生产级安全分析工作流.md`

**核心问题**

```text
如何形成一套可以迁移到真实企业场景的 LangGraph 工程模板？
```

**项目目标**

```text
输入资产或安全事件
 -> 并行收集资产、漏洞、情报、历史处置记录
 -> RAG 检索内部知识
 -> 多节点交叉验证
 -> 高风险动作进入人工审批
 -> 生成报告和处置建议
 -> 写入审计日志
 -> webhook 通知外部系统
```

**应该覆盖**

- 子图拆分
- map-reduce
- 多 Agent 或 supervisor
- 长短期记忆
- 缓存昂贵查询
- 重试与超时
- streaming UI 数据
- LangSmith tracing
- 权限和租户隔离思路
- graph migration 检查清单

**验收标准**

- 有清晰模块边界。
- 有失败路径和人工审批路径。
- 有测试、观测、审计和迁移说明。
- 可以作为后续安全 Agent 项目的模板。

---

## 优先级判断

如果只是想继续写下一篇，优先级是：

```text
18 Streaming v2
19 最小 CityWalk tool loop
20 Send
21 Command 节点返回值
22 Runtime Context
```

这五篇补完之后，再进入工具进阶、RAG、子图和多 Agent。原因很简单：没有 streaming，就看不清复杂图；没有 tool loop、Send 和 Command，就写不出复杂 Agent；没有 runtime context，后续生产配置、租户、模型选择和 store 都会污染 State。

---

## 写作节奏

每篇实验文章尽量遵守同一套结构：

```text
1. 这篇解决什么问题
2. 不使用这个能力时会遇到什么麻烦
3. 最小图结构
4. State 设计
5. 节点和边的实现
6. 运行实验与关键输出
7. 常见误区
8. 小结与下一篇衔接
```

Notebook 适合 18-28 这类需要亲自运行代码的实验。Markdown 适合 29-33 中偏部署、观测、迁移和项目设计的内容；如果某篇需要大量可执行代码，也可以改成 Notebook。

---

## 学习判断

如果目标是"会用 LangGraph"，学到 22 就能写不少完整 demo。

如果目标是"用 LangGraph 做可靠 Agent"，23-29 是分水岭。

如果目标是"把 LangGraph 用在安全业务、RAG 或自动化分析里"，重点完成 24、25、32 和 33。

如果目标是"做企业生产项目"，28-31 不能跳过。

真正重要的不是记住 API，而是形成这个判断：

```text
这个问题应该交给模型自由判断，
还是应该交给图结构明确控制？
```

这就是 LangGraph 最值得学的地方。

---

## 官方资料入口

后续每篇写作前，优先检查项目锁定版本和已有代码；如果涉及当前行为或平台能力，再查官方文档：

- LangGraph 概览：https://docs.langchain.com/oss/python/langgraph/overview
- Graph API 指南：https://docs.langchain.com/oss/python/langgraph/use-graph-api
- Functional API 指南：https://docs.langchain.com/oss/python/langgraph/functional-api
- Streaming 指南：https://docs.langchain.com/oss/python/langgraph/streaming
- Persistence 指南：https://docs.langchain.com/oss/python/langgraph/persistence
- Durable Execution 指南：https://docs.langchain.com/oss/python/langgraph/durable-execution
- Interrupts 指南：https://docs.langchain.com/oss/python/langgraph/interrupts
- Time Travel 指南：https://docs.langchain.com/oss/python/langgraph/use-time-travel
- Memory 指南：https://docs.langchain.com/oss/python/langgraph/add-memory
- Subgraphs 指南：https://docs.langchain.com/oss/python/langgraph/use-subgraphs
- Backward Compatibility 指南：https://docs.langchain.com/oss/python/langgraph/backward-compatibility
- Test 指南：https://docs.langchain.com/oss/python/langgraph/test
- Agent Server 指南：https://docs.langchain.com/langgraph-platform/langgraph-server
- Auth 指南：https://docs.langchain.com/langgraph-platform/auth
- Cron jobs 指南：https://docs.langchain.com/langgraph-platform/cron-jobs
- Webhooks 指南：https://docs.langchain.com/langgraph-platform/use-webhooks
- Changelog：https://docs.langchain.com/oss/python/releases/changelog
