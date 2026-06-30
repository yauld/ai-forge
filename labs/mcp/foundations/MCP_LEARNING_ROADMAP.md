# MCP 学习路线

这份路线用于在当前项目目录内系统学习 Model Context Protocol（MCP）。

当前基准日期：2026-06-28。

官方信息源：https://modelcontextprotocol.io

## 学习目标

完成这条路线后，你应该能够：

- 解释 MCP 在 AI 应用架构中的位置，以及它解决的问题。
- 区分 MCP Host、MCP Client 和 MCP Server 的职责。
- 为真实业务正确设计 tools、resources 和 prompts。
- 读懂 MCP 的 JSON-RPC 消息、连接生命周期和能力协商。
- 使用 stdio 和 Streamable HTTP 连接 MCP servers。
- 构建、测试和调试一个 MCP server 与一个基础 MCP client。
- 在接入真实凭据或生产数据前识别常见安全风险。

## 学习原则

- 整条路线尽量复用订单分析项目，不为每个概念重新造一套示例。
- 每一阶段都回答一个明确问题，并产出一篇文章或一个可运行实验。
- 学习顺序遵循：能力设计 → 协议消息 → Transport → Client → 工程化 → 安全。
- SDK 用来提高开发效率，但不能代替对协议消息和职责边界的理解。
- 涉及版本、API、transport 或安全行为时，以当前 MCP 官方文档为准。

## 当前进度

### 阶段 1：理解 MCP 是什么（已完成）

对应文章：

- `01 | MCP 是什么：先把它放回 AI 应用架构里理解.md`

已经覆盖：

- MCP 解决的问题，以及它在 AI 应用架构中的位置。
- MCP 连接的是 AI 应用与外部上下文，而不是模型与数据库。
- Host、Client、Server 的基本直觉。
- tools、resources、prompts 的初步区别。
- 适合与不适合使用 MCP 的场景。

检查点：

- 可以不用 SDK 术语，用一段话解释 MCP。
- 可以举出一个适合 MCP 的场景和一个没必要使用 MCP 的场景。

### 阶段 2：理解架构职责与连接生命周期（已完成）

对应材料：

- `02 | MCP 架构：从一次订单分析看懂 Host、Client、Server.md`
- `examples/shop_order_analysis_server.py`

已经覆盖：

- Host、Client、Server 的职责边界。
- 一个 Host 如何通过 Client 连接 Server。
- `initialize`、能力协商和 `notifications/initialized`。
- Inspector 如何发现并使用 resources、prompts 和 tools。
- 模型表达调用意图、Host 决策、Client 发起调用、Server 执行之间的边界。

检查点：

- 可以画出一个 Host 连接多个 Servers 的架构图。
- 可以解释为什么 Host 要按 server 管理 capabilities 和 primitives。
- 可以用 Inspector 连接订单分析 Server，并读取资源、获取 prompt、调用 tool。

## 后续主线

### 阶段 3：深入 Server Primitives（已完成）

核心问题：一个能力什么时候应该设计成 tool、resource 或 prompt？

对应文章：

- `03 | MCP Tool、Resource、Prompt：从会用到会设计.md`

继续扩展订单分析项目：

- 固定 Resource：订单字段说明或状态字典。
- Resource Template：按订单编号读取订单详情。
- Tool：查询订单、生成统计；可选加入带副作用的操作。
- Prompt：订单日报或异常分析模板。

学习内容：

- Tools：输入 schema、输出内容、结构化结果、输入校验和副作用边界。
- Resources：URI、MIME type、固定资源和参数化资源模板。
- Prompts：参数、消息模板，以及它与普通用户提示词的区别。
- `tools/list`、`resources/list`、`resources/templates/list`、`prompts/list`。
- `tools/call`、`resources/read`、`prompts/get`。
- Tool 的协议错误、输入错误和业务失败如何区分。
- `listChanged` capability 与列表变化通知。

实践任务：

1. 为订单详情增加 Resource Template。
2. 为 Tool 分别测试合法输入、非法输入和查无订单。
3. 比较“读取订单详情”设计成 resource 和 tool 时的差异。
4. 在 Inspector 中观察三种 primitive 暴露的元数据。

检查点：

- 可以根据读取、执行、复用模板等语义选择合适的 primitive。
- 可以描述“发现并调用一个 tool”的完整过程。
- 可以解释 schema 不只是文档，也参与 Host、模型和 Server 之间的协作。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- https://modelcontextprotocol.io/specification/2025-11-25/server/resources
- https://modelcontextprotocol.io/specification/2025-11-25/server/prompts

