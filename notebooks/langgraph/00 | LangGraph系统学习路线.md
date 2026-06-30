---
atitle: LangGraph 系统学习路线
date: 2026-06-10
tags:
  - LangGraph
  - LangChain
  - Agent
  - 学习路线
summary: "基于已完成的 LangChain 与 RAG 学习，从 CLI、Studio 和本地 Agent Server 起步，面向 LangGraph v1.x 的系统学习路线与文章拆分计划。"
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

所以这组笔记不要写成“API 速查”，而要按**从执行模型到工程控制，再到真实 Agent 工作流**的顺序展开。

## 版本基线

当前学习主线建议基于：

- Python `langgraph`：`1.2.4`
- `langgraph-cli`：`0.4.28`
- LangGraph 文档主线：`v1.x`
- CLI 安装命令：

```bash
uv tool install --upgrade "langgraph-cli[inmem]"
```

具体项目通过 `pyproject.toml` 声明 `langgraph`，再由 `uv sync` 安装并锁定实际版本。

官方文档定位里，LangGraph 是低层级的 Agent orchestration framework/runtime，核心能力包括 durable execution、streaming、human-in-the-loop、memory、checkpointing。学习时不要再以旧版 `0.x` 教程为主线。

## 学习总路线

推荐分成 7 个阶段：

```text
阶段 1：跑通开发环境，理解 CLI、本地 Server 与 Studio 的关系
阶段 2：掌握 Graph API，能写状态、节点、边、分支和循环
阶段 3：掌握状态建模，能处理 reducer、并行、map-reduce
阶段 4：掌握可恢复执行，能用 checkpoint、interrupt、time travel
阶段 5：掌握 Agent 工程模式，能组合工具、RAG、子图、多 Agent
阶段 6：掌握生产化能力，能处理配置、缓存、异步、测试、迁移、观测
阶段 7：掌握部署形态，理解 assistants、threads、runs、auth、cron、webhook
```

这条路线的判断标准不是“是否覆盖所有 API”，而是每一篇都回答一个更高一层的问题：

```text
先跑通本地项目并看见图
再知道图是什么
再知道状态怎么流动
再知道流程怎么分支和循环
再知道失败、暂停、恢复怎么处理
再知道如何把它变成真实业务系统
```

---

## 推荐文章顺序

### 01 | LangGraph 入门第一步：从开发环境搭建到可视化跑通

**定位**

使用当前官方推荐的工程方式创建项目，启动本地 Agent Server，并在 Studio 中看见第一张 Graph。

**核心问题**

```text
怎样从零创建一个可运行、可测试、可在 Studio 中调试的 LangGraph 项目？
```

**这一篇讲**

- LangGraph 是什么，为什么复杂 Agent 需要显式编排
- `langgraph` 与 `langgraph-cli` 的区别
- `uv tool install "langgraph-cli[inmem]"` 的作用
- 使用官方 Python 模板创建项目
- 初步认识 `langgraph.json`、`graph.py`、测试目录和 `uv.lock`
- 使用 `uv sync` 安装依赖并确认实际版本
- 使用 `uv run langgraph dev` 启动本地 Agent Server
- 登录 Studio 并确认本地 Graph 能够可视化
- Studio、API Key、Tracing 与本地执行之间的基本边界
- SOCKS 代理环境下为什么需要 `httpx[socks]`

**重点**

这一篇先完成最小闭环：

```text
安装 CLI
 -> 创建项目
 -> 同步依赖
 -> 启动本地服务
 -> 在 Studio 中看见 Graph
```

---

### 02 | LangGraph 启动链路：配置文件如何找到 Graph

**定位**

在第一篇“成功跑起来”的基础上，深入理解 CLI 如何定位、导入并加载 Graph。

**核心文件**

- `pyproject.toml`
- `uv.lock`
- `.env`
- `langgraph.json`
- `src/agent/graph.py`

**这一篇讲**

