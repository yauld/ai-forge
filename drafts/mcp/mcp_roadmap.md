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

### 阶段 5：理解 Transports（已完成）

核心问题：同样的 MCP 消息如何在本地进程与远程服务之间传递？

对应材料：

- GitHub 完整文章：`labs/mcp/foundations/05 | MCP Transport：stdio 与 Streamable HTTP 如何传递消息.md`
- 公众号精简稿：`drafts/mcp/05 | MCP 消息是怎么传过去的：stdio 与 Streamable HTTP.md`
- 配图：`drafts/mcp/assets/05-transport-stdio-vs-http.svg`
- 实验代码：
  - `labs/mcp/foundations/examples/shop_order_transport_server.py`
  - `labs/mcp/foundations/examples/transport_client.py`
  - `labs/mcp/foundations/examples/broken_stdout_server.py`

学习内容：

- Data layer 与 Transport layer 的边界。
- stdio 的进程启动、标准输入输出和消息 framing。
- 为什么本地文件、数据库或开发工具类 Server 常使用 stdio。
- Streamable HTTP 的 HTTP endpoint、请求与响应。
- session、流式推送、HTTP header 等细节只建立基本印象。
- 为什么 HTTP Server 会额外带来网络边界。
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

### 阶段 7：错误处理与调试（已完成）

核心问题：一次 MCP 调用失败时，如何快速判断问题发生在哪一层？

对应材料：

- `labs/mcp/foundations/07 | MCP 调试：从 Server 启动失败到 Tool 调用异常.md`
- `drafts/mcp/07 | MCP 调试指南：调用失败，到底该从哪一层查？.md`

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

### 阶段 8：Tool 输入安全（已完成）

核心问题：MCP Server 如何限制调用者能传入什么，以及能够读走多少数据？

对应材料：

- `labs/mcp/foundations/08 | MCP 输入安全：参数限制、Schema 与数据最小化.md`
- `drafts/mcp/08 | MCP 输入安全：Tool Schema、SQL 参数绑定与数据最小化.md`
- `drafts/mcp/assets/08-mcp-input-security-boundaries.svg`
- `labs/mcp/foundations/examples/input_security_server.py`
- `labs/mcp/foundations/examples/input_security_client.py`

实践任务：

1. 用枚举限制订单状态。
2. 用上下界限制查询数量。
3. 提交非法状态、SQL 注入式文本、`limit=0` 和 `limit=10000`。
4. 用执行计数证明非法参数没有进入查询函数。
5. 单独验证 SQL 参数绑定不会让注入式文本改变查询结构。
6. 检查返回数量和字段集合。

检查点：

- 可以区分合法边界值与越界输入。
- 可以解释 schema 校验、SQL 参数绑定和数据最小化各自解决什么问题。
- 可以用可观察证据证明输入边界实际生效。

### 阶段 9：Host 权限与危险操作确认（已完成）

核心问题：模型提出 Tool 调用后，Host 在什么条件下才允许 MCP Client 发送请求？

对应材料：

- `labs/mcp/foundations/09 | MCP Host 权限：Tool 白名单与危险操作确认.md`
- `drafts/mcp/09 | MCP Host 权限：模型提出 Tool 调用，不等于获得执行权.md`
- `drafts/mcp/assets/09-mcp-host-permission-gates.svg`
- `labs/mcp/foundations/examples/host_permission_server.py`
- `labs/mcp/foundations/examples/host_permission_host.py`

实践任务：

1. 发现 Tool 和风险 annotations。
2. 拒绝 Host 未审核的 Tool。
3. 拒绝未获得用户确认的退款建议。
4. 拒绝模型伪造的 `user_confirmed` 参数。

检查点：

- 可以解释模型、Host、MCP Client、Server 和 Tool 的职责关系。
- 可以证明 `blocked_before_call` 发生在请求离开 Host 之前。
- 可以解释为什么 annotations 和模型参数不能代替用户授权。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/server/tools

