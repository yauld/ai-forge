# MCP 输入安全：参数限制、Schema 与数据最小化

MCP Tool 的参数来自外部调用者。即使 Tool 只查询数据，也不能接受任意状态、
无限返回数量或调用者拼接的 SQL。

本文通过四个可以独立运行的场景回答：

> MCP Server 如何限制调用者能传入什么，以及能够读走多少数据？

实验完成后，你应该能观察并解释：

- 合法边界值为什么能够进入 Tool；
- 非法枚举和极端数值在哪里被拒绝；
- 如何证明非法参数没有进入查询函数；
- SQL 参数绑定和枚举校验分别解决什么问题；
- 如何检查 Tool 没有返回多余字段。

本文不讨论危险操作确认、退款业务规则、幂等和 Prompt injection。

## 1. 实验文件与运行准备

本实验使用三个文件：

| 文件 | 作用 |
| --- | --- |
| `examples/input_security_server.py` | 注册受限订单查询 Tool 和两个观察辅助 Tool |
| `examples/input_security_client.py` | 启动 Server、发送调用并检查结果 |
| `examples/security_order_data.py` | 重置独立实验数据库，不修改前序实验数据 |

仓库使用 Python 3.13 和 uv。在第一次运行仓库实验前，先完成依赖安装：

```bash
uv sync
```

后续命令都在仓库根目录执行。

你不需要单独启动 `input_security_server.py`。Client 的 `connect()` 会：

```text
使用当前 Python 启动 input_security_server.py
  → 建立 stdin/stdout 消息通道
  → 创建 ClientSession
  → 执行 initialize
  → 运行指定场景
  → 场景结束后关闭 Session 和 Server 子进程
```

Server 每次启动都会重建 `shop_order_security.sqlite`，所以各次运行从相同数据
开始，也不会修改前序实验使用的 `shop_orders.sqlite`。

## 2. 先理解实验中的三道防线

主查询 Tool 的定义是：

```python
def search_orders_for_support(
    status: Literal["paid", "cancelled", "refunded"],
    limit: Annotated[int, Field(ge=1, le=10)] = 5,
) -> list[dict[str, object]]:
```

第一道防线是 input schema：

- `status` 只能是 `paid`、`cancelled`、`refunded`；
- `limit` 必须在 1～10 之间；
- 参数不合法时，FastMCP 不会进入函数体。

第二道防线是 SQL 参数绑定：

```sql
SELECT order_id, status, amount, product
FROM orders
WHERE status = ?
ORDER BY order_id
LIMIT ?
```

SQL 结构由 Server 固定，调用者提供的内容只作为 `?` 对应的值。

第三道防线是数据最小化：

- 最多返回 10 笔；
- 每笔只返回 `order_id`、`status`、`amount`、`product`；
- 数据库中的 `region` 等字段不会出现在结果中。

一次合法查询的数据流如下：

```text
人：“查询已支付订单，最多返回 10 笔”
        ↓
实验 Client：构造 {"status": "paid", "limit": 10}
        ↓
MCP Client：发送 tools/call
        ↓
FastMCP：执行 input schema 校验
        ↓ 参数合法
search_orders_for_support：执行参数绑定查询
        ↓
SQLite：返回订单
        ↓
Tool：只返回允许字段
        ↓
实验 Client：检查数量和字段集合
```

## 3. 场景一：建立合法查询基线

先只运行成功场景：

```bash
uv run labs/mcp/foundations/examples/input_security_client.py query-allowed
```

对应函数：

```text
query-allowed → allowed_query()
```

它使用：

```json
{
  "status": "paid",
  "limit": 10
}
```

这里选择 10，是为了验证最大合法值，而不是只测试常用默认值 5。

你会看到类似输出：

```text
合法查询没有返回 Tool 错误        passed=True
Tool 返回结构化对象              passed=True
结构化结果中包含订单列表          passed=True
返回订单不超过 10 笔             passed=True  count=10
所有订单都只包含允许字段          passed=True
```

这个场景同时验证：

1. 最大合法值能够进入 Tool；
2. 返回数量没有超过限制；
3. 每条记录都只有四个允许字段。

`CallToolResult.structuredContent` 是 Tool 的结构化结果。由于 Python 函数返回
`list`，FastMCP 会把列表包装成：

```python
{"result": [订单列表]}
```

所以 Client 先读取 `structuredContent`，再读取其中的 `result`。

如果某条记录多出 `region`，`invalid_order` 会保存这条记录，字段检查随即失败。

## 4. 场景二：攻击 status 枚举

运行：

```bash
uv run labs/mcp/foundations/examples/input_security_client.py query-invalid-status
```

对应函数：

```text
query-invalid-status → invalid_status_query()
```