- 各核心文件在启动链路中分别承担什么职责
- `langgraph.json` 中 `dependencies`、`graphs`、`env` 的含义
- `./src/agent/graph.py:graph` 如何定位 Python 对象
- `uv run langgraph dev` 的启动过程
- CLI 如何读取配置、导入模块并启动 Agent Server
- 为什么项目依赖必须声明在当前工程的 `pyproject.toml`
- `.env` 如何进入本地服务进程
- 编译后的 Graph 如何向本地 API 暴露图结构与 State Schema

**核心流程**

```text
langgraph dev
 -> 读取 langgraph.json
 -> 加载 graph.py:graph
 -> 启动 http://127.0.0.1:2024
```

**重点**

网页能看到 Graph 的前提，是 CLI 已经在本地成功加载并编译了 `graph` 对象。

---

### 03 | LangGraph Studio 数据流：云端界面如何连接本地 Graph

**定位**

讲清楚一次 Studio 调试请求经过了哪些组件，以及哪些数据留在本地、哪些数据可能发送到外部服务。

**这一篇讲**

- 为什么 Studio URL 位于 `smith.langchain.com`
- URL 中 `baseUrl=http://127.0.0.1:2024` 的意义
- Studio 前端、本地 Agent Server 与本地 Python 代码的关系
- 浏览器如何读取本地图结构和 State Schema
- Studio 如何根据 Schema 生成输入区域
- 一次输入如何从 Studio 到达本地节点，再把结果返回浏览器
- 停止本地服务后为什么 Studio 无法继续执行
- `LANGSMITH_API_KEY` 与 LangSmith Trace 的关系
- 每月 5,000 条免费 Trace 是什么
- 未配置 LangSmith Key 时，哪些数据仍留在本地
- 调用云模型时，数据为什么仍会发送给模型提供商

**重点**

```text
smith.langchain.com 提供调试界面
127.0.0.1:2024 提供本地 Graph API
graph.py 在本地 Python 进程中执行
```

不要把“使用云端 Studio 页面”误解成“项目已经部署到云端”。

---

### 04 | LangGraph 核心三件套：用一个订单计算器看清 Node、State、Edge

**定位**

通过一个完整的订单金额计算助手，同时建立 State、Node、Edge 的基本心智模型，并跑通模型与工具之间的条件循环。

**核心组件**

- `StateGraph`
- `MessagesState`
- `START`
- `END`
- `compile`
- `@tool`
- `bind_tools`
- `ToolNode`
- `tools_condition`
- `add_conditional_edges`

**这一篇讲**

- 如何把第 01 篇创建的官方模板改造成订单金额计算助手
- 订单案例需要增加哪些依赖和环境变量
- 改造后的完整 `graph.py`
- 图由 State、Node、Edge 组成
- Node 本质上就是读取和更新 State 的 Python 函数
- `MessagesState` 如何保存用户与模型消息
- `assistant` 与 `ToolNode` 分别承担什么职责
- 为什么要显式写出 `START` 和 `END`
- `compile()` 之后才得到可运行图
- 模型如何通过 `bind_tools` 获得可调用工具的描述
- `tools_condition` 如何在工具节点与 `END` 之间路由
- 工具结果如何写回 State，再交给模型组织最终回答
- Studio 中的每一步如何对应源码与消息状态

**实验目标**

```text
用户输入写入 State
 -> START
 -> assistant
 -> tools
 -> assistant
 -> END
```

示例输入：

```text
买 3 件单价 129 元的商品，打九折，一共多少钱？请说明计算过程。
```

**重点**

LangGraph 是围绕 State 运行的流程编排器。模型和工具都是图中的节点，Edge 负责把“模型提出工具请求、图执行工具、模型读取结果”组织成可观察的状态循环。

---

### 05 | LangGraph 自定义 State：从消息循环走向多步骤流程

**定位**

离开订单案例，用一个不依赖模型和工具的多步骤流程，学习如何定义业务 State，并进一步巩固 Graph API 的执行模型。

**这一篇讲**

- 如何使用 `TypedDict` 定义自定义 State
- State 如何保存多步骤流程中的业务字段
- Node 读取 State，返回 State 的增量更新
- Edge 负责流程跳转
- 如何把一个业务任务拆成多个职责单一的节点
- 为什么“状态更新”比“函数返回值”更重要

**建议示例**

