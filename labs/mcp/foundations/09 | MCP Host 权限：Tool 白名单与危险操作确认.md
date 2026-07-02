# MCP Host 权限：Tool 白名单与危险操作确认

模型可以建议调用 Tool，但模型不是授权主体。

本文通过四个可独立运行的场景回答：

> 模型提出 Tool 调用后，Host 在什么条件下才允许 MCP Client 把请求发给 Server？

完成实验后，你应该能够区分：

- Server 声明的 annotations 与 Host 自己的权限策略；
- 模型生成的 Tool 参数与用户确认状态；
- Host 本地返回的 `blocked_before_call` 与 Server 返回的 Tool 结果；
- “请求没有离开 Host”与“请求到达 Server 后被拒绝”。

本文不研究复杂退款规则和幂等，只观察请求是否离开 Host。

## 1. 实验文件与运行准备

| 文件 | 作用 |
| --- | --- |
| `examples/host_permission_server.py` | 提供订单状态查询和最小退款 Tool |
| `examples/host_permission_host.py` | 模拟模型调用建议，执行 Host 权限检查 |
| `examples/security_order_data.py` | 每次启动时重置独立实验数据库 |

第一次运行仓库实验前执行：

```bash
uv sync
```

后续命令都在仓库根目录执行。你不需要手动启动 Server：

```text
host_permission_host.py
  → connect() 启动 host_permission_server.py
  → 建立 stdio 与 ClientSession
  → 执行 initialize
  → 运行指定场景
  → 自动关闭 Session 和 Server
```

每次单独运行场景都会重置数据库，因此订单从固定状态开始。

## 2. 先理解权限数据流

```text
人提出需求
  ↓
模型建议 Tool 名称和参数
  ↓
Host 检查 Tool 白名单
  ↓
Host 检查模型是否加入未知参数
  ↓
Host 检查用户是否确认危险操作
  ↓ 三项全部通过
MCP Client 执行 session.call_tool()
  ↓
MCP Server 执行 Tool
```

Host 使用两份本地配置：

```python
HOST_TOOL_POLICY = {
    "get_order_for_support": "allow",
    "refund_order": "require_confirmation",
}

HOST_TOOL_ARGUMENTS = {
    "get_order_for_support": {"order_id"},
    "refund_order": {"order_id", "reason"},
}
```

`host_decides_whether_to_call()` 只有在三项检查全部通过后，才执行：

```python
await session.call_tool(tool_name, model_proposed_arguments)
```

因此下面的结果由 Host 本地构造，不是 MCP Server 返回：

```text
host_status: blocked_before_call
```

## 3. 场景一：发现 Tool 和风险提示

运行：

```bash
uv run labs/mcp/foundations/examples/host_permission_host.py discovery
```

对应函数：

```text
discovery → discovery()
```

函数会：

1. 调用 `session.list_tools()`；
2. 列出 Server 暴露的 Tool；
3. 找到 `refund_order`；
4. 分别检查 `readOnlyHint` 和 `destructiveHint`。

预期核心输出：

```text
discovered_tools:
  get_order_for_support
  refund_order

refund_order 不是只读 Tool  passed=True
refund_order 有破坏性       passed=True
```

这直接证明 Server 声明了风险信息，但不证明 Host 应自动授权。annotations 是
Server 提供的提示，Host 仍然使用自己的 `HOST_TOOL_POLICY`。

## 4. 场景二：拒绝 Host 未审核的 Tool

运行：

```bash
uv run labs/mcp/foundations/examples/host_permission_host.py unknown-tool
```

对应函数：

```text
unknown-tool → unknown_tool()
```

实验模拟模型提出：

```text
export_all_orders
```

它不在 `HOST_TOOL_POLICY` 中，Host 返回：

```text
host_status: blocked_before_call
reason: tool_not_allowed_by_host_policy
```

代码在这个分支直接 `return`，不会运行 `session.call_tool()`。所以结果不是
Server 的“Tool 不存在”错误，而是 Host 在请求发送前做出的拒绝决定。

## 5. 场景三：合法退款参数也不能代替确认

运行：

```bash
uv run labs/mcp/foundations/examples/host_permission_host.py refund-unconfirmed
```

对应函数：

```text
refund-unconfirmed → unconfirmed_refund()
```

实验用字典模拟模型生成的 Tool 参数：

```python
model_proposed_arguments = {
    "order_id": "O-1001",
    "reason": "duplicate",
}
```

参数本身完全合法，但 Host 界面状态是：

```python
user_confirmed=False
```

预期输出：

```text
未确认退款在 tools/call 前被阻止  passed=True
reason: explicit_user_confirmation_required
订单没有被退款                 passed=True  evidence=paid
```

回查订单仍为 `paid`，证明退款 Tool 没有产生副作用。这里验证的是 Host 确认
边界，不是 Server 业务规则。

## 6. 场景四：模型不能伪造确认字段

运行：

```bash
uv run labs/mcp/foundations/examples/host_permission_host.py refund-forged-confirmation
```

对应函数：

```text
refund-forged-confirmation → forged_confirmation()
```

模型尝试把下面字段塞进 Tool 参数：

```python
"user_confirmed": True
```

但 `refund_order` 的允许参数只有 `order_id` 和 `reason`。即使实验把 Host
内部的真实 `user_confirmed` 设为 `True`，未知字段仍然必须被拒绝：

```text
reason: unexpected_tool_arguments
unexpected_arguments: ["user_confirmed"]
订单没有被退款: passed=True
```

这个对照证明两个结论：

- 真实确认状态属于 Host 控制流；
- 用户确认不能顺便放宽 Tool 参数契约。

## 7. 完整回归与常见问题

理解单个场景后运行：

```bash
uv run labs/mcp/foundations/examples/host_permission_host.py all
```

执行顺序：

```text
discovery
  → unknown-tool
  → refund-unconfirmed
  → refund-forged-confirmation
```

| 现象 | 优先检查 |
| --- | --- |
| 找不到 `refund_order` | Server 文件和 `SCENARIOS` 是否对应 |
| 订单意外变成 `refunded` | 是否绕过 `host_decides_whether_to_call()` 直接调用 |
| 未知参数没有被拒绝 | `HOST_TOOL_ARGUMENTS` 是否包含了不该出现的字段 |
| 输出 `passed=False` | 查看同一行 `evidence` 中的 Host 决定和订单状态 |

`all` 用于最终回归。第一次学习应按本文顺序逐个运行场景。

## 8. 实验验收

完成后尝试回答：

1. annotations 为什么不能自动授予 Tool 权限？
2. `blocked_before_call` 是谁生成的？
3. 哪一行代码真正把请求发送给 MCP Server？
4. 为什么模型生成 `user_confirmed=True` 不能代表用户确认？
5. 回查订单仍为 `paid` 提供了什么证据？

最终应形成：

```text
模型只能提出调用
  → Host 检查 Tool、参数和用户确认
  → 只有 Host 放行后，MCP Client 才发送请求
```
