---
title: LangGraph 系统学习路线
date: 2026-06-12
tags:
  - LangGraph
  - LangChain
  - Agent
  - 学习路线
summary: "基于 langgraph 1.2.4 / langgraph-cli 0.4.28，从基础执行模型到生产级 Agent 工作流的系统学习路线。"
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

这组笔记不要写成"API 速查"，而要按**从执行模型到工程控制，再到真实 Agent 工作流**的顺序展开。

---

## 版本基线

```
langgraph：1.2.4
langgraph-cli：0.4.28
LangGraph 文档主线：v1.x
```

CLI 安装命令：

```bash
uv tool install --upgrade "langgraph-cli[inmem]"
```

具体项目通过 `pyproject.toml` 声明 `langgraph`，再由 `uv sync` 安装并锁定实际版本。

**两个容易混淆的版本问题：**

1. 当前项目锁定的 `langgraph 1.2.4` 中，`ToolNode` 和 `tools_condition` 仍从 `langgraph.prebuilt` 导入。不要直接照搬其他版本或其他框架中的导入路径。

2. `stream()` / `astream()` 使用 `version="v2"` 后，输出统一为 `{"type": ..., "ns": ..., "data": ...}`。本系列默认使用 v2，避免单 mode、多 mode 和子图场景的返回格式不同。

---

## 学习总路线

推荐分成 7 个阶段：

```text
阶段 1：跑通开发环境，理解 CLI、本地 Server 与 Studio 的关系
阶段 2：掌握 Graph API 核心，能写状态、节点、边，并立即学会观察执行过程
阶段 3：掌握状态建模，能处理 reducer、Overwrite、并行、map-reduce、Command
阶段 4：掌握可恢复执行，能用 checkpoint、durable execution、interrupt、time travel
阶段 5：掌握 Agent 工程模式，能组合工具、RAG、子图、多 Agent
阶段 6：掌握生产化能力，能处理配置、缓存、超时、异步、测试、迁移、观测
阶段 7：掌握部署形态，理解 assistants、threads、runs、auth、cron、webhook
```

每一阶段都回答一个更高层的问题：

```text
先跑通本地项目并看见图
再知道图是什么、状态怎么流动、如何实时观察每一步（含 v2 流格式）
再知道流程怎么分支、循环、并行，状态更新怎么精确控制
再知道失败、暂停、恢复怎么处理，以及可恢复执行的设计原则
再知道如何把它变成真实业务系统
```

---

## 推荐文章顺序

---

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

先完成最小闭环：

```text
安装 CLI -> 创建项目 -> 同步依赖 -> 启动本地服务 -> 在 Studio 中看见 Graph
```

---

### 02 | LangGraph 启动链路：配置文件如何找到 Graph

**定位**

在第一篇"成功跑起来"的基础上，深入理解 CLI 如何定位、导入并加载 Graph。

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
- 未配置 LangSmith Key 时，哪些数据仍留在本地
- 调用云模型时，数据为什么仍会发送给模型提供商

**重点**

```text
smith.langchain.com 提供调试界面
127.0.0.1:2024 提供本地 Graph API
graph.py 在本地 Python 进程中执行
```

不要把"使用云端 Studio 页面"误解成"项目已经部署到云端"。

---

### 04 | LangGraph 核心三件套：用一个订单计算器看清 Node、State、Edge

**定位**

通过一个完整的订单金额计算助手，同时建立 State、Node、Edge 的基本心智模型，并跑通模型与工具之间的条件循环。

**核心组件**

- `StateGraph`
- `MessagesState`
- `START` / `END`
- `compile()`
- `@tool`
- `bind_tools()`
- `ToolNode`（从 `langgraph.prebuilt` 导入，v1.2.4 仍可用）
- `tools_condition`（同上）
- `add_conditional_edges()`

**这一篇讲**

- 如何把第 01 篇创建的官方模板改造成订单金额计算助手
- 图由 State、Node、Edge 组成
- Node 本质上就是读取和更新 State 的 Python 函数
- `MessagesState` 如何保存用户与模型消息
- `assistant` 与 `ToolNode` 分别承担什么职责
- 为什么要显式写出 `START` 和 `END`
- `compile()` 之后才得到可运行图
- 模型如何通过 `bind_tools()` 获得可调用工具的描述
- `tools_condition` 如何在工具节点与 `END` 之间路由
- 工具结果如何写回 State，再交给模型组织最终回答
- Studio 中的每一步如何对应源码与消息状态