做一个简单的信息处理流程：

```text
输入问题
 -> classify_question
 -> draft_answer
 -> polish_answer
 -> END
```

**重点**

第 04 篇使用 `MessagesState` 跑通模型与工具循环；这一篇改用自定义 State，理解 LangGraph 如何编排普通的多步骤业务流程。

---

### 06 | LangGraph State 设计：Agent 到底应该记什么

**定位**

专门讲状态建模。

**这一篇讲**

- `MessagesState` 适合什么场景
- 自定义 `TypedDict` / Pydantic State
- 哪些信息放进 `messages`
- 哪些信息应该放进独立字段
- 控制状态和用户可见对话状态的区别

**真实场景**

> 一个安全分析 Agent 不只要保存聊天消息，还要保存资产 ID、风险等级、当前分析阶段、工具查询结果和最终建议。

**重点**

State 设计决定了整个 Agent 的可维护性。状态乱，图会很快变成一团线。

---

### 07 | LangGraph Streaming：看见图每一步怎么跑

**定位**

讲可观察的执行过程。

**这一篇讲**

- `invoke` 和 `stream` 的区别
- `updates`：只看每步状态更新
- `values`：看每步完整状态
- `messages`：观察模型消息与 token 输出
- 如何根据调试目标选择合适的 stream mode
- 如何用 streaming 对照节点执行与 State 变化

**建议示例**

复用第 05 篇的多步骤流程，逐步打印每个节点的状态更新：

```text
[classify_question] ...
[draft_answer] ...
[polish_answer] ...
```

**重点**

先学会看见图的执行过程，后续学习分支、循环、并行和恢复时才不会只盯着最终答案猜问题。

---

### 08 | LangGraph 条件边：让流程根据结果分支

**定位**

讲条件路由。

**核心组件**

- `add_conditional_edges`
- router function
- symbolic route

**这一篇讲**

- 固定边和条件边的区别
- 路由函数应该返回什么
- 如何把分类结果映射到下一个节点
- 如何避免条件分支越来越乱

**建议示例**

```text
用户问题
 -> classify_intent
 -> 如果是技术问题：technical_answer
 -> 如果是普通问题：general_answer
 -> 无法识别：request_clarification
```

**重点**

条件边是 LangGraph 从“链”变成“图”的关键。

---

### 09 | LangGraph 循环：让 Agent 自己观察、行动、修正

**定位**

讲 Agent loop。

**这一篇讲**

- 为什么 Agent 需要循环
- ReAct 和 LangGraph 循环的关系
- 如何设置继续/结束条件
- 如何避免死循环
- recursion limit 的意义

**建议示例**

```text
plan
 -> act
 -> observe
 -> should_continue?
    -> yes: act
    -> no: final_answer
```

**重点**

循环是 Agent 能工作的原因，也是 Agent 会失控的地方。

---

### 10 | LangGraph Reducer：状态更新应该覆盖还是累积

**定位**

讲同一个 State 字段收到新值时如何合并，为下一篇并行工作流做好准备。

**核心组件**

- `Annotated`
- reducer function
- `operator.add`
- append-only state

**核心问题**

```text
如果 State 中已经有 {"steps": ["classify"]}，
下一个节点返回 {"steps": ["draft"]}，
LangGraph 应该覆盖旧值，还是把两次结果合并起来？
```

**这一篇讲**

- 默认状态更新是覆盖
- reducer 决定同一个 key 如何合并
- 哪些字段适合覆盖，哪些字段适合追加
- 如何使用 `Annotated` 和 `operator.add` 累积列表
- reducer 写错会导致哪些隐性 bug

**建议示例**

```text
START
 -> classify_question，记录 ["classify"]
 -> draft_answer，追加 ["draft"]
 -> polish_answer，追加 ["polish"]
 -> END
```

**重点**

先在线性流程里看清“覆盖”和“累积”的区别。下一篇进入并行后，Reducer 会直接决定多个结果能否正确汇总。

---

### 11 | LangGraph Send：并行分发与 Map-Reduce

**定位**

讲并行工作流。

**核心组件**

- `Send`
- fan-out
- fan-in
- map-reduce
- reducer

