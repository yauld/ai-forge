# LangGraph 实战专题

这个专题研究如何用 LangGraph 构建可控、可恢复、可检查的 AI 工作流。从 State、Node 和 Edge 开始，逐步进入条件分支、工具节点、Reducer、Send 并行分发、Command 跳转、Runtime Context、Checkpoint、人工审批、工具调用治理、RAG 接入和跨会话记忆。

LangGraph 的价值不只是“把流程画成图”，而是让复杂 AI 应用具备明确的状态转移、暂停恢复和人工介入边界。

## 你会学到什么

- State、Node、Edge 和 Graph 如何构成工作流。
- 条件边、ToolNode、Reducer 与 Send 如何控制流程、状态合并和并行分发。
- Runtime Context 如何注入本次运行的环境、身份和配置。
- Checkpoint 如何支持多轮对话、回退与持久化。
- Human-in-the-loop 如何介入高风险操作。
- 工具调用如何结合策略限制、错误处理、重试降级和审计日志。
- RAG 问答链路如何拆成检索、上下文整理、回答和 fallback 节点。
- Durable Execution 与长期记忆如何支撑可靠 Agent。

## 适合读者

- 已经理解基本模型调用，准备构建多步骤 AI 流程的人。
- 希望 Agent 具备可恢复、可审计、可人工介入能力的人。
- 想理解生产级 AI Workflow 核心机制的开发者。

## 研究路线

表格同时记录已有成果和后续研究计划。已有文件可直接打开；尚未创建的文件使用计划名称占位。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 00 | [LangGraph系统学习路线.md](LangGraph系统学习路线.md) | LangGraph 的核心概念应该按什么顺序学习？ | 已完成 |
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
| 19 | [用模型驱动tool loop实现一个最小CityWalk Agent.md](19%20%7C%20用模型驱动tool%20loop实现一个最小CityWalk%20Agent.md) | 如何用模型驱动 tool loop 实现一个最小 CityWalk Agent？ | 已完成 |
| 20 | [LangGraph Send：并行分发与 Map-Reduce.md](20%20%7C%20LangGraph%20Send：并行分发与%20Map-Reduce.md) | 如何用 Send 动态分发多个任务，并用 Map-Reduce 汇总结果？ | 已完成 |
| 21 | [LangGraph Command：节点里同时更新状态和决定下一步.md](21%20%7C%20LangGraph%20Command：节点里同时更新状态和决定下一步.md) | 如何在节点里同时更新 State 并决定下一步？ | 已完成 |
| 22 | [LangGraph Runtime Context：不要把配置塞进 State.md](22%20%7C%20LangGraph%20Runtime%20Context：不要把配置塞进%20State.md) | 哪些信息属于业务状态，哪些信息应该作为运行时配置注入？ | 已完成 |
| 23 | [LangGraph 工具调用治理：让工具执行可控、可恢复、可审计.md](23%20%7C%20LangGraph%20工具调用治理：让工具执行可控、可恢复、可审计.md) | 真实业务里的工具调用，如何避免变成模型随意触发的黑箱动作？ | 已完成 |
| 24 | [LangGraph + RAG：把最小问答链路接入图.md](24%20%7C%20LangGraph%20+%20RAG：把最小问答链路接入图.md) | 如何把一个最小 RAG 问答链路拆成 LangGraph 节点，并用 State 串起来？ | 已完成 |
| 25 | [LangGraph 子图：把复杂 Agent 拆成模块.md](25%20%7C%20LangGraph%20子图：把复杂%20Agent%20拆成模块.md) | 如何把复杂流程封装成子图，并观察父图、子图和 checkpoint namespace 的边界？ | 已完成 |

## 配套实验

| 文件 | 实验问题 | 状态 |
| --- | --- | --- |
| [experiments/19_amap_citywalk_tool_loop](experiments/19_amap_citywalk_tool_loop) | 如何用模型驱动 tool loop 实现一个最小 CityWalk Agent？ | 已完成 |
| [experiments/20_asset_risk_map_reduce](experiments/20_asset_risk_map_reduce) | 如何用 Send 把资产风险检查动态分发出去，并用 Map-Reduce 汇总结果？ | 已完成 |
| [experiments/21_command_registration_desk](experiments/21_command_registration_desk) | 如何用 Command 在节点里同时更新 State 并决定下一步？ | 已完成 |
| [experiments/22_runtime_context_cicd](experiments/22_runtime_context_cicd) | 如何用 CI/CD 发布流水线区分 State 与 Runtime Context？ | 已完成 |
| [experiments/23_tool_governance_console](experiments/23_tool_governance_console) | 如何把安全运维工具调用做成可控、可恢复、可审计的治理流程？ | 已完成 |
| [experiments/24_minimal_rag_graph](experiments/24_minimal_rag_graph) | 如何把最小客服 RAG 问答链路接入 LangGraph？ | 已完成 |
| [experiments/25_rag_subgraph_checkpoint](experiments/25_rag_subgraph_checkpoint) | 如何把客服 RAG 封装成子图，并观察 stream 层级和 checkpoint namespace？ | 已完成 |

## 下一步

读完 LangGraph 后，可以继续进入：

- [MCP 实战](../../mcp/foundations)：理解外部工具和上下文能力如何被协议化。
- [LangChain 实战](../../langchain/foundations)：补充模型、工具和 Agent Middleware 的运行时机制。
