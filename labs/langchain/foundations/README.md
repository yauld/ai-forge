# LangChain 实战专题

这个专题从模型接入开始，逐步研究 Messages、Prompt、Tools、Memory、Agent 和 Middleware，目标是理解 LangChain 如何把模型能力组织成可控制的 AI 应用。

这里既包含基础接口实验，也包含失败兜底、人工审批、敏感信息脱敏和上下文管理等 Agent 工程化问题。

## 你会学到什么

- 如何通过 OpenAI Python SDK 和 LangChain 接入模型。
- Messages、Prompt、Tools 与 LCEL 如何协作。
- 短期记忆与长期记忆分别解决什么问题。
- Agent 的 ReAct 过程如何运行。
- Middleware 如何限制、拦截和修正 Agent 行为。

## 适合读者

- 想系统理解 LangChain 基础接口的开发者。
- 正在把 LLM 接入真实业务系统的人。
- 想从“能调用模型”继续走向“能控制 Agent”的实践者。

## 研究路线

表格同时记录已有成果和后续研究计划。已有文件可直接打开；尚未创建的文件使用计划名称占位。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [LangChain开发环境搭建.ipynb](01%20%7C%20LangChain开发环境搭建.ipynb) | 如何搭建可运行的 LangChain 开发环境？ | 已完成 |
| 02 | [基于 OpenAI Python SDK的模型接入方式.ipynb](02%20%7C%20基于%20OpenAI%20Python%20SDK的模型接入方式.ipynb) | 不使用 LangChain 时，如何通过 OpenAI Python SDK 接入模型？ | 已完成 |
| 03 | [快速体验LangChain.ipynb](03%20%7C%20快速体验LangChain.ipynb) | 如何完成第一次 LangChain 模型调用？ | 已完成 |
| 04 | [LangChain推荐的模型创建方式.ipynb](04%20%7C%20LangChain推荐的模型创建方式.ipynb) | LangChain 推荐怎样创建和配置模型？ | 已完成 |
| 05 | [LangChain中模型调用的两种方式.ipynb](05%20%7C%20LangChain中模型调用的两种方式.ipynb) | 不同模型调用方式分别适合什么场景？ | 已完成 |
| 06 | [LangChain中的消息（Messages）.ipynb](06%20%7C%20LangChain中的消息（Messages）.ipynb) | LangChain 如何表示不同角色的消息？ | 已完成 |
| 07 | [LangChain 提示词工程.ipynb](07%20%7C%20LangChain%20提示词工程.ipynb) | 如何组织可复用的提示词？ | 已完成 |
| 08 | [LangChain中的工具（Tools）.ipynb](08%20%7C%20LangChain中的工具（Tools）.ipynb) | 模型如何发现并调用外部工具？ | 已完成 |
| 09 | [LangChain中的短期记忆（InMemorySaver）.ipynb](09%20%7C%20LangChain中的短期记忆（InMemorySaver）.ipynb) | `InMemorySaver` 如何保存对话状态？ | 已完成 |
| 10 | [LangChain中的短期记忆（SqliteSaver与PostgresSaver）.ipynb](10%20%7C%20LangChain中的短期记忆（SqliteSaver与PostgresSaver）.ipynb) | SQLite 与 Postgres Saver 如何持久化状态？ | 已完成 |
| 11 | [LangChain中的长期记忆（Store与Cross-Thread）.ipynb](11%20%7C%20LangChain中的长期记忆（Store与Cross-Thread）.ipynb) | Store 与 Cross-Thread Memory 如何支持跨会话记忆？ | 已完成 |
| 12 | [把资产中心接入大模型：一个安全Agent的最小闭环.md](12%20%7C%20把资产中心接入大模型：一个安全Agent的最小闭环.md) | 如何把资产中心安全地接入大模型？ | 已完成 |
| 13 | [LangChain Embeddings：从文本向量化到语义检索.ipynb](13%20%7C%20LangChain%20Embeddings：从文本向量化到语义检索.ipynb) | 如何从文本向量化走到语义检索？ | 已完成 |
| 14 | [LangChain LCEL：从模型输出到业务动作.ipynb](14%20%7C%20LangChain%20LCEL：从模型输出到业务动作.ipynb) | 如何把模型输出连接到后续业务动作？ | 已完成 |
| 15 | [LangChain中的短期记忆（RunnableWithMessageHistory）.ipynb](15%20%7C%20LangChain中的短期记忆（RunnableWithMessageHistory）.ipynb) | `RunnableWithMessageHistory` 如何管理短期记忆？ | 已完成 |
| 16 | [Agent ReAct：看一次完整的思考、行动和观察过程.ipynb](16%20%7C%20Agent%20ReAct:看一次完整的思考、行动和观察过程.ipynb) | Agent 的思考、行动与观察过程如何流转？ | 已完成 |
| 17 | [LangChain：为什么 Agent 需要Middleware.ipynb](17%20%7C%20LangChain：为什么%20Agent%20需要Middleware.ipynb) | 为什么 Agent 需要运行时约束？ | 已完成 |
| 18 | [LangChain Middleware：限制Agent别疯跑.ipynb](18%20%7C%20LangChain%20Middleware：限制Agent别疯跑.ipynb) | 如何限制 Agent 的运行次数和失控循环？ | 已完成 |
| 19 | [LangChain Middleware：模型和工具失败时怎么兜底.ipynb](19%20%7C%20LangChain%20Middleware：模型和工具失败时怎么兜底.ipynb) | 模型或工具失败时如何降级处理？ | 已完成 |
| 20 | [LangChain Middleware：关键工具调用前先让人点头.ipynb](20%20%7C%20LangChain%20Middleware：关键工具调用前先让人点头.ipynb) | 如何在高风险工具调用前要求人工确认？ | 已完成 |
| 21 | [LangChain Middleware：敏感信息进入模型前，先脱敏.ipynb](21%20%7C%20LangChain%20Middleware：敏感信息进入模型前，先脱敏.ipynb) | 如何在信息进入模型前完成脱敏？ | 已完成 |
| 22 | [LangChain Middleware：对话太长，先总结再继续聊.ipynb](22%20%7C%20LangChain%20Middleware：对话太长，先总结再继续聊.ipynb) | 上下文过长时如何先总结再继续？ | 已完成 |
| 23 | [LangChain Middleware：清理旧工具结果，别让上下文越滚越胖.ipynb](23%20%7C%20LangChain%20Middleware：清理旧工具结果，别让上下文越滚越胖.ipynb) | 如何清理旧工具结果以控制上下文规模？ | 已完成 |
| 24 | [LangChain 自定义 Middleware：让 Agent 按工程规则办事.ipynb](24%20%7C%20LangChain%20自定义%20Middleware：让%20Agent%20按工程规则办事.ipynb) | 如何让 Agent 遵守自定义工程规则？ | 已完成 |
| 25 | [LangChain Middleware：自定义拦截逻辑背后的 request 和 handler.ipynb](25%20%7CLangChain%20Middleware：自定义拦截逻辑背后的%20request%20和%20handler.ipynb) | 自定义拦截逻辑中的 request 和 handler 如何协作？ | 已完成 |
| 26 | [LangChain Middleware：state 和 runtime 到底是什么.ipynb](26%20%7C%20LangChain%20Middleware：state%20和%20runtime%20到底是什么.ipynb) | Middleware 中的 state 和 runtime 分别是什么？ | 已完成 |
| 27 | [LangChain Middleware：dynamic_prompt动态切换提示词.ipynb](27%20%7C%20LangChain%20Middleware：dynamic_prompt动态切换提示词.ipynb) | 如何根据运行上下文动态切换提示词？ | 已完成 |
| 28 | `LangChain 生产工程实践：测试、观测与部署.md` | 如何把现有能力组合成可观测、可测试的真实应用？ | 待研究 |

## 下一步

读完 LangChain 后，可以继续进入：

- [LangGraph 实战](../../langgraph/foundations)：把 AI 应用组织成可控、可恢复的状态图。
- [RAG 实战](../../rag/foundations)：补齐知识检索链路。
- [MCP 实战](../../mcp/foundations)：理解外部工具和上下文能力如何被协议化。