**这一篇讲**

- 一个节点如何动态生成多个并行任务
- 每个并行任务如何使用不同输入
- 多个结果如何通过 reducer 汇总
- fan-out/fan-in 在 RAG 和安全分析中的用途
- 并行带来的成本、顺序和错误处理问题

**真实场景**

```text
输入一个资产
 -> 同时分析漏洞、暴露面、弱口令、情报命中
 -> 汇总多个分析结果
 -> 生成最终风险判断
```

**重点**

企业工作流里很多任务不是一条线跑到底，而是“拆开并行做，再汇总”。`Send` 是这类图的关键。

---

### 12 | LangGraph Command：在节点里同时更新状态和决定下一步

**定位**

讲更灵活的控制流。

**核心组件**

- `Command`
- `goto`
- `update`

**核心问题**

```text
有些节点执行完之后，既要修改 state，又要决定下一个节点去哪。
这个逻辑应该放在条件边里，还是直接由节点返回？
```

**这一篇讲**

- 条件边和 `Command` 的区别
- 什么时候用条件边更清晰
- 什么时候用 `Command` 更自然
- 节点如何返回 `Command(update=..., goto=...)`

**真实场景**

> 校验节点发现输入完整时，更新校验结果并进入处理节点；输入不完整时，记录缺失字段并进入补充信息节点。

**重点**

`Command` 适合处理“决策和状态更新天然绑定”的场景。它是写复杂图时绕不开的控制工具。

---

### 13 | LangGraph Checkpointer：短期记忆与线程状态

**定位**

讲 checkpoint 和 thread。

**核心组件**

- checkpointer
- `thread_id`
- checkpoint
- thread state

**这一篇讲**

- checkpoint 保存的是什么
- 为什么需要 `thread_id`
- 同一个图如何服务多个会话
- checkpointer 和 LangChain 短期记忆的关系
- MemorySaver / SQLite / Postgres 的学习顺序

**重点**

LangGraph 的记忆不是“把聊天记录塞给模型”，而是把图状态保存下来，下一次可以继续演进。

---

### 14 | LangGraph Time Travel：回到历史状态重新跑

**定位**

讲调试和状态回放。

**这一篇讲**

- 如何查看历史 checkpoint
- 如何从某个历史状态恢复
- time travel 适合调试什么问题
- 为什么它对 Agent 可靠性很重要

**真实场景**

> Agent 第 4 步误判了风险等级，不想从头重跑整个流程，而是回到第 3 步修改状态后继续。

**重点**

Time travel 让 Agent 工作流具备“可复盘、可修正”的工程特性。

---

### 15 | LangGraph Human-in-the-loop：关键步骤先暂停

**定位**

讲人工审批。

**核心组件**

- `interrupt`
- `Command`
- checkpointer
- resume

**真实场景**

> Agent 可以分析漏洞，但如果要创建工单、发通知、调整资产风险等级，就必须先让人确认。

**这一篇讲**

- 什么是 interrupt
- 为什么 HITL 必须依赖持久化
- 人如何 approve / edit / reject
- 如何恢复被暂停的图
- 哪些节点适合加人工审批

**重点**

Human-in-the-loop 不是“多问一句确认”，而是让图真正暂停、保存、等待外部决策。

---

### 16 | LangGraph Memory：短期记忆、长期记忆与跨线程信息

**定位**

把短期状态、长期记忆和业务知识放在一张图里讲清楚。

**这一篇讲**

- checkpointer 解决 thread 内状态
- store 解决跨 thread 记忆
- messages、state、store 的职责边界
- semantic memory：事实和偏好
- episodic memory：过去发生过的任务经验
- procedural memory：规则、提示词和工作方式
- 记忆写入是在 hot path 里做，还是后台整理
- 长期用户偏好如何保存
- 业务知识为什么通常不该放进 memory，而应该走 RAG

**重点**

短期记忆、长期记忆、RAG 是三件事。混在一起会越学越乱。

---

### 17 | LangGraph Runtime Context：不要把配置塞进 State

**定位**

讲运行时配置和依赖注入。

**核心组件**

