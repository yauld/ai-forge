# MCP 审计安全：既要留下证据，也不能泄露秘密

退款成功后，订单状态发生了变化；退款被拒绝时，也可能意味着有人正在尝试操作
不存在或不允许处理的订单。两种结果都值得留下证据。

但“留下证据”不等于把完整 Tool 请求原样写进日志。请求中的幂等键、Token、
用户输入和业务字段一旦进入审计系统，通常会被保存更久、被更多人读取，审计日志
反而可能成为新的泄露面。

本文用一个可运行的退款实验回答：

> MCP Server 如何同时记录成功与拒绝操作，并只保留调查所需的数据？

完成实验后，你应该能解释：

- 为什么成功和拒绝都要审计；
- 为什么审计记录不能直接保存完整 Tool 请求；
- 完整摘要和短指纹分别承担什么职责；
- 为什么审计结果还要与最终业务状态相互验证；
- 当前实验能证明什么，又没有证明什么。

本实验研究请求到达 Server 之后的业务审计，不再展开 Host 确认、远程身份认证和
传输安全。

## 1. 实验文件、前提与目标

实验使用三个文件：

| 文件 | 作用 |
| --- | --- |
| `examples/audit_security_server.py` | 提供退款、审计查询和订单状态查询 Tool |
| `examples/audit_security_client.py` | 发起成功与拒绝请求，并执行全部断言 |
| `examples/security_order_data.py` | 重建安全实验专用的 SQLite 订单数据 |

仓库要求 Python 3.13 或更高版本，MCP Python SDK 依赖由 `pyproject.toml` 管理。
第一次运行仓库实验时，在仓库根目录执行：

```bash
uv sync
```

后续命令也都从仓库根目录执行。Client 会通过 stdio 自动启动 Server，不需要再
打开一个终端。

Server 每次启动都会重建：

```text
labs/mcp/foundations/examples/data/shop_order_security.sqlite
```

因此每次完整运行都从相同订单状态开始。注意，这也意味着再次启动任意使用
`security_order_data.py` 的安全实验 Server，可能覆盖你上一次观察到的数据。

本次实验使用两个输入：

| 场景 | 订单 | 初始状态 | 幂等键 | 预期业务结果 |
| --- | --- | --- | --- | --- |
| 合法基线 | O-1005 | `paid`，金额 129 元 | `refund-audit0001` | 退款成功 |
| 拒绝场景 | O-9999 | 订单不存在 | `refund-audit0002` | 拒绝退款 |

实验需要形成三段证据：

1. Tool 返回值证明成功请求被执行、非法对象被拒绝；
2. 审计查询证明 `applied` 和 `denied` 都被记录，同时没有暴露原始幂等键；
3. 订单状态回查证明成功审计对应真实的业务状态变化。

## 2. 先看完整数据流

实验中的 Host 代码就是 `audit_security_client.py`。它在进程内创建 MCP Client，
再由 Client 通过 stdio 与 Server 通信。SQLite 是 Server 访问的外部业务系统，
Client 不直接修改数据库。

```text
Host：audit_security_client.py
  ↓ 创建并初始化
MCP Client：ClientSession
  ↓ stdio / tools/call
MCP Server：audit_security_server.py
  ↓ refund_order()
SQLite：读取订单、写入退款结果和审计事件
  ↑
MCP Server：返回结构化结果
  ↑
MCP Client → Host：执行断言并打印证据
```

`refund_order()` 内部还有两条业务路径：

```text
收到退款请求
  ↓
原始幂等键 → SHA-256 完整摘要 → 前 12 位短指纹
  ↓
完整摘要是否已存在？
  ├─ 是 → 返回 already_applied，不重复执行
  └─ 否
       ↓
     订单是否存在且状态为 paid？
       ├─ 否 → 写入 denied 审计 → 返回 denied
       └─ 是 → 更新订单状态
                → 写入完整幂等摘要
                → 写入 applied 审计
                → 提交事务后返回 refunded
```

