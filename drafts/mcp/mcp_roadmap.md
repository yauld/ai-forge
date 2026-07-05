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

### 阶段 6：构建一个基础 MCP Client（已完成）

核心问题：Host 如何发现 Server 能力，并把调用路由到正确的连接？

对应材料：

- `labs/mcp/foundations/06 | MCP Client：Host 如何发现并调用 Server 能力.md`
- `drafts/mcp/06 | 接了多个 MCP Server，Tool 调用到底该发给谁？.md`
- `labs/mcp/foundations/examples/multi_server_client.py`

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
- `drafts/mcp/10 | MCP 执行安全：请求到了 Server，也不等于应该执行.md`
- `drafts/mcp/assets/10-mcp-server-execution-boundaries.svg`
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

### 交叉案例：间接 Prompt Injection（已迁移）

间接 Prompt Injection 的核心问题是 AI 安全威胁建模：外部业务数据如何进入模型上下文，并诱导模型提出危险 Tool 调用。它使用 MCP 作为实验载体，但主线不属于 MCP 协议学习，已迁移到 Sec for AI 专题。

对应材料：

- `labs/sec-for-ai/foundations/01 | 间接 Prompt Injection：业务数据如何变成指令.md`
- `drafts/sec-for-ai/01 | 间接 Prompt Injection：业务数据也可能变成指令.md`

MCP 专题继续保留 Host 权限、Server 执行安全、审计和远程授权等协议与工程边界内容。

### 阶段 11：审计与敏感信息安全（已完成）

核心问题：操作日志如何保留调查证据，同时避免泄露原始凭据和完整请求？

对应材料：

- `labs/mcp/foundations/11 | MCP 审计安全：既要留下证据，也不能泄露秘密.md`
- `drafts/mcp/11 | MCP 审计安全：日志不是记得越多越好.md`
- `labs/mcp/foundations/examples/audit_security_server.py`
- `labs/mcp/foundations/examples/audit_security_client.py`

实践任务：

1. 分别执行一笔成功退款和一笔被拒绝的退款。
2. 检查审计同时保留 `applied` 与 `denied`。
3. 验证原始幂等键没有进入日志，但短指纹仍可用于关联。
4. 回查订单最终状态，使审计证据与业务结果互相验证。

检查点：

- 可以为成功与失败操作选择最小审计字段。
- 可以解释短指纹的关联价值与隐私边界。
- 可以避免把完整 Tool 请求直接写入审计。

### 阶段 12：远程 MCP Server 的连接与调用（已完成）

核心问题：MCP Server 独立运行后，Host 如何通过 URL 建立连接并调用它的能力？

对应材料：

- `labs/mcp/foundations/12 | MCP 远程访问基础：通过 Streamable HTTP 连接与调用 Server.md`
- `drafts/mcp/12 | 通过 Streamable HTTP 连接远程 MCP Server.md`
- `labs/mcp/foundations/examples/remote_connection_server.py`
- `labs/mcp/foundations/examples/remote_connection_client.py`

学习内容：

- 本地 stdio Server 与远程 HTTP Server 的运行方式差异。
- Server 独立启动、监听地址、端口、MCP endpoint 与完整连接 URL。
- Host、MCP Client、远程 Server 和业务系统之间的连接关系。
- `streamable_http_client` 如何把 HTTP 通道包装成 `ClientSession` 使用的消息流。
- `initialize`、`tools/list` 和 `tools/call` 如何通过 Streamable HTTP 完成。
- Server 未启动、URL 或 endpoint 错误时的基本失败现象。

实践任务：

1. 独立启动一个不带授权的订单查询 MCP Server，并确认 `/mcp` endpoint。
2. 在另一个进程中使用 Client 按 URL 连接 Server。
3. 依次执行 `initialize`、`tools/list` 和 `tools/call`。
4. 对照 stdio 实验，观察谁负责启动 Server、Client 连接的目标是什么。
5. 分别尝试未启动 Server、错误端口和错误 endpoint，并记录失败位置。

检查点：

- 可以解释“远程”描述的是独立运行并通过网络 URL 访问，而不等于一定部署在公网。
- 可以说明 stdio 与 Streamable HTTP 模式下分别由谁启动 Server。
- 可以从 Server 地址、端口和 endpoint 组成正确的 MCP URL。
- 可以使用基础 Client 完成一次远程 Tool 调用。
- 可以区分连接失败、HTTP endpoint 错误和 MCP Tool 执行失败。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://github.com/modelcontextprotocol/python-sdk#streamable-http-transport

### 阶段 13：远程 Server 如何完成授权（已完成）

核心问题：Bearer Token 如何决定 MCP Client 能否调用远程 Server？

对应材料：