实验依次提交：

```text
pending
paid' OR 1=1 --
```

第一个值是普通的枚举外状态，第二个值故意写成 SQL 注入式文本。

预期输出的核心部分是：

```text
拒绝非法 status='pending'           passed=True
非法 status 没有进入查询函数         passed=True  before=0 after=0

拒绝非法 status="paid' OR 1=1 --"  passed=True
非法 status 没有进入查询函数         passed=True  before=0 after=0
```

错误内容中还会出现：

```text
type=literal_error
Input should be 'paid', 'cancelled' or 'refunded'
```

### 如何证明 Tool 没有执行

Server 中的 `QUERY_EXECUTION_COUNT` 只在
`search_orders_for_support()` 进入函数体后增加。

Client 在恶意调用前后分别调用 `get_query_execution_count()`：

```text
调用前 execution_count=0
提交非法参数
调用后 execution_count=0
```

计数没有变化，直接证明非法参数在 FastMCP 校验阶段被拒绝，主查询函数没有
执行，因此 SQLite 也没有收到这次主查询。

这一场景证明的是枚举校验，不是 SQL 参数绑定。

## 5. 场景三：攻击 limit 上下界

运行：

```bash
uv run labs/mcp/foundations/examples/input_security_client.py query-extreme-limit
```

对应函数：

```text
query-extreme-limit → extreme_limit_query()
```

实验提交两个方向的越界值：

```text
limit=0
limit=10000
```

预期核心输出：

```text
拒绝 limit=0                 passed=True
越界 limit 没有进入查询函数    passed=True

拒绝 limit=10000             passed=True
越界 limit 没有进入查询函数    passed=True
```

具体错误分别是：

```text
limit=0      → greater_than_equal
limit=10000  → less_than_equal
```

同样，调用前后的执行计数保持不变。实验不仅观察到错误，还证明查询函数没有运行。

## 6. 场景四：单独验证 SQL 参数绑定

枚举校验会提前拒绝注入式状态，因此仅凭场景二不能证明参数绑定的效果。

为隔离验证这道防线，Server 提供实验专用 Tool：

```text
count_orders_for_status_text
```

它允许普通字符串进入 SQL 参数，但仍使用：

```sql
SELECT COUNT(*) FROM orders WHERE status = ?
```

运行：

```bash
uv run labs/mcp/foundations/examples/input_security_client.py query-parameter-binding
```

对应函数：

```text
query-parameter-binding → parameterized_sql_query()
```

实验先提交：

```text
paid' OR 1=1 --
```

预期结果：

```text
submitted_status: paid' OR 1=1 --
matching_count: 0
total_order_count: 14
```

这说明整段文字只被当作一个状态值：

- 它没有匹配全部订单；
- 它没有改变 SQL 结构；
- `orders` 表仍有 14 笔数据。

实验再提交正常值 `paid`，可以匹配 10 笔订单，证明数据库和对照 Tool 仍能正常工作。

正式查询仍应使用枚举。参数绑定是纵深防御，不是放弃输入限制的理由。

## 7. 最后运行完整回归与排查问题

理解四个单独场景后，再运行全部实验：

```bash
uv run labs/mcp/foundations/examples/input_security_client.py all
```

`SCENARIOS` 将命令行名称映射到实验函数，并按以下顺序执行：

```text
query-allowed
  → query-invalid-status
  → query-extreme-limit
  → query-parameter-binding
```

每条 `check` 都包含：

- `check`：正在验证什么；
- `passed`：是否满足预期；
- `evidence`：用于判断的最小证据。

如果 `passed=False`，脚本会抛出 `AssertionError` 并停止，表示安全边界与实验
预期不一致。

常见问题：

| 现象 | 优先检查 |
| --- | --- |
| 找不到 Server 文件 | 是否在仓库根目录运行；文件是否位于 `examples/` |
| `ModuleNotFoundError: mcp` | 是否已执行 `uv sync` |
| 参数校验文字略有不同 | 本地 MCP/Pydantic 版本是否与仓库环境一致 |
| 某个检查为 `passed=False` | 查看同一行的 `evidence`，不要只看最后的异常 |

## 8. 实验验收

完成后，尝试不看代码回答：

1. `status="pending"` 在哪一层失败？
2. 为什么 `limit=10000` 不会进入查询函数？
3. `before=0, after=0` 提供了什么证据？
4. 枚举校验与 SQL 参数绑定有什么区别？
5. 为什么合法查询还要检查返回字段？
6. `structuredContent["result"]` 中保存的是什么？

最终应形成下面这条判断链：

```text
先限制参数形状和值域
  → 再用参数绑定固定 SQL 结构
  → 最后限制返回数量和字段
  → 用可观察证据证明边界真正生效
```