### 阶段 4：读懂 JSON-RPC 与 MCP 生命周期（已完成）

核心问题：Inspector 点击一次按钮后，Client 和 Server 实际交换了什么消息？

对应文章：

- `04 | MCP 通信过程：从 initialize 到 tools-call.ipynb`

这阶段改用 Notebook，把文章讲解和分步实验放在同一个文件里。

学习内容：

- JSON-RPC request、response 和 notification 的区别。
- `jsonrpc`、`id`、`method`、`params`、`result` 和 `error`。
- `initialize` 请求和响应的具体结构。
- 为什么 `notifications/initialized` 是 notification。
- 为什么初始化完成后才能进行 primitive discovery。
- `tools/list`、`tools/call`、`resources/read`、`prompts/get` 的消息形态。
- pagination、cursor、取消和列表变化通知。
- MCP 协议错误与 tool 执行结果中的业务错误。

建议实验：

```text
initialize
→ initialize response
→ notifications/initialized
→ tools/list
→ tools/call
→ call result
```

保存并注释一组真实消息，逐个标出调用方向、消息类型和关键字段。

检查点：

- 可以判断一段消息是请求、响应还是通知。
- 可以根据相同的 `id` 配对请求与响应。
- 可以解释初始化和能力协商解决了什么问题。
- 即使 SDK 调用失败，也知道应该查看哪一层消息。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/basic/index
- https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
- https://modelcontextprotocol.io/specification/2025-11-25/server/utilities/pagination

### 阶段 5：理解 Transports

核心问题：同样的 MCP 消息如何在本地进程与远程服务之间传递？

建议文章：

- `05 | MCP Transport：stdio 与 Streamable HTTP 如何传递消息.md`

学习内容：

- Data layer 与 Transport layer 的边界。
- stdio 的进程启动、标准输入输出和消息 framing。
- 为什么本地文件、数据库或开发工具类 Server 常使用 stdio。
- Streamable HTTP 的请求、响应、session 与流式消息。
- 为什么远程 Server 需要额外考虑认证、授权和网络边界。
- 本地部署与远程部署的选择依据。

实践任务：

1. 画出 Host 启动 stdio Server 的进程关系。
2. 观察 Server 把普通日志写入 stdout 后会发生什么。
3. 在保持业务能力不变的前提下，为订单 Server 增加 HTTP 运行方式。
4. 比较两种 transport 下没有改变的协议层内容。

检查点：

- 可以解释 JSON-RPC 与 transport 各自负责什么。
- 可以解释为什么 stdio Server 必须谨慎使用 stdout。
- 可以根据部署位置、信任边界和访问方式选择 transport。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports

### 阶段 6：构建一个基础 MCP Client

核心问题：Host 如何发现 Server 能力，并把调用路由到正确的连接？

建议文章：

- `06 | MCP Client：Host 如何发现并调用 Server 能力.md`

构建内容：

- 启动并连接订单分析 Server。
- 完成初始化与能力协商。
- 列出 tools、resources 和 prompts。
- 调用订单查询 Tool。
- 读取一个 Resource 并获取一个 Prompt。
- 正确关闭连接与子进程。
- 再连接一个简单 Server，按 server 保存能力并路由调用。

学习内容：

- Client session 的生命周期。
- capability 检查。
- 多 Server 场景下的命名、冲突和路由。
- 超时、取消、断开与资源清理。
- Host 如何把 Tool 描述交给模型，又如何验证和执行模型产生的调用意图。

检查点：

- 可以独立编写一个连接本地 Server 并调用 Tool 的小型 Client。
- 可以解释为什么一个 Host 通常为每个 Server 维护独立 Client 连接。
- 可以把某个 tool call 路由到正确的 Server，而不是只维护一张无来源的工具列表。

推荐官方页面：

- https://modelcontextprotocol.io/docs/develop/build-client
- https://modelcontextprotocol.io/docs/develop/clients/client-best-practices

### 阶段 7：错误处理与调试

核心问题：一次 MCP 调用失败时，如何快速判断问题发生在哪一层？

建议文章：

- `07 | MCP 调试：从 Server 启动失败到 Tool 调用异常.md`

学习内容：