### 阶段 10：Server 执行安全（已完成）

核心问题：请求到达 Server 后，业务系统根据什么规则执行或拒绝危险操作？

对应材料：

- `labs/mcp/foundations/10 | MCP 执行安全：业务边界、幂等与重复调用.md`
- `labs/mcp/foundations/examples/execution_security_server.py`
- `labs/mcp/foundations/examples/execution_security_client.py`

实践任务：

1. 拒绝不存在、状态不允许和金额超限的订单。
2. 用相同幂等键模拟网络重试。
3. 尝试把已使用的幂等键换绑到另一笔订单。
4. 每次拒绝后回查订单最终状态，并检查重试只写入一条退款记录。

检查点：

- 可以区分 Host 确认与 Server 业务授权。
- 可以为有副作用 Tool 设计对象、状态、金额和幂等边界。

### 阶段 11：内容与审计安全（已完成）

核心问题：外部内容中的恶意指令能否影响 Tool 调用，审计又应保留哪些信息？

对应材料：

- `labs/mcp/foundations/11 | MCP 内容安全：Prompt Injection、审计与敏感信息.md`
- `labs/mcp/foundations/examples/content_security_server.py`
- `labs/mcp/foundations/examples/content_security_host.py`

实践任务：

1. 在订单备注中放入诱导退款的恶意指令。
2. 模拟模型受到诱导后提出 Tool 调用。
3. 用执行计数和订单状态验证 Host 权限不受外部内容影响。
4. 检查审计包含必要证据但不泄露原始幂等键。

检查点：

- 可以解释为什么 Tool 返回内容是数据而不是用户授权。
- 可以同时满足可审计性与敏感信息最小化。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices

### 阶段 12：远程 Server 的授权与攻击面

核心问题：远程 MCP Server 接入真实账户和服务时，用户、Host、Server 与授权服务之间如何建立可信的授权关系？

建议文章：

- `12 | MCP 远程授权：OAuth、Token 与信任边界.md`

学习内容：

- OAuth 与远程 Server authorization flow。
- 用户、Host、Server 与授权服务的信任边界。
- scope minimization、凭据存储、刷新与撤销。
- token passthrough 与 confused deputy 风险。
- SSRF 与 session hijacking 等远程攻击面。
- 授权事件的审计与异常追踪。

实践任务：

1. 画出用户、Host、远程 Server、授权服务和业务系统之间的信任边界。
2. 标注授权码、access token 与业务请求在各角色之间的流向。
3. 为订单查询设计最小 scope，并区分只读查询与退款权限。
4. 分析 token passthrough、confused deputy、SSRF 和 session hijacking 的触发条件与防护位置。
5. 先完成授权流程和威胁分析，再决定是否实现完整 OAuth 实验。

检查点：

- 可以解释远程 MCP 授权中各角色的职责和信任关系。
- 可以说明为什么不能把上游 token 不加约束地透传给 MCP Server。
- 可以为不同能力设计最小 scope、凭据生命周期和撤销策略。
- 可以指出常见远程攻击分别应由 Host、Server 还是授权服务防护。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tutorials/security/authorization
- https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices

### 阶段 13（可选进阶）：Registry、Extensions 与生态

核心问题：哪些能力属于 MCP 核心协议，哪些属于扩展或特定 Client？

这部分不阻塞主线，可以在掌握 Client、本地安全和远程授权基础后按需学习：

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
6. 输入安全阶段：限制 Tool 参数和值域，并最小化返回数据。
7. Host 权限阶段：增加 Tool 白名单和危险操作确认。
8. 执行安全阶段：增加业务规则、幂等和副作用回查。
9. 内容安全阶段：验证 Prompt injection 防护和审计脱敏。
10. 远程授权阶段：梳理 OAuth、最小 scope、token 生命周期和远程攻击面。

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

下一步进入阶段 12：

> 在本地权限和确认边界之上，继续研究远程 Server 的 OAuth、Token 与信任边界。