**实验目标**

```text
用户输入写入 State
 -> START -> assistant -> tools -> assistant -> END
```

示例输入：

```text
买 3 件单价 129 元的商品，打九折，一共多少钱？请说明计算过程。
```

**重点**

LangGraph 是围绕 State 运行的流程编排器。模型和工具都是图中的节点，Edge 负责把"模型提出工具请求、图执行工具、模型读取结果"组织成可观察的状态循环。

---

### 05 | LangGraph Streaming：用 v2 格式看见图每一步怎么跑

**定位**

讲可观察的执行过程，建立统一的 v2 流格式习惯。后续学习分支、循环和并行时，都使用 Streaming 对照节点执行与 State 变化。

**这一篇讲**

先掌握 `invoke` 和 `stream` 的区别，以及两种基础 stream mode：

- `updates`：每步只返回本步的状态更新（最常用于调试）
- `values`：每步返回完整的状态快照

文末再认识两种进阶模式：

- `messages`：从模型调用中逐 token 输出内容
- `custom`：节点通过 `get_stream_writer()` 主动推送自定义事件

**为什么使用 `version="v2"`**

不加 `version="v2"` 时，stream 的输出格式会随你用的 stream mode 数量变化：

```python
# 旧方式（不推荐）：不同场景格式不同，容易出错
for chunk in graph.stream(input, stream_mode="updates"):
    print(chunk)  # 直接是 dict

for chunk in graph.stream(input, stream_mode=["updates", "custom"]):
    print(chunk)  # 变成 (mode, data) 元组，格式变了！
```

加了 `version="v2"` 之后，无论 mode 数量多少，格式始终一致：

```python
# 推荐方式：v2 格式统一，type 字段明确区分
for chunk in graph.stream(input, stream_mode=["updates", "custom"], version="v2"):
    if chunk["type"] == "updates":
        print(chunk["data"])  # 始终是 dict
    elif chunk["type"] == "custom":
        print(chunk["data"])  # 始终是 dict
```

**`get_stream_writer()` 用法**

```python
from langgraph.config import get_stream_writer

def my_node(state):
    writer = get_stream_writer()
    writer({"progress": "step 1 started"})  # 主动推送事件
    # ... 做实际工作 ...
    writer({"progress": "step 1 done"})
    return {...}
```

**建议示例**

复用第 04 篇的订单计算器，用 `version="v2"` + `stream_mode="updates"` 逐步打印每个节点的状态更新。

**重点**

先用 `updates` 看清节点更新了什么，再用 `values` 检查完整 State。`messages` 和 `custom` 只建立初步认识，不在这一篇展开复杂前端场景。

---

### 06 | LangGraph 自定义 State：从消息循环走向多步骤流程

**定位**

离开订单案例，用一个不依赖模型和工具的多步骤流程，学习如何定义业务 State。

**这一篇讲**

- 如何使用 `TypedDict` 定义自定义 State
- State 如何保存多步骤流程中的业务字段
- Node 读取 State，返回 State 的增量更新（不是覆盖整个 State）
- Edge 负责流程跳转
- 如何把一个业务任务拆成多个职责单一的节点

**建议示例**

做一个简单的信息处理流程：

```text
输入问题
 -> classify_question
 -> draft_answer
 -> polish_answer
 -> END
```

用 `version="v2"` + `stream_mode="updates"` 观察每一步，直接应用第 05 篇学到的工具。

---

### 07 | LangGraph State 设计：Agent 到底应该记什么

**定位**

专门讲状态建模，为后续更复杂的图打好"状态设计"基础。

**这一篇讲**

- `MessagesState` 适合什么场景
- 自定义 `TypedDict` / Pydantic State 的选择
- 哪些信息放进 `messages`，哪些信息应该放进独立字段
- 控制状态和用户可见对话状态的区别
- Input Schema / Output Schema：如何给图定义独立的输入和输出结构

**真实场景**

> 一个安全分析 Agent 不只要保存聊天消息，还要保存资产 ID、风险等级、当前分析阶段、工具查询结果和最终建议。

**重点**

State 设计决定了整个 Agent 的可维护性。状态乱，图会很快变成一团线。这一篇建立好"状态设计思维"，后续的 reducer、子图、多 Agent 都依赖这个基础。

---

### 08 | LangGraph 条件边：让流程根据结果分支