Server 给 `refund_order` 标记了 `destructiveHint=True` 和
`idempotentHint=True`，给查询 Tool 标记了 `readOnlyHint=True`。这些
Tool annotations 只是向 Client 描述行为的提示，不是强制执行的安全策略。
MCP 官方 Schema 也明确说明，Client 不应基于不可信 Server 提供的 annotations
做安全决策。真正保证本实验行为的是 Server 中的业务分支、数据库约束和事务，
不是这些布尔字段。

官方参考：
[MCP ToolAnnotations Schema](https://modelcontextprotocol.io/specification/2025-11-25/schema#toolannotations)

## 3. Server 如何设计最小化审计

### 3.1 三张表各自记录什么

Server 启动时创建或重建三张与本实验有关的表：

| 表 | 关键内容 | 用途 |
| --- | --- | --- |
| `orders` | 订单状态、金额等业务数据 | 判断并保存真实退款结果 |
| `refund_operations` | 完整幂等键摘要、订单编号 | 精确识别重复退款 |
| `audit_events` | 时间、动作、订单、结果、脱敏详情 | 支持事后调查 |

审计表没有保存完整请求：

```sql
CREATE TABLE audit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    action TEXT NOT NULL,
    order_id TEXT NOT NULL,
    outcome TEXT NOT NULL,
    detail TEXT NOT NULL
);
```

稳定字段单独成列，便于按时间、订单和结果查询；不同结果需要的补充信息放入
`detail` JSON。例如，成功记录包含金额和退款原因，拒绝记录只包含统一拒绝原因。

这是一种面向实验的简单设计。真实系统如果需要频繁按 `detail` 中的字段检索，
可以把重要字段拆成独立列，而不是长期依赖 JSON 文本扫描。

### 3.2 为什么不保存原始幂等键

Server 对原始幂等键做两种处理：

```python
digest = hashlib.sha256(idempotency_key.encode()).hexdigest()
fingerprint = digest[:12]
```

- `digest` 是完整 SHA-256 摘要，保存到 `refund_operations`，用于精确判重；
- `fingerprint` 是摘要前 12 位，写入响应和审计，供人工关联同一次业务意图；
- 原始 `idempotency_key` 不进入这两张表。

短指纹不能承担唯一约束或认证职责，因为截断后存在碰撞可能。它只是一种降低
暴露面的关联标识。

摘要也不是加密，更不是绝对匿名化。如果原始值空间很小或格式容易预测，攻击者
仍可能枚举候选值并比对摘要。因此，真实系统仍应限制摘要和短指纹的访问范围与
保留时间。

### 3.3 为什么审计写入要复用业务连接

`record_audit()` 不自行创建数据库连接，而是接收 `refund_order()` 当前使用的
`conn`：

```python
def record_audit(
    conn: sqlite3.Connection,
    *,
    order_id: str,
    outcome: str,
    detail: dict[str, object],
) -> None:
    conn.execute(...)
```

退款成功路径依次执行：

```text
UPDATE orders
INSERT refund_operations
INSERT audit_events
```

三步位于同一个 `with sqlite3.connect(...)` 事务边界内。正常离开上下文时一起
提交；中途抛出异常时一起回滚。这样可以避免订单已经退款但没有成功审计，或者
审计声称成功但业务状态没有改变。

拒绝路径虽然在 `with` 内直接 `return`，仍属于正常离开连接上下文，所以拒绝
审计会被提交。成功响应则放在 `with` 之后返回，确保提交完成后才向 Client 报告
`refunded`。

这项事务设计直接来自本地代码；实验没有主动注入数据库写入故障，因此本次运行
只验证正常成功与正常拒绝，没有动态证明异常回滚路径。

## 4. 场景一：合法退款必须留下成功证据

Client 首先调用：

```python
applied = await session.call_tool(
    "refund_order",
    {
        "order_id": "O-1005",
        "reason": "duplicate",
        "idempotency_key": "refund-audit0001",
    },
)
```

O-1005 初始状态是 `paid`，所以 Server 应当：

1. 把订单状态更新为 `refunded`；
2. 保存完整幂等摘要；
3. 写入一条 `outcome=applied` 的审计记录；
4. 返回短指纹，不返回原始幂等键。

关键响应形态是：

```text
status: refunded
order_id: O-1005
idempotency_fingerprint: 55740cd0fe30
```

这条响应只能证明 Server 声称退款成功。它还不能单独证明数据库状态真的改变，
也不能证明审计记录已经存在，所以 Client 后面还会分别读取审计和回查订单状态。

成功审计保留：

```json
{
  "action": "refund",
  "order_id": "O-1005",
  "outcome": "applied",
  "detail": {
    "amount": 129.0,
    "idempotency_fingerprint": "55740cd0fe30",
    "reason": "duplicate"
  }
}
```

时间字段每次运行都会变化，这里省略。金额和业务原因有助于解释“哪一笔操作为何
成功”，短指纹用于关联调用；产品、地区等与本次调查无关的订单字段没有进入审计。

## 5. 场景二：拒绝请求同样需要审计

接着，Client 请求不存在的 O-9999：

```python
denied = await session.call_tool(
    "refund_order",
    {
        "order_id": "O-9999",
        "reason": "customer_request",
        "idempotency_key": "refund-audit0002",
    },
)
```

`O-9999` 符合 `O-\d{4}` 的输入格式，所以请求能够通过参数 Schema；但它在
数据库中不存在，因此由 Server 的业务规则拒绝。这是业务拒绝，不是 JSON-RPC、
transport 或参数校验错误。

Server 对“订单不存在”和“订单不是 paid 状态”统一返回：

```text
status: denied
reason: order_not_refundable
```

统一原因避免调用方通过错误差异继续探测订单是否存在或处于什么状态。与此同时，
Server 写入：

```json
{
  "action": "refund",
  "order_id": "O-9999",
  "outcome": "denied",
  "detail": {
    "idempotency_fingerprint": "efa29aa6ecdc",
    "reason": "order_not_refundable"
  }
}
```

拒绝记录没有保存退款金额，因为不存在可退款订单；也没有保存调用方提交的原始
幂等键。它仍保留请求针对的订单编号、统一拒绝原因和短指纹，使调查者能知道发生
过一次失败尝试。

本实验没有为 O-9999 回查状态，因为不存在的订单本来就没有可变化的状态。Client
用成功场景的状态回查验证真实副作用，用拒绝审计验证失败尝试已留下证据，两项
检查承担不同职责。

## 6. 运行完整实验并解释输出

在仓库根目录运行：

```bash
uv run labs/mcp/foundations/examples/audit_security_client.py
```

Client 按以下顺序执行：

```text
启动并初始化 Server
  → 调用 O-1005 合法退款
  → 调用 O-9999 拒绝退款
  → 检查两个业务返回
  → 读取全部审计记录
  → 检查成功和拒绝结果
  → 检查原始幂等键没有出现
  → 检查两条记录都有短指纹
  → 回查 O-1005 最终状态
```

一次真实运行得到的关键结果如下。MCP SDK 的 INFO 日志和重复的完整审计对象在此
省略，只保留判断证据：

```text
合法退款成功，非法对象被拒绝              passed=True
审计同时保留 applied 与 denied           passed=True
审计没有保存原始幂等键                    passed=True
审计保留可关联的幂等键短指纹              passed=True
成功审计对应的订单最终为 refunded         passed=True
```

审计数据中的关键值是：

```text
O-1005  outcome=applied  fingerprint=55740cd0fe30
O-9999  outcome=denied   fingerprint=efa29aa6ecdc
```

最后一次状态查询返回：

```text
found: True
order_id: O-1005
status: refunded
```

这些观察分别支持：

| 直接观察 | 能支持的结论 |
| --- | --- |
| 两个 Tool 返回 `refunded` 和 `denied` | 两条业务路径都被执行 |
| 审计中同时出现 `applied` 与 `denied` | 成功和拒绝事件都留下记录 |
| 审计序列化结果不含两个原始幂等键 | 通过 Tool 返回的审计没有暴露原始键 |
| 审计中出现两个短指纹字段 | 两次尝试都保留了可关联标识 |
| O-1005 最终为 `refunded` | 成功日志对应真实业务状态变化 |

“通过 Tool 返回的审计不含原始键”不等于证明整个进程、所有日志和所有基础设施都
绝不会泄露它。本实验只检查当前 Server 生成并返回的审计数据。

### 可选：直接查看 SQLite

Client 退出后，数据库文件仍然存在。可以用 SQLite 客户端执行：

```sql
SELECT
    event_id,
    created_at,
    action,
    order_id,
    outcome,
    detail
FROM audit_events
ORDER BY event_id;
```

再检查业务状态：

```sql
SELECT order_id, status
FROM orders
WHERE order_id = 'O-1005';
```

也可以确认幂等表保存的是摘要而非原始值：

```sql
SELECT idempotency_digest, order_id
FROM refund_operations;
```

如果表不存在或没有数据，先确认已经运行 Client，且之后没有启动另一个会重置
`shop_order_security.sqlite` 的安全实验 Server。

## 7. 证据边界与工程化改进

本实验直接验证了：

- 成功退款和拒绝尝试都会写入审计；
- 审计只选择当前调查需要的字段；
- 审计结果不包含两个原始幂等键；
- 短指纹可以把响应和审计记录关联起来；
- 成功审计与订单最终状态一致。

从代码可以进一步判断，业务更新、幂等记录和成功审计共享 SQLite 事务；但本实验
没有通过故障注入动态验证回滚。

它没有覆盖：

- 谁可以调用 `list_security_audit`，以及不同角色能看到哪些记录；
- 远程 Server 的身份认证、Token 管理和传输加密；
- 审计记录的防篡改、签名、备份和独立存储；
- 操作者身份、会话 ID、请求 ID、来源和策略版本；
- 日志保留期限、删除规则和敏感字段分级；
- 数据库并发写入与跨服务事务；
- 对高频拒绝、异常金额或重复攻击的告警。

尤其要注意，示例把 `list_security_audit` 暴露成普通只读 Tool，只是为了让实验
Client 能观察结果。生产系统通常应把审计查询放在受严格授权的管理边界内，而
不是让所有能连接 Server 的调用方都读取。

工程化时可以沿着四条线继续完善：

1. **身份与关联**：记录经过认证的操作者、租户、请求 ID 和策略版本；
2. **访问与最小化**：按角色限制审计读取，并为字段设置保留期限；
3. **完整性**：把审计发送到独立、追加写入或可验证完整性的存储；
4. **监控**：针对集中拒绝、异常频率和敏感对象建立告警。

## 8. 常见问题与实验验收

| 现象 | 优先检查 |
| --- | --- |
| 找不到数据库文件 | 是否先运行 `audit_security_client.py` |
| `audit_events` 为空 | Server 是否执行 `prepare_database()`，请求是否到达 Tool |
| 只有 `applied` 没有 `denied` | 拒绝分支是否调用 `record_audit()` |
| 审计出现 `refund-audit0001` | 是否把完整请求或原始幂等键写入 `detail` |
| 短指纹数量不是 2 | 成功与拒绝分支是否都写入 `idempotency_fingerprint` |
| O-1005 仍为 `paid` | 业务更新是否成功提交，是否随后重启 Server 重置了数据 |
| VS Code 中数据没有变化 | 刷新数据库视图，确认打开的是 `shop_order_security.sqlite` |

完成实验后，尝试不看代码回答：

1. 为什么 `applied` 和 `denied` 都有调查价值？
2. 为什么不能把完整 Tool 请求直接保存为审计记录？
3. 完整 SHA-256 摘要和前 12 位短指纹分别保存在哪里、解决什么问题？
4. 为什么短指纹不能作为唯一约束或认证凭据？
5. 为什么看到 `outcome=applied` 后还要回查订单状态？
6. Tool annotations 为什么不能代替 Server 的业务检查和审计实现？
7. 当前实验对事务一致性提供了什么证据，又缺少什么故障证据？

可以把本实验的结论收束为：

```text
审计不是保存得越多越好
  → 成功与拒绝都要记录
  → 只保留调查所需字段
  → 敏感值用受控摘要和短指纹关联
  → 审计写入与业务副作用保持一致
  → 再用最终业务状态验证日志含义
```
