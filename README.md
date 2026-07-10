# AI Forge

AI Engineering 实战锻造场。

这个仓库通过文章、Notebook 和可运行示例，持续研究 LangChain、LangGraph、RAG、MCP、Sec for AI、Agent 工程化、记忆、工具调用与安全控制。每个专题的 README 提供专题介绍、学习路线和内容入口。

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/package%20manager-uv-261230)](https://docs.astral.sh/uv/)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C)](https://www.langchain.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.x-1C3C3C)](https://www.langchain.com/langgraph)
[![MCP](https://img.shields.io/badge/MCP-practice-5B5BD6)](https://modelcontextprotocol.io/)

## 专题入口

| 专题 | 研究范围 | 入口 |
| --- | --- | --- |
| LangChain | 模型、Messages、Prompt、Tools、Memory、Agent、Middleware、LCEL、Embeddings | [查看专题](labs/langchain/foundations) |
| LangGraph | State、Node、Edge、Checkpoint、Human-in-the-loop、Durable Execution、Memory | [查看专题](labs/langgraph/foundations) |
| RAG | 文档加载、文本切分、向量库、Retriever、Prompt 与问答链路 | [查看专题](labs/rag/foundations) |
| MCP | Host、Client、Server、Tool、Resource、Prompt、JSON-RPC 与 Transport | [查看专题](labs/mcp/foundations) |
| Sec for AI | 模型、数据、Prompt、RAG、Agent、供应链、安全评测与运行治理 | [查看专题](labs/sec-for-ai/foundations) |
| Skills | Codex Skills、工作流固化与工程自动化 | [查看专题](labs/skills/foundations) |
| Coding | Python、FastAPI 与 AI 工程所需的服务化基础 | [查看内容](labs/coding) |

## 研究内容一览

下面展示各专题的前 10 项内容，帮助你快速了解仓库目前覆盖的问题。完整路线和后续计划请进入对应专题。

### LangChain

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [LangChain开发环境搭建.ipynb](labs/langchain/foundations/01%20%7C%20LangChain开发环境搭建.ipynb) | 如何搭建可运行的 LangChain 开发环境？ | 已完成 |
| 02 | [基于 OpenAI Python SDK的模型接入方式.ipynb](labs/langchain/foundations/02%20%7C%20基于%20OpenAI%20Python%20SDK的模型接入方式.ipynb) | 不使用 LangChain 时，如何通过 OpenAI Python SDK 接入模型？ | 已完成 |
| 03 | [快速体验LangChain.ipynb](labs/langchain/foundations/03%20%7C%20快速体验LangChain.ipynb) | 如何完成第一次 LangChain 模型调用？ | 已完成 |
| 04 | [LangChain推荐的模型创建方式.ipynb](labs/langchain/foundations/04%20%7C%20LangChain推荐的模型创建方式.ipynb) | LangChain 推荐怎样创建和配置模型？ | 已完成 |
| 05 | [LangChain中模型调用的两种方式.ipynb](labs/langchain/foundations/05%20%7C%20LangChain中模型调用的两种方式.ipynb) | 不同模型调用方式分别适合什么场景？ | 已完成 |
| 06 | [LangChain中的消息（Messages）.ipynb](labs/langchain/foundations/06%20%7C%20LangChain中的消息（Messages）.ipynb) | LangChain 如何表示不同角色的消息？ | 已完成 |
| 07 | [LangChain 提示词工程.ipynb](labs/langchain/foundations/07%20%7C%20LangChain%20提示词工程.ipynb) | 如何组织可复用的提示词？ | 已完成 |
| 08 | [LangChain中的工具（Tools）.ipynb](labs/langchain/foundations/08%20%7C%20LangChain中的工具（Tools）.ipynb) | 模型如何发现并调用外部工具？ | 已完成 |
| 09 | [LangChain中的短期记忆（InMemorySaver）.ipynb](labs/langchain/foundations/09%20%7C%20LangChain中的短期记忆（InMemorySaver）.ipynb) | `InMemorySaver` 如何保存对话状态？ | 已完成 |
| 10 | [LangChain中的短期记忆（SqliteSaver与PostgresSaver）.ipynb](labs/langchain/foundations/10%20%7C%20LangChain中的短期记忆（SqliteSaver与PostgresSaver）.ipynb) | SQLite 与 Postgres Saver 如何持久化状态？ | 已完成 |

[查看 LangChain 完整研究路线](labs/langchain/foundations)

### LangGraph

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 00 | [LangGraph系统学习路线.md](labs/langgraph/foundations/00%20%7C%20LangGraph系统学习路线.md) | LangGraph 的核心概念应该按什么顺序学习？ | 已完成 |
| 01 | [LangGraph 入门第一步：从开发环境搭建到可视化跑通.ipynb](labs/langgraph/foundations/01%20%7C%20LangGraph%20入门第一步：从开发环境搭建到可视化跑通.ipynb) | 如何搭建环境并运行第一个可视化 Graph？ | 已完成 |
| 02 | [LangGraph 启动原理：CLI 如何找到并加载 Graph.md](labs/langgraph/foundations/02%20%7C%20LangGraph%20启动原理：CLI%20如何找到并加载%20Graph.md) | LangGraph CLI 如何找到并加载 Graph？ | 已完成 |
| 03 | [LangGraph Studio 数据流：云端界面如何连接本地 Graph.md](labs/langgraph/foundations/03%20%7C%20LangGraph%20Studio%20数据流：云端界面如何连接本地%20Graph.md) | 云端 Studio 如何连接本地 Graph？ | 已完成 |
| 04 | [LangGraph 核心三件套：用一个订单计算器看清Node、State、Edge.md](labs/langgraph/foundations/04%20%7C%20LangGraph%20核心三件套：用一个订单计算器看清Node、State、Edge.md) | 如何用最小例子理解 LangGraph 的核心三件套？ | 已完成 |
| 05 | [LangGraph 常用语法：类型提示与Lambda.ipynb](labs/langgraph/foundations/05%20%7C%20LangGraph%20常用语法：类型提示与Lambda.ipynb) | LangGraph 示例中常见的 Python 语法如何工作？ | 已完成 |
| 06 | [LangGraph 基础骨架：State、Node、Edge、Graph 是什么.ipynb](labs/langgraph/foundations/06%20%7C%20LangGraph%20基础骨架：State、Node、Edge、Graph%20是什么.ipynb) | State、Node、Edge 和 Graph 如何组成完整流程？ | 已完成 |
| 07 | [LangGraph 条件边：让流程根据 State 分支.ipynb](labs/langgraph/foundations/07%20%7C%20LangGraph%20条件边：让流程根据%20State%20分支.ipynb) | 如何根据 State 动态选择流程分支？ | 已完成 |
| 08 | [LangGraph 工具节点：tools、ToolNode、Runnable 是什么.ipynb](labs/langgraph/foundations/08%20%7C%20LangGraph%20工具节点：tools、ToolNode、Runnable%20是什么.ipynb) | Tools、ToolNode 与 Runnable 如何协作？ | 已完成 |
| 09 | [LangGraph 状态更新与 Reducer.ipynb](labs/langgraph/foundations/09%20%7C%20LangGraph%20状态更新与%20Reducer.ipynb) | 并发或连续更新时如何合并 State？ | 已完成 |
| 10 | [Graphviz 与 LangGraph：安装、绘图与导出.ipynb](labs/langgraph/foundations/10%20%7C%20Graphviz%20与%20LangGraph：安装、绘图与导出.ipynb) | 如何绘制和导出 Graph 结构？ | 已完成 |

[查看 LangGraph 完整研究路线](labs/langgraph/foundations)

### RAG

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [RAG基础通识.md](labs/rag/foundations/01%20%7C%20RAG基础通识.md) | RAG 解决什么问题，完整链路包含哪些环节？ | 已完成 |
| 02 | [向量基础通识.md](labs/rag/foundations/02%20%7C%20向量基础通识.md) | 文本为什么可以表示成向量？ | 已完成 |
| 03 | [余弦相似度到底在算什么.md](labs/rag/foundations/03%20%7C%20余弦相似度到底在算什么.md) | 余弦相似度究竟在比较什么？ | 已完成 |
| 04 | [RAG中的CSV文档加载（CSVLoader）.ipynb](labs/rag/foundations/04%20%7C%20RAG中的CSV文档加载（CSVLoader）.ipynb) | 如何把 CSV 数据转换成文档？ | 已完成 |
| 05 | [RAG中的JSON文档加载（JSONLoader）.ipynb](labs/rag/foundations/05%20%7C%20RAG中的JSON文档加载（JSONLoader）.ipynb) | 如何读取和组织 JSON 文档？ | 已完成 |
| 06 | [RAG主流文档加载器速查（PDF、Text、Markdown、目录）.ipynb](labs/rag/foundations/06%20%7C%20RAG主流文档加载器速查（PDF、Text、Markdown、目录）.ipynb) | PDF、Text、Markdown 和目录应该如何加载？ | 已完成 |
| 07 | [RAG文档切分 Text Splitter.ipynb](labs/rag/foundations/07%20%7C%20RAG文档切分%20Text%20Splitter.ipynb) | 文档为什么要切分，常见切分策略如何选择？ | 已完成 |
| 08 | [RAG向量库的增删查与持久化.ipynb](labs/rag/foundations/08%20%7C%20RAG向量库的增删查与持久化.ipynb) | 如何完成向量数据的增删查与持久化？ | 已完成 |
| 09 | [RAG Retriever 检索器.ipynb](labs/rag/foundations/09%20%7C%20RAG%20Retriever%20检索器.ipynb) | 检索器如何从向量库取回相关上下文？ | 已完成 |
| 10 | [RAG最小问答链路：Prompt组装与LLM调用.ipynb](labs/rag/foundations/10%20%7C%20RAG最小问答链路：Prompt组装与LLM调用.ipynb) | 如何把检索结果、Prompt 和 LLM 组成最小 RAG？ | 已完成 |

[查看 RAG 完整研究路线](labs/rag/foundations)

### MCP

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [MCP 是什么：先把它放回 AI 应用架构里理解.md](labs/mcp/foundations/01%20%7C%20MCP%20是什么：先把它放回%20AI%20应用架构里理解.md) | MCP 到底是什么，解决了什么连接问题？ | 已完成 |
| 02 | [MCP 架构：从一次订单分析看懂 Host、Client、Server.md](labs/mcp/foundations/02%20%7C%20MCP%20架构：从一次订单分析看懂%20Host、Client、Server.md) | Host、Client、Server 如何在一次订单分析中协作？ | 已完成 |
| 03 | [MCP Tool、Resource、Prompt：从会用到会设计.md](labs/mcp/foundations/03%20%7C%20MCP%20Tool、Resource、Prompt：从会用到会设计.md) | 一个能力应该设计成哪种 Server Primitive？ | 已完成 |
| 04 | [MCP 通信过程：从 initialize 到 tools-call.ipynb](labs/mcp/foundations/04%20%7C%20MCP%20通信过程：从%20initialize%20到%20tools-call.ipynb) | 从 `initialize` 到 `tools/call`，MCP 消息如何流动？ | 已完成 |
| 05 | [MCP Transport：stdio 与 Streamable HTTP 如何传递消息.md](labs/mcp/foundations/05%20%7C%20MCP%20Transport：stdio%20与%20Streamable%20HTTP%20如何传递消息.md) | 同一组消息如何通过 stdio 和 Streamable HTTP 传递？ | 已完成 |
| 06 | [MCP Client：Host 如何发现并调用 Server 能力.md](labs/mcp/foundations/06%20%7C%20MCP%20Client：Host%20如何发现并调用%20Server%20能力.md) | Host 如何发现多个 Server 的能力并正确路由调用？ | 已完成 |
| 07 | [MCP 调试：从 Server 启动失败到 Tool 调用异常.md](labs/mcp/foundations/07%20%7C%20MCP%20调试：从%20Server%20启动失败到%20Tool%20调用异常.md) | 如何按进程、Transport、生命周期、能力发现和执行逐层定位失败？ | 已完成 |
| 08 | [MCP 输入安全：参数限制、Schema 与数据最小化.md](labs/mcp/foundations/08%20%7C%20MCP%20输入安全：参数限制、Schema%20与数据最小化.md) | Tool 如何限制输入范围和返回数据？ | 已完成 |
| 09 | [MCP Host 权限：Tool 白名单与危险操作确认.md](labs/mcp/foundations/09%20%7C%20MCP%20Host%20权限：Tool%20白名单与危险操作确认.md) | Host 何时允许 MCP Client 发送 Tool 调用？ | 已完成 |
| 10 | [MCP 执行安全：业务边界、幂等与重复调用.md](labs/mcp/foundations/10%20%7C%20MCP%20执行安全：业务边界、幂等与重复调用.md) | Server 如何约束危险操作的真实副作用？ | 已完成 |

[查看 MCP 完整研究路线](labs/mcp/foundations)

### Sec for AI

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [间接 Prompt Injection：业务数据如何变成指令.md](labs/sec-for-ai/foundations/01%20%7C%20间接%20Prompt%20Injection：业务数据如何变成指令.md) | 外部业务数据如何诱导模型提出危险 Tool 调用并造成真实副作用？ | 已完成 |

[查看 Sec for AI 完整研究路线](labs/sec-for-ai/foundations)

### Skills

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [Skills 的定位：它在 Agent 架构中解决什么问题.md](labs/skills/foundations/01%20%7C%20Skills%20的定位：它在%20Agent%20架构中解决什么问题.md) | Skills 到底应该放在 Agent 架构的哪一层？ | 已完成 |
| 02 | [最小 SKILL.md：一个 Skill 如何被发现和使用.md](labs/skills/foundations/02%20%7C%20最小%20SKILL.md：一个%20Skill%20如何被发现和使用.md) | 一个最小 `SKILL.md` 至少要写清哪些内容，才能被发现和使用？ | 已完成 |
| 03 | [Skill 的两种常见设计形态：Action 与 Reference.md](drafts/skills/03%20%7C%20Skill%20的两种常见设计形态：Action%20与%20Reference.md) | Action 与 Reference 分别适合承载什么内容，如何组合？ | 已完成 |
| 05 | [教学用 Skills runtime：扫描、路由、加载、执行如何分工.md](labs/skills/foundations/05%20%7C%20教学用%20Skills%20runtime：扫描、路由、加载、执行如何分工.md) | 一个支持 Skills 的最小 runtime 应该如何拆分扫描、路由、加载、执行和记录？ | 已完成 |

[查看 Skills 完整研究路线](labs/skills/foundations)

## 本地复现实验（可选）

文章和 Notebook 可以直接在线阅读，无需安装本地环境。

如果你希望运行 Notebook 或复现示例，本仓库要求 Python 3.13 或更高版本，并使用 uv 管理依赖：

```bash
uv sync
uv run jupyter notebook
```

不同实验可能有额外启动参数，请查看对应专题说明。例如：[MCP README](labs/mcp/foundations/README.md)。

## 公众号

公众号用于发布更短、更聚焦的文章版本；仓库保留完整实验和持续更新的研究记录。

已整理的公众号稿按专题收录，例如 [Skills 公众号稿](drafts/skills)。

<p align="center">
  <img src="assets/wechat-qr.jpg" width="220" alt="公众号二维码">
</p>