**定位**

讲条件路由。

**核心组件**

- `add_conditional_edges()`
- router function（路由函数）
- symbolic route（字符串路由标记）

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

条件边是 LangGraph 从"链"变成"图"的关键。

---

### 09 | LangGraph 循环：让 Agent 自己观察、行动、修正

**定位**

讲 Agent loop。

**这一篇讲**

- 为什么 Agent 需要循环
- ReAct 和 LangGraph 循环的关系
- 如何设置继续/结束条件
- 如何避免死循环
- `recursion_limit` 的意义与配置方式（通过 `config={"recursion_limit": N}` 传入）

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

循环是 Agent 能工作的原因，也是 Agent 会失控的地方。学完循环，前三个阶段的基础控制流能力就完整了。

---

### 10 | LangGraph Reducer：状态更新应该覆盖、累积，还是强制覆写

**定位**

讲同一个 State 字段收到新值时如何合并，以及如何绕过 reducer。为下一篇并行工作流做好准备。

**核心组件**

- `Annotated`（标注 reducer 的方式）
- reducer function（自定义合并函数）
- `operator.add`（最常见的追加 reducer）
- `add_messages`（消息专用 reducer，已内置于 MessagesState）
- `Overwrite`（绕过 reducer，强制覆写）

**核心问题**

```text
如果 State 中已经有 {"steps": ["classify"]}，
下一个节点返回 {"steps": ["draft"]}，
LangGraph 应该覆盖旧值，还是把两次结果合并起来？
```

**这一篇讲**

- 默认状态更新是覆盖（last-write-wins）
- reducer 决定同一个 key 如何合并
- 哪些字段适合覆盖，哪些字段适合追加
- 如何使用 `Annotated` + `operator.add` 累积列表
- reducer 写错会导致哪些隐性 bug
- **`Overwrite` 的用法**：当字段已有 reducer，但某个节点需要直接重置该字段时，用 `Overwrite` 绕过 reducer

**`Overwrite` 用法示例**

```python
from langgraph.types import Overwrite
from typing_extensions import Annotated
import operator

class State(TypedDict):
    steps: Annotated[list, operator.add]  # 有 reducer，正常情况追加

def reset_node(state):
    # 需要清空 steps，但 steps 有 reducer，普通返回会追加而不是清空
    # 用 Overwrite 绕过 reducer，直接覆写为空列表
    return {"steps": Overwrite([])}
```

**重点**

先在线性流程里看清"覆盖"、"累积"、"强制覆写"三种情况的区别。下一篇进入并行后，Reducer 会直接决定多个结果能否正确汇总。

---

### 11 | LangGraph Send：并行分发与 Map-Reduce

**定位**

讲并行工作流。

**核心组件**

- `Send`
- fan-out / fan-in
- map-reduce
- reducer（依赖第 10 篇基础）

**这一篇讲**

- 一个节点如何动态生成多个并行任务
- 每个并行任务如何使用不同输入
- 多个结果如何通过 reducer 汇总
- fan-out/fan-in 在 RAG 和安全分析中的用途
- 并行带来的成本、顺序不确定性和错误处理问题

**真实场景**

```text
输入一个资产
 -> 同时分析漏洞、暴露面、弱口令、情报命中
 -> 汇总多个分析结果
 -> 生成最终风险判断
```

**重点**

企业工作流里很多任务不是一条线跑到底，而是"拆开并行做，再汇总"。`Send` 是这类图的关键。reducer 必须在这篇之前学完，否则汇总步骤会不知道如何处理并发写入。

---

### 12 | LangGraph Command：节点里同时更新状态和决定下一步

**定位**

讲更灵活的控制流。

**需要区分的两种用法**

`Command` 有两种完全不同的用途，本篇只讲**用途一**：

**用途一（本篇）：作为节点的返回值**，同时完成"更新状态"和"决定跳转目标"两件事。

```python
# 节点函数返回 Command，同时更新状态 + 跳转到指定节点
def my_node(state):
    return Command(update={"field": "value"}, goto="next_node")
```

**用途二（第 15 篇）：作为顶层输入，恢复被 interrupt() 暂停的图。**

```python
# 这不是节点返回值，而是作为 invoke/stream 的 input 传入，恢复中断
graph.invoke(Command(resume=True), config=config)
```

这两种用途语法很像，但含义完全不同。**不要把用途二的写法用在节点返回值里，也不要把用途一作为顶层输入传给 invoke。**