- `labs/mcp/foundations/13 | MCP 远程授权：从 401 到第一次受保护调用.md`
- `drafts/mcp/13 | MCP 远程授权：Token 从哪里来，又在哪里被验证.md`
- `labs/mcp/foundations/examples/remote_auth_server.py`
- `labs/mcp/foundations/examples/remote_auth_resource_server.py`
- `labs/mcp/foundations/examples/remote_auth_client.py`

学习内容：

- 远程 MCP Server 如何验证 Bearer Token。
- 无 Token 请求为什么在 MCP 初始化前得到 `401 Unauthorized`。
- Client 如何通过登录、同意和授权码交换取得 access token。
- Resource Server 如何通过 introspection 检查 issuer、audience、有效期和 scope。

实践任务：

1. 启动一个演示 Authorization Server 和一个受保护的远程 MCP Server。
2. 不带 Token 请求 `/mcp`，观察 `401`。
3. 用演示账号登录并同意授权，取得一次性授权码和短期 access token。
4. 携带正确 Token 完成初始化并调用订单查询 Tool。
5. 换成错误 Token，确认请求仍然被拒绝。

检查点：

- 可以解释认证为什么发生在 MCP 初始化和 Tool 执行之前。
- 可以用无 Token 和授权服务签发的正确 Token 证明授权门槛生效。
- 可以说明本实验保留了授权码与 introspection 主线，但不是完整生产 OAuth。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tutorials/security/authorization

### 阶段 14：权限与 Token 边界

核心问题：Client 拿到 access token 后，远程 MCP Server 应如何限制它能调用的能力？

建议文章：

- `14 | MCP 权限与 Token 边界：Scope、Audience 与安全调用.md`

学习内容：

- 订单查询、明细读取与退款能力的最小 scope。
- access token 的有效期、issuer、audience 与 scope 校验。
- scope 不足时的拒绝与增量授权。
- token passthrough 为什么会破坏 MCP Server 与下游业务系统的信任边界。
- OAuth 权限、Host 确认与 Server 业务授权之间的区别。

实践任务：

1. 使用正确 token 调用订单查询 Tool。
2. 使用缺少退款 scope 的 token 调用退款 Tool，并验证请求被拒绝。
3. 使用 audience 不属于当前 MCP Server 的 token 发起调用，并验证请求被拒绝。
4. 获得退款 scope 后再次调用，并验证请求仍需通过 Host 确认和 Server 业务规则。

检查点：

- 可以为只读查询与危险操作设计不同 scope。
- 可以解释 Server 为什么必须校验 token 的有效期、audience 和 scope。
- 可以说明为什么 MCP Server 不能把收到的 token 原样透传给下游 API。
- 可以区分 OAuth 授权、Host 权限与业务执行边界。

推荐官方页面：

- https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
- https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices

### 阶段 15：远程 Server 的常见攻击面

核心问题：Token 校验正确以后，远程 MCP 连接还面临哪些 HTTP、授权发现与 Session 风险？

建议文章：

- `15 | MCP 远程攻击面：Confused Deputy、SSRF 与 Session Hijacking.md`

学习内容：

- confused deputy 的触发条件与授权边界。
- OAuth 元数据发现过程中的 SSRF。
- 重定向、私网地址与网络出口限制。
- MCP Session ID 泄露、冒用与用户绑定。
- 授权事件的审计与异常追踪。

实践任务：

1. 分析 confused deputy 的触发条件和用户授权被绕过的位置。
2. 构造指向 localhost 或私网地址的 OAuth 元数据 URL，观察 Client 的拒绝位置。
3. 尝试使用另一用户的 Session ID 发起请求，并验证 Server 仍会校验 token。
4. 标注每类攻击主要应由 Client、Server、授权服务还是网络层防护。

检查点：

- 可以识别 confused deputy、SSRF 和 session hijacking 的基本触发条件。
- 可以说明 Session ID 为什么不能代替身份凭据。
- 可以指出常见远程攻击的主要防护位置。

推荐官方页面：

- https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices

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
9. 审计安全阶段：验证成功与拒绝事件的最小化审计和敏感字段脱敏。
10. 远程访问阶段：独立启动 HTTP Server，并通过 URL 完成初始化、能力发现和 Tool 调用。
11. 远程授权阶段：对比无 Token 的 `401` 与携带正确 Token 后的受保护 Tool 调用。
12. 权限与 Token 阶段：验证最小 scope、token audience 和下游凭据边界。
13. 远程攻击面阶段：验证 confused deputy、SSRF 和 session hijacking 的触发条件与防护位置。

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

下一步进入阶段 14：

> 在看清 Bearer Token 授权效果的基础上，继续验证最小 scope、token audience 和下游凭据边界。
