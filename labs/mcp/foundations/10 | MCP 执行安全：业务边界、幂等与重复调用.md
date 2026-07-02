# MCP 执行安全：业务边界、幂等与重复调用

Host 允许调用，不代表 Server 必须执行。

本文通过五个独立场景回答：

> 退款请求到达 MCP Server 后，Server 如何根据业务规则决定执行或拒绝？

完成后，你应该能解释对象、状态、金额和幂等分别保护什么，并用最终订单状态
或退款操作记录证明副作用是否发生。

本实验假设 Host 已完成用户确认，不再研究 Tool 白名单和确认界面。

## 1. 实验文件与运行准备

| 文件 | 作用 |
| --- | --- |
| `examples/execution_security_server.py` | 实现退款业务规则和幂等记录 |
| `examples/execution_security_client.py` | 主动提交不同退款请求并检查最终状态 |
| `examples/security_order_data.py` | 每次启动时重置独立实验数据库 |

首次运行仓库实验前执行：

```bash
uv sync
```

后续命令在仓库根目录执行。Client 会通过 `connect()` 自动启动 Server，无需
打开第二个终端。

单独运行任意场景时，Server 都会重建订单和 `refund_operations` 表，因此场景
不依赖上一次运行残留的数据。

## 2. 先理解 Server 执行路径

```text
Host 已允许 tools/call
  ↓
MCP Client 把请求发送给 Server
  ↓
refund_order 检查幂等键
  ↓
检查订单是否存在
  ↓
检查订单状态是否为 paid
  ↓
检查金额是否在 2000 元自助范围
  ↓
更新订单并写入一条退款操作记录
```

这四道边界解决的问题不同：

| 边界 | 防止什么 |
| --- | --- |
| 对象存在 | 对不存在的订单执行操作 |
| 状态检查 | 对 cancelled、refunded 等状态重复操作 |
| 金额限制 | 高风险金额绕过人工审核 |
| 幂等约束 | 网络重试重复产生副作用，或幂等键换绑对象 |

实验 Client 使用两个辅助 Tool：

- `get_order_status()`：回查最终订单状态；
- `get_refund_operation_count()`：检查数据库实际写入几条退款记录。

## 3. 场景一和二：对象与状态边界

先运行不存在订单：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py refund-missing-order
```

对应：

```text
refund-missing-order → missing_order()
```

O-9999 格式合法，但数据库中不存在。预期：

```text
不存在订单被拒绝  passed=True
reason: order_not_found
```

这是一项业务拒绝，不是协议错误或 schema 错误。

再运行状态边界：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py refund-invalid-state
```

对应：

```text
refund-invalid-state → invalid_state()
```

O-1003 当前为 `cancelled`，预期：

```text
取消订单被拒绝          passed=True
reason: order_not_paid
拒绝后仍为 cancelled    passed=True
```

第二条检查回查数据库状态，证明拒绝后没有发生退款。

## 4. 场景三：金额边界

运行：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py refund-amount-limit
```

对应：

```text
refund-amount-limit → amount_limit()
```

O-1011 金额为 2699 元，高于 2000 元自助退款上限。预期：

```text
超额退款转人工审核  passed=True
reason: manual_review_required
policy_limit: 2000.0
拒绝后仍为 paid    passed=True
```

这里的 `paid` 是最终业务状态证据。仅看到 `manual_review_required` 文案，
不足以证明数据库没有先被修改。

## 5. 场景四：相同业务意图的网络重试

运行：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py refund-idempotency
```

对应：

```text
refund-idempotency → idempotent_retry()
```

Client 使用相同订单和幂等键调用两次：

```text
O-1001
refund-demo0001
```

预期：

```text
首次退款成功                 passed=True  status=refunded
重试没有重复退款             passed=True  status=already_applied
最终状态为 refunded          passed=True
数据库只记录一次退款操作      passed=True  evidence=1
```

最后一项来自 `get_refund_operation_count()`，直接证明数据库只有一条退款操作
记录，而不只是相信 `already_applied` 返回文案。

Server 不保存原始幂等键，而是保存完整 SHA-256 摘要；结果中只展示前 12 位
指纹。

## 6. 场景五：幂等键不能换绑订单

运行：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py refund-key-conflict
```

对应：

```text
refund-key-conflict → idempotency_conflict()
```

实验先把 `refund-conflict1` 绑定到 O-1004，再尝试用于 O-1002：

```text
幂等键已绑定 O-1004       passed=True
幂等键不能换绑 O-1002     passed=True
reason: idempotency_key_conflict
冲突后 O-1002 仍为 paid   passed=True
```

这说明幂等键不仅表示“请求执行过”，还必须绑定原始业务对象。

## 7. 完整回归与常见问题

理解单个场景后运行：

```bash
uv run labs/mcp/foundations/examples/execution_security_client.py all
```

执行顺序：

```text
missing-order
  → invalid-state
  → amount-limit
  → idempotency
  → key-conflict
```

| 现象 | 优先检查 |
| --- | --- |
| 单独场景结果受上次运行影响 | Server 是否调用 `prepare_database()` |
| 重试返回 `order_not_paid` | 是否先检查业务状态、后检查幂等记录 |
| 幂等场景记录数大于 1 | `idempotency_digest` 是否有唯一约束 |
| 拒绝后订单状态变化 | UPDATE 是否发生在全部规则通过之前 |

## 8. 实验验收

完成后尝试回答：

1. Host 确认和 Server 业务授权有什么区别？
2. O-9999 为什么不是 schema 错误？
3. 为什么拒绝后必须回查订单状态？
4. `already_applied` 为什么还需要操作记录数佐证？
5. 幂等键为什么必须绑定具体订单？

最终应形成：

```text
Host 决定是否发送
  → Server 根据可信业务状态决定是否执行
  → 幂等记录约束重复副作用
  → 最终状态和记录数提供直接证据
```