**核心组件**

- `Command`（从 `langgraph.types` 导入）
- `goto`（跳转目标节点名称）
- `update`（同步更新的状态片段）

**这一篇讲**

- 条件边和 `Command` 的区别
- 什么时候用条件边更清晰
- 什么时候用 `Command` 更自然（决策和状态更新天然绑定时）
- 节点如何返回 `Command(update=..., goto=...)`
- 第 15 篇将展开 `Command(resume=...)` 的 HITL 恢复用法

**真实场景**

> 校验节点发现输入完整时，更新校验结果并进入处理节点；输入不完整时，记录缺失字段并进入补充信息节点。

---

### 13 | LangGraph Checkpointer 与 Durable Execution：状态保存与可恢复执行

**定位**

讲 checkpoint、thread，以及可恢复执行的正确设计方式。这是后续 Time Travel 和 Human-in-the-loop 的必要前置。

**核心组件**

- checkpointer（持久化后端）
- `thread_id`（会话标识符）
- checkpoint（每个 super-step 后的状态快照）
- `InMemorySaver` / `MemorySaver`（开发调试用）
- `SqliteSaver`（本地持久化实验）
- `PostgresSaver`（生产持久化）
- `durability` 参数（`"exit"` / `"async"` / `"sync"`，v1.x 新增）

**这一篇讲**

**第一部分：Checkpointer 基础**

- checkpoint 保存的是什么（图在每个 super-step 执行后的完整 State 快照）
- 为什么需要 `thread_id`（checkpointer 用它定位存哪条线程的状态）
- 同一个图如何服务多个会话
- `MemorySaver` / `SqliteSaver` / `PostgresSaver` 的选择顺序

**第二部分：Durable Execution 的三个原则（生产踩坑点）**

仅有 checkpointer 还不够，图的可恢复执行需要满足以下条件：

1. **确定性**：节点函数对相同输入必须产生相同输出。随机数、时间戳、`uuid` 等不确定操作不应直接写在节点里。

2. **副作用隔离**：API 调用、文件写入和数据库操作要放进职责明确、可重试或幂等的执行单元。Graph API 中优先拆成独立节点；Functional API 中可以使用 `@task`，具体写法留到第 22 篇。

3. **Durability 模式**：通过 `graph.invoke(input, durability="sync")` 控制持久化时机：
   - `"exit"`：仅在图完全执行结束时持久化（性能最好，但崩溃会丢失中间状态）
   - `"async"`：异步持久化（平衡）
   - `"sync"`：每步同步持久化（最安全，适合 HITL 和长时间运行的图）

**重点**

没有 checkpointer，就没有 time travel 和 interrupt。有了 checkpointer 但没有遵循 Durable Execution 原则，恢复时会出现副作用重复执行、状态不一致等难以调试的 bug。

---

### 14 | LangGraph Time Travel：回到历史状态重新跑

**定位**

讲调试和状态回放。依赖第 13 篇的 checkpointer。

**这一篇讲**

- 如何查看历史 checkpoint（`graph.get_state_history(config)`）
- 如何从某个历史状态恢复（指定 `checkpoint_id` 重新 invoke）
- 如何在某个历史状态上手动修改再继续（`graph.update_state(config, values)`）
- time travel 适合调试什么问题
- 为什么它对 Agent 可靠性很重要

**真实场景**

> Agent 第 4 步误判了风险等级，不想从头重跑整个流程，而是回到第 3 步修改状态后继续。

**重点**

Time travel 让 Agent 工作流具备"可复盘、可修正"的工程特性。

---

### 15 | LangGraph Human-in-the-loop：关键步骤先暂停

**定位**

讲人工审批与中断恢复。依赖第 13 篇（checkpointer）。

**Command 的恢复用法**

在第 12 篇，`Command` 是节点的返回值，用于同时更新状态和跳转。

在本篇，`Command(resume=...)` 是**作为顶层输入传给 invoke/stream**，用于恢复被 `interrupt()` 暂停的图。这是 `Command` 的另一种用途，语法像但含义完全不同：

```python
# 节点里返回 Command（第 12 篇的用法）
def approval_node(state):
    decision = interrupt("请确认是否继续？")   # 在节点内部调用 interrupt
    return Command(goto="proceed" if decision else "cancel")

# 恢复中断时，Command(resume=...) 作为 invoke 的顶层输入（本篇用法）
graph.invoke(Command(resume=True), config=config)   # 传入人的决策
```