- `context_schema`
- `Runtime`
- `runtime.context`
- `runtime.store`
- `runtime.stream_writer`
- `runtime.execution_info`
- `runtime.server_info`

**核心问题**

```text
模型供应商、用户 ID、数据库连接、环境配置，
到底应该放进 State，还是作为运行上下文传给图？
```

**这一篇讲**

- State 和 runtime context 的边界
- 为什么配置不应该污染业务状态
- 如何在节点里读取模型选择、用户身份、数据库连接
- deployed graph 中如何读取 server info
- tool / node / middleware 如何共享运行上下文

**真实场景**

> 同一张安全分析图，在开发环境用本地模型，在生产环境用云模型；同一个图根据用户身份读取不同租户的数据。

**重点**

企业项目里，一张图通常要服务多个用户、多个环境、多个模型配置。runtime context 是把图写成“可复用架构”的关键。

---

### 18 | LangGraph 工具调用进阶：让工具执行可控、可恢复、可审计

**定位**

在第 04 篇最小工具循环，以及前面 Command、Checkpointer、Human-in-the-loop 和 Runtime Context 的基础上，处理真实工程中的工具控制问题。

**这一篇讲**

- Node 中直接调用工具与 `ToolNode` 的边界
- 模型决定工具调用与图决定工具调用的区别
- 工具返回 `Command` 时如何更新图状态
- 工具错误如何处理
- 工具重试、超时和降级
- 工具权限与危险动作审批
- 工具输入输出如何进入审计日志
- 如何限制模型能够调用的工具集合

**真实场景**

> 安全 Agent 根据用户输入判断是否要查询资产中心、漏洞情报、招聘数据或本地知识库。

**重点**

真实项目的重点不是“工具能被调用”，而是工具调用能被约束、失败能被处理、危险动作能被审批。

---

### 19 | LangGraph + RAG：把检索流程做成可控图

**定位**

把检索增强做成可检查、可重试、可兜底的图。

**这一篇讲**

- RAG 不一定是一条固定链
- query rewrite
- retrieve
- grade documents
- retry retrieve
- generate answer
- verify answer

**建议流程**

```text
question
 -> rewrite_query
 -> retrieve
 -> grade_docs
 -> 如果文档够用：answer
 -> 如果文档不够：rewrite_query / web_or_tool_fallback
 -> verify
 -> END
```

**重点**

LangGraph 可以把 RAG 从“检索后回答”升级成“可检查、可重试、可兜底”的工作流。

---

### 20 | LangGraph 子图：把复杂 Agent 拆成模块

**定位**

讲 subgraph 和模块化。

**这一篇讲**

- 什么是 subgraph
- 子图适合封装什么
- 父图和子图如何共享状态
- 子图如何降低复杂度
- 什么时候不该过早拆子图

**真实场景**

```text
安全分析主图
 -> 资产画像子图
 -> 漏洞研判子图
 -> 情报检索子图
 -> 报告生成子图
```

**重点**

子图不是为了炫技，而是为了让复杂 Agent 有边界。

---

### 21 | LangGraph 多 Agent：让多个角色协作

**定位**

讲 multi-agent workflow。

**这一篇讲**

- supervisor 模式
- handoff 模式
- 多 Agent 和多个普通节点的区别
- 什么时候需要多 Agent
- 多 Agent 的成本和失控风险

**建议示例**

```text
Supervisor
 -> Research Agent
 -> Risk Analyst Agent
 -> Report Writer Agent
 -> Final Review
```

**重点**

多 Agent 不是越多越强。角色边界清楚，才值得拆。

---

### 22 | LangGraph Functional API：什么时候不用 StateGraph

**定位**

选修篇。补齐另一种官方 API 范式，但不打断 Graph API 主线。

**这一篇讲**

- Graph API 和 Functional API 的区别
- Functional API 适合线性流程和快速改造
- Graph API 适合显式状态、复杂分支、复杂协作
- 两种 API 的迁移思路

**重点**

主线仍然使用 Graph API。读者只需理解两种 API 的适用边界，不必立刻重写前面的项目。

---

