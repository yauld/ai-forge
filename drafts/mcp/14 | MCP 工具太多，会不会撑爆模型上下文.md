# 14 | MCP 工具太多，会不会撑爆模型上下文

做 MCP Server 时，很容易遇到一个问题：

> 如果 Server 暴露了 100 个 Tool，用户只是想计算两个数的和，模型是不是也要先看到这 100 个 Tool 的全部说明？

这个问题背后真正担心的，不是“加法工具怎么写”，而是 MCP 的工具发现机制会不会把 Server 的复杂性直接转嫁给模型上下文：token 浪费、延迟上升、上下文被挤占，模型还更容易选错工具。

更具体一点，这里有五层担心：

| 担心 | 问题 |
| --- | --- |
| 上下文成本 | 100 个 Tool 的定义会不会每轮都占 prompt tokens |
| 性能成本 | 工具列表很大，会不会让请求变慢、首 token 延迟增加 |
| 工具选择质量 | 模型面对 100 个工具，会不会更容易选错或幻觉调用 |
| MCP 设计边界 | 这是协议天然问题，还是 Client / Host 的实现问题 |
| 架构可扩展性 | 大量 Tool、Resource、Prompt 会不会让 MCP Server 从根上不可扩展 |

把这些担心压缩成一句话就是：

> MCP 的工具发现机制，会不会把 Server 的复杂性直接转嫁到 LLM 上下文里，导致 Tool 数量一多，整个 Agent 系统就又贵、又慢、又不稳定？

这个担心是合理的。也正是因为它存在，才有必要把这件事拆开讲清楚。

但要说清楚它，必须先分清一件事：

```text
MCP 协议返回了什么
不等于
模型请求里一定放了什么
```

## 一、tools/list 返回给 Client，不是直接返回给模型

MCP Server 暴露 Tool 后，Client 可以发送 `tools/list`。Server 返回工具清单，每个工具通常包含：

```text
name
description
inputSchema
```

这里关键点是：`tools/list` 的接收方是 MCP Client，不是模型本身。

MCP 协议定义的是 Client 和 Server 之间怎么通信。Server 不会直接把工具列表塞进 LLM 上下文。真正决定哪些工具进入模型请求的，是 Host 或 Client。

关系可以简化成：

```text
MCP Server
  暴露 100 个 Tools

MCP Client
  通过 tools/list 拿到 100 个 Tool 定义

Host / Agent Runtime
  决定本轮把哪些 Tool 定义交给模型

LLM
  在它实际看到的工具里选择是否调用 add
```

所以，`tools/list` 本身不是模型上下文膨胀的直接原因。真正的问题是：Client 拿到工具列表之后，Host 怎么处理这些工具定义。

## 二、模型不能凭空选择 add

假设 Server 有 100 个 Tool，其中一个叫 `add`。

用户说：

```text
帮我计算 12 + 30
```

模型要调用 `add`，前提是它在当前请求里知道有这么一个工具，知道它叫什么，知道参数怎么填。

也就是说，模型不能先神奇地决定“我要用 add”，然后系统才把 `add` 的定义加载进来。通常顺序是：

```text
Host 先把一批 Tool 定义交给模型
→ 模型在这批工具里判断是否需要调用 add
→ 模型生成 tool call
→ Client 再向 MCP Server 发送 tools/call
```

如果 Host 本轮只给模型 `add` 一个工具，那模型只会看到 `add`。

如果 Host 本轮给模型 100 个工具，那模型就会在 100 个工具里选择。

所以，真正要问的不是：

```text
MCP Server 有多少工具？
```

而是：

```text
当前这次模型请求暴露了多少工具？
```

这才是上下文成本真正发生的位置。

## 三、现实里通常有三种做法

不同客户端和 Agent 框架，处理方式并不一样。

第一种是全量暴露。把当前启用的 MCP Server 工具都交给模型。实现简单，但如果 Server 有 100 个 Tool，模型请求里就可能包含 100 个工具定义。

第二种是静态过滤。只暴露当前 workspace、当前权限范围、当前模式下允许的工具。模型看到的是一个子集，但仍然不等于只看到 `add`。

第三种是动态工具检索。系统在模型请求之前，先根据用户意图从工具池里找出最相关的一小批工具：

```text
用户：计算 12 + 30

工具检索层：
  add
  subtract
  multiply

模型实际看到：
  只看到这几个候选工具
```

这是比较理想的做法。但它不是 MCP 协议天然保证的能力，而是 Host、Agent Runtime 或应用层额外做的优化。

## 四、Resources 和 Prompts 不在 Tool 里面

还有一个常见误解：

> 一个 Tool 里面是不是还包含大量 Resource、Prompt、Prompt Template？

在 MCP 里，Tool、Resource、Prompt 是并列的 Server primitive，不是嵌套关系。

更准确地说：

```text
tools/list
  返回工具列表

resources/list
  返回资源列表

prompts/list
  返回 Prompt 模板列表
```

Resource 的内容通常要通过 `resources/read` 读取。Prompt 的内容通常要通过 `prompts/get` 获取。所以，`tools/list` 不会自动把所有 Resource 内容、Prompt 内容都塞进每个 Tool。

但如果开发者把大量文档、示例、规则硬写进 Tool 的 `description` 或 `inputSchema`，那这些内容就会变成工具定义的一部分。这不是 MCP 强制要求的结果，而是工具设计不克制带来的结果。

## 五、问题到底出在哪里

真正需要警惕的是这一层：

```text
Host 把大量 Tool 定义暴露给模型
```

而不是这一层：

```text
MCP Server 支持 tools/list
```

MCP Server 暴露 100 个工具，本身只是说明它能力很多。真正让模型上下文变重的是：Host 在模型请求里，把这 100 个工具定义都作为可调用工具传给模型。

所以要分清两类成本：

| 成本 | 发生位置 |
| --- | --- |
| 工具发现成本 | Client 调用 `tools/list`，拿到工具清单 |
| 模型上下文成本 | Host 把工具定义放进 LLM 请求 |

前者是协议通信成本。后者才是 token 和上下文成本。

## 六、设计 MCP Tool 时要保守

既然不能假设所有 Host 都会做智能过滤，MCP Server 设计时就应该保守一点。

几个原则：

```text
Tool 数量要少而清楚
Tool 名称要稳定
description 只写模型选择工具所需的信息
inputSchema 只描述必要参数
大量上下文放到 Resource，按需读取
复杂流程放到 Server 内部编排
```

不要把工具设计成“一个小动作一个 Tool”，最后暴露出几十上百个细碎工具。也不要把大量业务说明、长文档、异常处理策略、权限规则都塞进 `description`。合理的工具粒度应该让模型容易选择，也让系统容易授权。

如果一个系统确实有大量能力，最好在模型前面加一层 Tool Router：

```text
用户请求
→ 工具检索 / 权限过滤
→ 模型看到 3 到 8 个候选工具
→ 模型选择并调用
```

这比让模型直接面对 100 个工具更稳。

## 七、最后记住这句话

MCP 的 `tools/list` 不是问题本身。真正的问题是：

> Host 是否把过多工具定义暴露给模型。

所以，看到一个 MCP Server 有 100 个工具时，不应该立刻得出“每轮模型请求都会塞 100 个工具”的结论。更准确的问题是：这个 Host 会不会全量传给模型？有没有按权限、场景、意图做过滤？工具描述和 Schema 是否足够克制？

> MCP Server 可以有很多工具，但模型每轮应该只看到当前任务真正需要的一小组工具。

协议给了工具发现和调用的标准接口。工程上要补上的，是工具治理、工具检索和上下文预算。