**核心组件**

- `interrupt()`（在节点内部调用，触发暂停，返回值就是 resume 传入的内容）
- `Command(resume=...)`（恢复时作为顶层输入，不是节点返回值）
- checkpointer（暂停必须依赖持久化）
- `graph.stream_events(version="v3")`（推荐的事件流驱动方式）

**这一篇讲**

- `interrupt()` 是如何让图暂停在节点内部的
- 为什么 HITL 必须依赖 checkpointer（无持久化就无法恢复）
- 用 `graph.invoke(Command(resume=...), config)` 恢复（简单场景）
- 使用 `graph.stream_events(version="v3")` 驱动 HITL 流程
  - `stream.interrupted`：检测图是否因 interrupt 而暂停
  - `stream.interrupts`：读取 interrupt 的 payload（传给人看的内容）
  - `stream.output`：等待最终输出
  - 用 `graph.stream_events(Command(resume=human_response), config)` 继续
- 哪些节点适合加人工审批
- 并行节点同时中断时如何批量恢复（用 interrupt ID 映射）

**真实场景**

> Agent 可以分析漏洞，但如果要创建工单、发通知、调整资产风险等级，就必须先让人确认。

**重点**

Human-in-the-loop 不是"多问一句确认"，而是让图真正暂停、保存、等待外部决策。`Command` 的两种用途在这一篇形成完整闭环。

---

### 16 | LangGraph Memory：短期记忆、长期记忆与跨线程信息

**定位**

把短期状态、长期记忆和业务知识放在一张图里讲清楚。

**这一篇讲**

- checkpointer 解决 thread 内状态（短期记忆）
- store 解决跨 thread 记忆（长期记忆）
- `messages`、`state`、`store` 的职责边界
- semantic memory：事实和偏好
- episodic memory：过去发生过的任务经验
- procedural memory：规则、提示词和工作方式
- 记忆写入是在 hot path 里做，还是后台整理
- 业务知识为什么通常不该放进 memory，而应该走 RAG

**重点**

短期记忆、长期记忆、RAG 是三件事。混在一起会越学越乱。

---

### 17 | LangGraph Runtime Context：不要把配置塞进 State

**定位**

讲运行时配置和依赖注入。

**核心组件**

- `context_schema`（在 `StateGraph(state_schema, context_schema=...)` 中声明）
- `Runtime`（从 `langgraph.runtime` 导入）
- `runtime.context`（在节点函数中访问注入的 context 对象）
- `runtime.store`（在节点函数中访问注入的 store 对象）
- `get_stream_writer()`（从 `langgraph.config` 导入，**不是 runtime 的属性**）
- 调用图时通过 `context=MyContextInstance()` 传入

**用法示例**

```python
from dataclasses import dataclass
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.runtime import Runtime

@dataclass
class ContextSchema:
    model_provider: str = "anthropic"

def call_model(state: MessagesState, runtime: Runtime[ContextSchema]):
    provider = runtime.context.model_provider
    # 根据 provider 选择不同模型
    model = get_model(provider)
    response = model.invoke(state["messages"])
    return {"messages": [response]}

builder = StateGraph(MessagesState, context_schema=ContextSchema)
builder.add_node("model", call_model)
builder.add_edge(START, "model")
builder.add_edge("model", END)
graph = builder.compile()

# 调用时传入 context 实例
graph.invoke(
    {"messages": [{"role": "user", "content": "hi"}]},
    context=ContextSchema(model_provider="openai")
)
```

**这一篇讲**

- State 和 runtime context 的边界（State 是业务流程数据；context 是运行时注入的不可变配置）
- 为什么配置不应该污染业务状态
- 在节点里读取模型选择、用户身份（通过 `runtime.context`）
- 在节点里读取跨线程 store（通过 `runtime.store`）
- 在节点里推送自定义 streaming 事件（通过 `get_stream_writer()`，**与 runtime 无关**）
- `config.configurable` 和 `context_schema` 的关系（旧方式 vs 新方式）

**真实场景**

> 同一张安全分析图，在开发环境用本地模型，在生产环境用云模型；同一个图根据用户身份读取不同租户的数据。

**重点**

区分清楚 `runtime.context`（注入的配置值）和 `get_stream_writer()`（推送流事件的函数）。两者容易混淆，但来源完全不同。

---

