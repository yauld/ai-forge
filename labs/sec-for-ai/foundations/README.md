# Sec for AI 实战专题

这个专题研究 AI 和 AI 应用本身的安全问题，覆盖模型、数据、Prompt、RAG、Agent、工具调用、供应链和运行治理。

Sec for AI（Security for AI）关注“如何保护 AI 系统”；AI for Security 关注“如何用 AI 解决安全问题”。本专题属于前者。

## 你会学到什么

- AI 系统面临哪些攻击面，如何建立威胁模型。
- Prompt Injection、越狱和不可信内容如何影响模型行为。
- 训练数据、用户数据、上下文和日志如何避免泄露或污染。
- RAG、Agent 和 Tool 为什么会引入新的权限与执行风险。
- 模型、依赖、插件和外部服务的供应链如何建立信任。
- 如何通过安全评测、红队测试、监控和审计持续验证防护效果。

## 适合读者

- 构建大模型、RAG、Agent 或 AI 平台的开发者。
- 研究 AI 安全、应用安全和数据安全的工程师。
- 希望系统理解 AI 风险与防护方法的人。

## 研究路线

当前只列已经完成并可直接打开的内容。

| 序号 | 文件 | 研究问题 | 状态 |
| --- | --- | --- | --- |
| 01 | [间接 Prompt Injection：业务数据如何变成指令.md](01%20%7C%20间接%20Prompt%20Injection：业务数据如何变成指令.md) | 外部业务数据如何诱导模型提出危险 Tool 调用并造成真实副作用？ | 已完成 |

完整选题规划记录在 [Sec for AI 内容路线图](../../../drafts/sec-for-ai/sfa_roadmap.md)。

## 示例项目

示例代码集中在 [examples](examples)。第 01 篇使用 MCP 作为 Agent 连接业务能力的实验载体，但研究问题属于 Sec for AI：外部业务数据如何影响模型工具调用意图，以及 Host 如何约束真实副作用。

| 文件 | 作用 |
| --- | --- |
| [support_portal.py](examples/support_portal.py) | 模拟外部客户通过公开售后表单提交不可信问题描述。 |
| [indirect_injection_server.py](examples/indirect_injection_server.py) | 提供读取订单、退款和退款执行计数 Tool。 |
| [indirect_injection_host.py](examples/indirect_injection_host.py) | 使用本地真实模型运行间接 Prompt Injection 场景，对比 Host 放行后的退款副作用与关闭确认后的拦截结果。 |
| [security_order_data.py](examples/security_order_data.py) | 为安全实验重置独立的订单样例数据库。 |

## 研究原则

- 同时研究模型风险和应用工程风险。
- 用对抗性输入验证边界，不只演示正常路径。
- 区分缓解措施与确定性安全控制。
- 涉及真实副作用时，回查最终状态和审计证据。
