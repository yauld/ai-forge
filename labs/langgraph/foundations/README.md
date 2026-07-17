# LangGraph 实战专题

这个专题研究如何用 LangGraph 构建可控、可恢复、可检查的 AI 工作流。从 State、Node 和 Edge 开始，逐步进入条件分支、工具节点、Checkpoint、人工审批和跨会话记忆。

LangGraph 的价值不只是“把流程画成图”，而是让复杂 AI 应用具备明确的状态转移、暂停恢复和人工介入边界。

## 你会学到什么

- State、Node、Edge 和 Graph 如何构成工作流。
- 条件边、ToolNode 与 Reducer 如何控制流程和状态。
- Checkpoint 如何支持多轮对话、回退与持久化。
- Human-in-the-loop 如何介入高风险操作。
- Durable Execution 与长期记忆如何支撑可靠 Agent。

## 适合读者

- 已经理解基本模型调用，准备构建多步骤 AI 流程的人。
- 希望 Agent 具备可恢复、可审计、可人工介入能力的人。
- 想理解生产级 AI Workflow 核心机制的开发者。

## 研究路线

表格同时记录已有成果和后续研究计划。已有文件可直接打开；尚未创建的文件使用计划名称占位。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 00 | [LangGraph系统学习路线.md](00%20%7C%20LangGraph系统学习路线.md) | LangGraph 的核心概念应该按什么顺序学习？ | 已完成 |
| 01 | [LangGraph 入门第一步：从开发环境搭建到可视化跑通.ipynb](01%20%7C%20LangGraph%20入门第一步：从开发环境搭建到可视化跑通.ipynb) | 如何搭建环境并运行第一个可视化 Graph？ | 已完成 |
| 02 | [LangGraph 启动原理：CLI 如何找到并加载 Graph.md](02%20%7C%20LangGraph%20启动原理：CLI%20如何找到并加载%20Graph.md) | LangGraph CLI 如何找到并加载 Graph？ | 已完成 |
| 03 | [LangGraph Studio 数据流：云端界面如何连接本地 Graph.md](03%20%7C%20LangGraph%20Studio%20数据流：云端界面如何连接本地%20Graph.md) | 云端 Studio 如何连接本地 Graph？ | 已完成 |
| 04 | [LangGraph 核心三件套：用一个订单计算器看清Node、State、Edge.md](04%20%7C%20LangGraph%20核心三件套：用一个订单计算器看清Node、State、Edge.md) | 如何用最小例子理解 LangGraph 的核心三件套？ | 已完成 |
| 05 | [LangGraph 常用语法：类型提示与Lambda.ipynb](05%20%7C%20LangGraph%20常用语法：类型提示与Lambda.ipynb) | LangGraph 示例中常见的 Python 语法如何工作？ | 已完成 |
| 06 | [LangGraph 基础骨架：State、Node、Edge、Graph 是什么.ipynb](06%20%7C%20LangGraph%20基础骨架：State、Node、Edge、Graph%20是什么.ipynb) | State、Node、Edge 和 Graph 如何组成完整流程？ | 已完成 |
| 07 | [LangGraph 条件边：让流程根据 State 分支.ipynb](07%20%7C%20LangGraph%20条件边：让流程根据%20State%20分支.ipynb) | 如何根据 State 动态选择流程分支？ | 已完成 |
| 08 | [LangGraph 工具节点：tools、ToolNode、Runnable 是什么.ipynb](08%20%7C%20LangGraph%20工具节点：tools、ToolNode、Runnable%20是什么.ipynb) | Tools、ToolNode 与 Runnable 如何协作？ | 已完成 |
| 09 | [LangGraph 状态更新与 Reducer.ipynb](09%20%7C%20LangGraph%20状态更新与%20Reducer.ipynb) | 并发或连续更新时如何合并 State？ | 已完成 |
| 10 | [Graphviz 与 LangGraph：安装、绘图与导出.ipynb](10%20%7C%20Graphviz%20与%20LangGraph：安装、绘图与导出.ipynb) | 如何绘制和导出 Graph 结构？ | 已完成 |
| 11 | [LangGraph checkpoint：状态快照到底是什么.ipynb](11%20%7C%20LangGraph%20checkpoint：状态快照到底是什么.ipynb) | 状态快照保存了什么？ | 已完成 |
| 12 | [LangGraph 多轮对话：checkpoint 和 thread_id.ipynb](12%20%7C%20LangGraph%20多轮对话：checkpoint%20和%20thread_id.ipynb) | Checkpoint 与 `thread_id` 如何支撑多轮会话？ | 已完成 |
| 13 | [用 checkpoint 查看、回退和修正 LangGraph 状态.ipynb](13%20%7C%20用%20checkpoint%20查看、回退和修正%20LangGraph%20状态.ipynb) | 如何查看、回退和修改历史状态？ | 已完成 |
| 14 | [LangGraph checkpoint 如何持久化到 Postgres.ipynb](14%20%7C%20LangGraph%20checkpoint%20如何持久化到%20Postgres.ipynb) | 如何把 Checkpoint 持久化到 Postgres？ | 已完成 |
| 15 | [LangGraph Human-in-the-loop：让 Agent 在人工审批后继续执行.ipynb](15%20%7C%20LangGraph%20Human-in-the-loop：让%20Agent%20在人工审批后继续执行.ipynb) | 如何暂停 Agent，在人工审批后继续执行？ | 已完成 |
| 16A | [LangGraph Durable Execution：节点失败后从断点恢复.ipynb](16%20%7C%20LangGraph%20Durable%20Execution：节点失败后从断点恢复.ipynb) | 节点失败后如何从断点恢复？ | 已完成 |
| 16B | [LangGraph 内容安全混合方案：Workflow 与 Agent 的 MVP 实现.md](16%20%7C%20LangGraph%20内容安全混合方案：Workflow%20与%20Agent%20的%20MVP%20实现.md) | Workflow 与 Agent 如何组合成内容安全 MVP？ | 已完成 |
| 17 | [LangGraph 记忆系统：让个人助理跨会话记住用户.ipynb](17%20%7C%20LangGraph%20记忆系统：让个人助理跨会话记住用户.ipynb) | 如何让个人助理跨会话记住用户？ | 已完成 |
| 18 | `LangGraph 生产工程实践：测试、观测与部署.md` | 如何测试、观测并部署可恢复的 LangGraph 工作流？ | 待研究 |
| 20 | [用模型驱动tool loop实现一个最小CityWalk Agent.md](20%20%7C%20用模型驱动tool%20loop实现一个最小CityWalk%20Agent.md) | 如何用模型驱动 tool loop 实现一个最小 CityWalk Agent？ | 已完成 |

## 配套实验

| 文件 | 实验问题 | 状态 |
| --- | --- | --- |
| [experiments/amap_citywalk_tool_loop](experiments/amap_citywalk_tool_loop) | 如何用模型驱动 tool loop 实现一个最小 CityWalk Agent？ | 已完成 |

## 下一步

读完 LangGraph 后，可以继续进入：

- [MCP 实战](../../mcp/foundations)：理解外部工具和上下文能力如何被协议化。
- [LangChain 实战](../../langchain/foundations)：补充模型、工具和 Agent Middleware 的运行时机制。