### 18 | LangGraph 工具调用进阶：让工具执行可控、可恢复、可审计

**定位**

在第 04 篇最小工具循环，以及前面 Command、Checkpointer、Human-in-the-loop 和 Runtime Context 的基础上，处理真实工程中的工具控制问题。

**这一篇讲**

- Node 中直接调用工具 vs `ToolNode` 的边界与选择
- 模型决定工具调用 vs 图决定工具调用的区别
- 工具返回 `Command` 时如何更新图状态
- 工具错误如何处理（节点级 try/catch 与错误节点路由）
- 工具重试、超时和降级
- 工具权限与危险动作审批（结合 interrupt）
- 工具输入输出如何进入审计日志
- 如何限制模型能够调用的工具集合

**真实场景**

> 安全 Agent 根据用户输入判断是否要查询资产中心、漏洞情报、招聘数据或本地知识库。高危操作需要先 interrupt 等待人工确认再执行。

---

### 19 | LangGraph + RAG：把检索流程做成可控图

**定位**

把检索增强做成可检查、可重试、可兜底的图。

**这一篇讲**

- RAG 不一定是一条固定链，可以是可检查的流程图
- query rewrite -> retrieve -> grade documents -> retry retrieve -> generate answer -> verify answer

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

LangGraph 可以把 RAG 从"检索后回答"升级成"可检查、可重试、可兜底"的工作流。

---

### 20 | LangGraph 子图：把复杂 Agent 拆成模块

**定位**

讲 subgraph 和模块化。

**这一篇讲**

- 什么是 subgraph
- 子图适合封装什么
- 父图和子图如何共享状态（共享 State key 的规则）
- 子图的 checkpoint namespace 与父图的区别
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

---

### 21 | LangGraph 多 Agent：让多个角色协作

**定位**

讲 multi-agent workflow。

**这一篇讲**

- supervisor 模式（一个协调者 Agent 分发任务给其他 Agent）
- handoff 模式（Agent 之间通过 `Command(goto=...)` 交接控制权）
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

- Graph API（`StateGraph`）和 Functional API（`@entrypoint` / `@task`）的区别
- Functional API 的 `context_schema` 写法（与 Graph API 一致）
- `@task` 的作用：把副作用包进 task，支持 durable execution（与第 13 篇呼应）
- Functional API 适合线性流程和快速改造
- Graph API 适合显式状态、复杂分支、复杂协作
- v1.x 中 `config_schema` 已废弃，统一用 `context_schema`
- 两种 API 的迁移思路

**重点**

主线仍然使用 Graph API。读者只需理解两种 API 的适用边界，不必立刻重写前面的项目。`@task` 的 durable execution 价值在这里可以和第 13 篇形成回呼。

---

### 23 | LangGraph 生产化一：错误处理、重试、缓存、超时与异步并发

**定位**

讲运行可靠性和性能成本。

**核心组件**

- `RetryPolicy`（节点级重试策略，`add_node` 时传入）
- 节点函数内的 try/catch（工具失败兜底）
- `CachePolicy(key_func=..., ttl=...)`（节点缓存，可按业务需要自定义缓存键）
- `InMemoryCache`（开发用）/ 自定义 cache backend
- `async def` 节点（异步节点）
- `max_concurrency`（通过运行配置限制并发任务数）
- `timeout`（`add_node(func, timeout=30.0)` 传入，限制单节点最大运行时间）
- `TimeoutPolicy(run_timeout=..., idle_timeout=...)`（组合硬超时和空闲超时）

**`CachePolicy` 示例**

```python
from langgraph.types import CachePolicy
from langgraph.cache.memory import InMemoryCache

def cache_key(state):
    return str(state["query"])  # 自定义缓存键，按 query 区分结果

graph = (
    StateGraph(State)
    .add_node("expensive_node", my_func,
              cache_policy=CachePolicy(key_func=cache_key, ttl=300))
    .compile(cache=InMemoryCache())
)
```

**`timeout` / `TimeoutPolicy` 正确用法**

```python
from langgraph.types import TimeoutPolicy

# 方式一：单节点超时（秒）
builder.add_node("slow_node", my_func, timeout=30.0)

# 方式二：组合硬超时 + 空闲超时
builder.add_node("slow_node", my_func,
                 timeout=TimeoutPolicy(run_timeout=30.0, idle_timeout=10.0))
```

**限制并发**