### 23 | LangGraph 生产化一：错误处理、重试、缓存与异步并发

**定位**

讲运行可靠性和性能成本。

**核心组件**

- `RetryPolicy`
- node-level error handling
- `CachePolicy`
- graph cache
- async node
- `max_concurrency`
- deferred node

**这一篇讲**

- 节点级异常处理
- 工具失败兜底
- 超时与重试
- 节点缓存：哪些昂贵节点适合 cache
- async graph：模型、API、向量库并发调用
- `max_concurrency` 如何限制并发
- `defer=True` 如何让汇总节点等其他任务完成
- 成本控制

**真实场景**

> 一个 Agent 调用了模型、向量库、资产 API、外部情报 API。任何一步都可能失败，不能让整条链路悄悄坏掉。

**重点**

企业项目里的 Agent 不只是“能回答”，还要稳定、便宜、可限流、可恢复。

---

### 24 | LangGraph 生产化二：测试、评估、观测与图迁移

**定位**

讲上线前后怎么保证图没有悄悄坏掉。

**这一篇讲**

- 单测节点函数
- 测试条件路由
- 测试中断和恢复
- 固定输入下验证最终 State
- LangSmith tracing
- 日志应该记录哪些状态变化
- 图结构变化后，旧 thread / checkpoint 怎么办
- state key 新增、删除、重命名的迁移风险

**真实场景**

> 今天给安全分析图加了一个“情报复核节点”，但线上还有很多 thread 停在人工审批处。新图发布后，这些旧 thread 能不能继续恢复？

**重点**

LangGraph 的生产化不是只有部署。只要图会持久化状态，就必须考虑测试、观测和迁移。

---

### 25 | LangGraph Platform / Agent Server：什么时候需要部署能力

**定位**

最后再讲平台化，不作为入门主线。

**这一篇讲**

- 本地 LangGraph 和 LangGraph Platform 的区别
- `langgraph.json` 应用结构
- Agent Server 自动处理哪些持久化能力
- assistants：同一张图的不同配置版本
- threads：有状态会话容器
- runs：一次图执行
- background runs 和 streaming runs
- Studio / tracing / deployment 的作用
- 什么时候本地就够
- 什么时候才值得上平台

**重点**

先学开源框架和核心执行模型，再考虑平台能力。不要一开始就被部署概念带偏。

---

### 26 | LangGraph 平台能力：Auth、Cron、Webhook 与外部系统集成

**定位**

讲企业部署后常见的外围能力。

**这一篇讲**

- authentication：请求进来时如何识别用户
- authorization：如何控制 threads、assistants、runs、crons 的访问
- 多租户数据隔离
- cron：定时运行 Agent
- webhook：运行完成后通知外部系统
- webhook 安全：token、headers、域名限制、禁用策略
- 前端如何消费 streaming 事件

**真实场景**

```text
每天 06:10 自动采集安全情报
 -> LangGraph cron 触发图执行
 -> 执行完成后 webhook 通知 Dashboard
 -> 用户只能看到自己租户的 thread 和 run
```

**重点**

企业生产项目里，Agent 不是孤立脚本。它要接权限、调度、通知、前端、审计和多租户边界。

---

### 27 | 项目实战：安全 Agent 的 LangGraph 最小闭环

**定位**

用一个真实项目把前面的概念串起来。

**项目目标**

做一个最小安全分析 Agent：

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

- State 设计
- reducer
- 条件边
- `Command`
- `Send`
- 工具节点
- RAG 节点
- checkpoint
- interrupt
- streaming
- runtime context
- 错误处理
- 最终报告生成

**重点**

这一篇不是追求功能多，而是验证自己已经能把 LangGraph 用在真实业务问题上。

---

### 28 | 项目实战：生产级安全分析工作流

**定位**

在最小闭环之后，再做一个更贴近企业项目的版本。

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
- 缓存和重试
- streaming UI 数据
- LangSmith tracing
- 权限和租户隔离思路
- graph migration 注意事项

**重点**

这一篇用来形成自己的企业级 LangGraph 模板：状态怎么设计、节点怎么拆、工具怎么控、失败怎么恢复、结果怎么交付。

---