- Server 进程启动失败。
- transport 建连失败。
- 初始化或能力协商失败。
- primitive discovery 与 schema 错误。
- 输入校验、业务错误、超时和取消。
- logs、Inspector 和原始协议消息的分工。
- 可观测性与敏感信息脱敏。

实践任务：

人为制造并定位以下故障：

1. Server 启动命令错误。
2. stdout 混入普通日志。
3. Tool schema 与实现不一致。
4. Tool 收到非法参数。
5. 数据库查询超时或业务对象不存在。

检查点：

- 可以按“进程 → transport → lifecycle → discovery → execution”逐层排查。
- 可以区分 JSON-RPC error、协议错误和 Tool 返回的业务失败。
- 可以用 Inspector 复现问题，并找到足够小的失败证据。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tools/inspector
- https://modelcontextprotocol.io/docs/tools/debugging

### 阶段 8：安全与授权

核心问题：当 Server 能访问真实文件、账户或服务时，谁有权做什么？

建议文章：

- `08 | MCP 安全：权限、授权与危险 Tool 的确认边界.md`

学习内容：

- 本地 Server 的代码信任与进程权限。
- 最小权限、路径限制和敏感操作确认。
- Prompt injection 对 tool 调用与资源读取的影响。
- OAuth 与远程 Server authorization flow。
- token passthrough、confused deputy、SSRF 和 session hijacking。
- scope minimization、凭据存储、撤销与审计。

实践任务：

1. 为订单查询限定可接受的参数和值域。
2. 如果增加退款 Tool，要求明确确认并设计幂等机制。
3. 检查日志和错误信息是否泄露订单或凭据。
4. 为远程 Server 画出用户、Host、Server 与授权服务的信任边界。

检查点：

- 可以列出权限过宽的 MCP Server 带来的风险。
- 可以解释为什么模型提出调用不等于 Host 应当直接执行。
- 可以为只读与有副作用的能力设计不同的授权和确认策略。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tutorials/security/authorization
- https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices

## 可选进阶：Registry、Extensions 与生态

核心问题：哪些能力属于 MCP 核心协议，哪些属于扩展或特定 Client？

这部分不阻塞主线，可以在掌握 Client 和安全基础后按需学习：

- 官方 MCP Registry 与 Server 发布。
- 已发布 Server 的版本管理。
- MCP Apps。
- Tasks 等 extensions。
- Client extension support matrix。
- Specification Enhancement Proposals（SEPs）。
- 如何判断旧文章中的能力是否仍然有效。

检查点：

- 可以判断一个能力属于核心协议、extension、experimental、deprecated，还是某个 Client 的特定行为。
- 可以根据协议版本和官方资料评估旧教程。

推荐官方页面：

- https://modelcontextprotocol.io/registry/about
- https://modelcontextprotocol.io/extensions/overview
- https://modelcontextprotocol.io/extensions/client-matrix
- https://modelcontextprotocol.io/seps/index
- https://modelcontextprotocol.io/docs/learn/versioning

## 贯穿路线的实践项目

不再单独重复构建一个 `echo` Server。现有订单分析项目已经覆盖最小 Server 的核心结构，后续围绕它逐步演进：

1. 能力设计阶段：补充 Resource Template、输入校验和失败路径。
2. 协议阶段：记录并注释真实 JSON-RPC 消息。
3. Transport 阶段：在 stdio 之外增加 Streamable HTTP 实验。
4. Client 阶段：编写基础 Client，并连接第二个简单 Server 验证路由。
5. 调试阶段：构造启动、协议、schema 和业务故障。
6. 安全阶段：增加只读边界、敏感操作确认和最小权限设计。

完成主线后，再选择一个真实项目：

- 文件读取 Server：只暴露固定目录，并防止路径穿越。
- 笔记或文章助手：把文章暴露为 resources，并提供 review prompts。
- 公开 API 包装 Server：处理 timeout、rate limit 和结构化错误。
- 带认证的远程 Server：只在完成安全阶段后实现。

## 推荐学习节奏

每个阶段都按同一个循环推进：

1. 先提出本阶段要回答的核心问题。
2. 在现有订单项目中做一个最小实验。
3. 用 Inspector 或自建 Client 观察真实行为。
4. 回到协议文档解释观察结果。
5. 写成文章，并删除与前文重复的背景说明。
6. 用检查点确认自己能否脱离代码复述关键机制。

下一步从阶段 5 开始：

> 比较同一组 JSON-RPC 消息如何通过 stdio 和 Streamable HTTP 传递，理解协议层与 transport 层的边界。