```python
result = graph.invoke(
    input_data,
    config={"max_concurrency": 4},
)
```

**这一篇讲**

- 节点级异常处理与工具失败兜底
- `RetryPolicy` 的配置方式
- `CachePolicy` 的默认缓存键，以及何时需要自定义 `key_func`
- 节点超时：`timeout` 和 `TimeoutPolicy` 的用法
- async graph：模型、API、向量库并发调用
- 如何通过运行配置设置 `max_concurrency`
- 成本控制思路

**真实场景**

> 一个 Agent 调用了模型、向量库、资产 API、外部情报 API。任何一步都可能失败、超时，不能让整条链路悄悄坏掉。

---

### 24 | LangGraph 生产化二：测试、评估、观测与图迁移

**定位**

讲上线前后怎么保证图没有悄悄坏掉。

**这一篇讲**

- 单测节点函数（纯函数测试）
- 测试条件路由（固定输入验证路由结果）
- 测试中断和恢复（用 `MemorySaver` 做集成测试）
- 固定输入下验证最终 State
- LangSmith tracing 的配置与使用
- 日志应该记录哪些状态变化
- 图结构变化后，旧 thread / checkpoint 怎么办
- state key 新增、删除、重命名的迁移风险
- 官方 Backward Compatibility 指南：https://docs.langchain.com/oss/python/langgraph/backward-compatibility

**真实场景**

> 今天给安全分析图加了一个"情报复核节点"，但线上还有很多 thread 停在人工审批处。新图发布后，这些旧 thread 能不能继续恢复？

**重点**

LangGraph 的生产化不是只有部署。只要图会持久化状态，就必须考虑测试、观测和迁移。

---

### 25 | LangGraph Platform / Agent Server：什么时候需要部署能力

**定位**

最后再讲平台化，不作为入门主线。

**这一篇讲**

- 本地 LangGraph（`langgraph dev`）和 LangGraph Platform（云部署/自托管）的区别
- `langgraph.json` 应用结构
- Agent Server 自动处理哪些持久化能力
- assistants：同一张图的不同配置版本（可类比"图的实例化配置"）
- threads：有状态会话容器
- runs：一次图执行（分 blocking run / streaming run / background run）
- 什么时候本地就够，什么时候才值得上平台

---

### 26 | LangGraph 平台能力：Auth、Cron、Webhook 与外部系统集成

**定位**

讲企业部署后常见的外围能力。

**这一篇讲**

- authentication：请求进来时如何识别用户
- authorization：如何控制 threads、assistants、runs、crons 的访问
- 多租户数据隔离
- cron：定时运行 Agent
- webhook：运行完成后通知外部系统，以及 webhook 安全
- 前端如何消费 streaming 事件（SSE 协议）

**真实场景**

```text
每天 06:10 自动采集安全情报
 -> LangGraph cron 触发图执行
 -> 执行完成后 webhook 通知 Dashboard
 -> 用户只能看到自己租户的 thread 和 run
```

---

### 27 | 项目实战：安全 Agent 的 LangGraph 最小闭环

**定位**

用一个真实项目把前面的概念串起来。

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

- State 设计（TypedDict + 业务字段）
- reducer（列表字段用 `Annotated` + `operator.add`）
- 条件边（任务类型路由）
- `Command`（节点返回值，控制跳转）
- `Command(resume=...)`（HITL 恢复，作为顶层输入）
- `Send`（并行收集多个维度信息）
- 工具节点（资产查询、情报检索）
- RAG 节点（知识库检索）
- checkpoint（`MemorySaver`）
- interrupt + resume（高风险动作的人工确认）
- streaming（`version="v2"` + `updates` 模式观察进度 + `custom` 模式推送前端事件）
- runtime context（开发/生产环境模型切换）
- 错误处理（工具失败兜底）

**重点**

这一篇不是追求功能多，而是验证自己已经能把 LangGraph 用在真实业务问题上。注意在项目里区分 `Command` 的两种用途：节点返回值（控制流）和 HITL 恢复（顶层输入）。

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

- 子图拆分（每个分析领域一个子图）
- map-reduce（`Send` 并行 + reducer 汇总）
- 多 Agent 或 supervisor（根据事件严重程度动态协调）
- 长短期记忆（`MemorySaver` + store 跨线程记忆）
- `CachePolicy(key_func=..., ttl=...)` 缓存昂贵的情报查询节点
- `RetryPolicy` + `timeout` 处理外部 API 不稳定
- streaming UI 数据（`version="v2"` + `custom` mode + 前端 SSE 消费）
- LangSmith tracing 观测
- 权限和租户隔离思路
- graph migration 注意事项（State key 变更前的备份与验证）