## 建议学习节奏

### 第一轮：先跑通

学习 01-12。

目标是能自己写出：

```text
CLI 项目 + Studio 调试 + StateGraph + reducer + 条件边
+ 循环 + Send + Command + streaming
```

这一轮完成 Graph API 的核心闭环：状态如何变化、流程如何分支循环、结果如何合并、任务如何并行。

### 第二轮：学会可恢复

学习 13-18。

目标是弄清楚：

```text
thread_id、checkpoint、time travel、interrupt、resume、memory、store、
runtime context，以及受控的工具调用
```

这一轮重点做实验，必须亲眼看到状态被保存、暂停、恢复。

### 第三轮：做复杂工作流

学习 19-22，其中 22 为选修。

目标是能把 RAG、子图和多 Agent 组织成边界清楚的工作流。

### 第四轮：学生产化

学习 23-26。

目标是补齐企业项目会遇到的：

```text
重试、缓存、异步、并发、测试、评估、观测、迁移、部署、权限、调度、webhook
```

### 第五轮：做项目

完成 27-28。

目标不是“学完 LangGraph”，而是形成自己的 Agent 工程模板。

## 与已有课程的衔接关系

### 已学 LangChain 可以复用的部分

- 模型创建
- Messages
- Prompt
- Tools
- 短期记忆
- 长期记忆
- ReAct Agent
- Middleware 的控制思想

### 已学 RAG 可以复用的部分

- 文档加载
- 文档切分
- Embeddings
- 向量库
- Retriever
- Prompt 组装
- 最小问答链路

### LangGraph 要新增掌握的部分

- 显式状态建模
- reducer 与状态合并
- 图执行模型
- 条件边与循环
- `Command` 控制跳转
- `Send` 并行分发
- checkpoint 与 thread
- interrupt / resume
- time travel
- runtime context
- subgraph
- multi-agent workflow
- streaming 事件体系
- node cache
- retry / timeout / async / concurrency
- testing / evaluation / tracing
- graph migration
- assistants / threads / runs
- auth / cron / webhook
- 可恢复的复杂业务流程

## 官方资料入口

- LangGraph overview: https://docs.langchain.com/oss/python/langgraph
- Graph API: https://docs.langchain.com/oss/python/langgraph/graph-api
- Functional API: https://docs.langchain.com/oss/python/langgraph/functional-api
- Choosing APIs: https://docs.langchain.com/oss/python/langgraph/choosing-apis
- Streaming: https://docs.langchain.com/oss/python/langgraph/streaming
- Persistence: https://docs.langchain.com/oss/python/langgraph/persistence
- Memory: https://docs.langchain.com/oss/python/langgraph/add-memory
- Human-in-the-loop: https://docs.langchain.com/oss/python/langgraph/human-in-the-loop
- Agent Server: https://docs.langchain.com/langgraph-platform/langgraph-server
- Assistants: https://docs.langchain.com/langgraph-platform/assistants
- Auth: https://docs.langchain.com/langgraph-platform/auth
- Cron jobs: https://docs.langchain.com/langgraph-platform/cron-jobs
- Webhooks: https://docs.langchain.com/langgraph-platform/use-webhooks
- LangGraph v1 release notes: https://docs.langchain.com/oss/python/releases/langgraph-v1

## 我的学习判断

如果目标是“会用 LangGraph”，学到 12 就可以写不少完整 demo。

如果目标是“用 LangGraph 做可靠 Agent”，13-18 是分水岭。

如果目标是“把 LangGraph 用在安全业务、RAG 或自动化分析里”，重点完成 19、27 和 28。

如果目标是“做企业生产项目”，23-26 不能跳过。因为生产环境里最常见的问题不是图不会跑，而是：

```text
状态怎么迁移？
失败怎么重试？
成本怎么控制？
多用户怎么隔离？
任务怎么定时跑？
运行完成怎么通知外部系统？
线上怎么观察每一步发生了什么？
```

真正重要的不是记住 API，而是形成这个判断：

```text
这个问题应该交给模型自由判断，
还是应该交给图结构明确控制？
```

这就是 LangGraph 最值得学的地方。