**重点**

这一篇用来形成自己的企业级 LangGraph 模板。

---

## 建议学习节奏

### 第一轮：先跑通（01-12）

目标是能自己写出：

```text
CLI 项目 + Studio 调试 + StateGraph + 自定义 State + reducer（含 Overwrite）
+ 条件边 + 循环 + Send + Command（节点返回用法）+ streaming（version="v2"，含 custom mode）
```

### 第二轮：学会可恢复（13-18）

目标是弄清楚：

```text
thread_id、checkpoint、durable execution 三原则、time travel、
interrupt、Command(resume=...)（HITL 恢复用法，与节点返回用法的区别）、
memory、store、runtime context，以及受控的工具调用
```

这一轮重点做实验，必须亲眼看到状态被保存、暂停、恢复。

### 第三轮：做复杂工作流（19-22，其中 22 为选修）

目标是能把 RAG、子图和多 Agent 组织成边界清楚的工作流。

### 第四轮：学生产化（23-26）

目标是补齐企业项目会遇到的：

```text
重试（RetryPolicy）、缓存（CachePolicy，可自定义 key_func）、
超时（timeout + TimeoutPolicy）、异步（async def）、
并发（max_concurrency）、测试、评估、观测（LangSmith）、
迁移（Backward Compatibility）、部署、权限（auth）、调度（cron）、webhook
```

### 第五轮：做项目（27-28）

目标不是"学完 LangGraph"，而是形成自己的 Agent 工程模板。

---

## 与已有课程的衔接关系

### 已学 LangChain 可以复用

- 模型创建（`init_chat_model` 等）
- Messages 体系
- Prompt 模板
- Tools / `@tool` 装饰器
- ReAct Agent 思想（在 LangGraph 里用循环实现）

### 已学 RAG 可以复用

- 文档加载与切分
- Embeddings 和向量库
- Retriever 接口
- Prompt 组装与最小问答链路

### LangGraph 要新增掌握的部分

- 显式状态建模（TypedDict / Pydantic State）
- reducer 与状态合并（`Annotated` + reducer function）
- `Overwrite`（绕过 reducer 强制覆写）
- 图执行模型（StateGraph、Node、Edge、compile）
- 条件边与循环（`add_conditional_edges`、`recursion_limit`）
- `Command`（两种用途：节点返回值 vs HITL 顶层输入）
- `Send` 并行分发（fan-out / fan-in / map-reduce）
- checkpoint 与 thread（MemorySaver / SqliteSaver）
- durable execution 三原则（确定性、副作用隔离、durability 模式）
- interrupt / resume（`interrupt()` + `Command(resume=...)`）
- time travel（`get_state_history` / `update_state`）
- runtime context（`context_schema` + `Runtime` + `runtime.context`）
- `get_stream_writer()`（自定义 streaming 事件，来自 `langgraph.config`）
- streaming 事件体系（`version="v2"` + `updates` / `values` / `messages` / `custom`）
- `stream_events(version="v3")`（生产 HITL 的推荐方式）
- subgraph（父子图 State 共享规则、checkpoint namespace）
- multi-agent workflow（supervisor / handoff）
- `CachePolicy(key_func=..., ttl=...)`（节点缓存）
- `RetryPolicy`（节点重试）
- `timeout` / `TimeoutPolicy`（节点超时）
- async node 与 `max_concurrency`
- testing / evaluation / tracing（LangSmith）
- graph migration（Backward Compatibility）
- assistants / threads / runs（平台概念）
- auth / cron / webhook（企业部署能力）

---

## 官方资料入口

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

---

## 学习判断

如果目标是"会用 LangGraph"，学到 12 就可以写不少完整 demo。

如果目标是"用 LangGraph 做可靠 Agent"，13-18 是分水岭。

如果目标是"把 LangGraph 用在安全业务、RAG 或自动化分析里"，重点完成 19、27 和 28。

如果目标是"做企业生产项目"，23-26 不能跳过。

真正重要的不是记住 API，而是形成这个判断：

```text
这个问题应该交给模型自由判断，
还是应该交给图结构明确控制？
```

这就是 LangGraph 最值得学的地方。
