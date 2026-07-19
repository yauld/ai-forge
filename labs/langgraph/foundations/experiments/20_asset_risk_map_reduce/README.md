# Asset Risk Map-Reduce

这个实验用“批量检查资产暴露风险”演示 LangGraph 的 `Send`、并行分发与 Map-Reduce。

实验不做真实网络扫描，只使用一组模拟资产。这样可以把注意力放在 LangGraph 的运行机制上：输入里有几个资产，`Send` 就动态发出几个检查任务；每个任务独立完成 Map；最后 Reduce 节点把所有检查结果汇总成一份风险报告。

配套详细文稿：[LangGraph Send：并行分发与 Map-Reduce](../../20%20%7C%20LangGraph%20Send：并行分发与%20Map-Reduce.md)

## 流程

```text
START
  ↓
prepare_scan
  ↓ Send(asset_1), Send(asset_2), ...
check_asset
  ↓ 多个分支通过 reducer 合并 findings
summarize_risks
  ↓
END
```

## 对应关系

- `Send`：根据资产列表动态创建多个 `check_asset` 任务。
- Map：`check_asset` 每次只分析一个资产，输出一条 `finding`。
- Reducer：`findings` 使用列表拼接，合并多个并行分支的结果。
- Reduce：`summarize_risks` 汇总所有 `finding`，生成最终报告。

注意：`findings` 是带 reducer 的字段，Reduce 节点不会再返回 `findings`，否则会触发二次拼接，造成结果重复。

模型使用本地 Ollama 的 `qwen3-coder:30b`。风险等级先由稳定规则判定，模型负责解释单个资产风险和生成最终报告，避免模型输出格式漂移影响实验观察。

## 文件结构

```text
20_asset_risk_map_reduce/
├── main.py       # Send 分发、Map 节点、Reduce 节点、导图和命令行入口
├── asset_schemas.py  # State 类型、资产类型和样例资产
├── risk_rules.py  # 资产风险等级判定规则
├── graphviz_utils.py  # 静态结构图和运行时示意图导出
├── *.png         # 当前实验生成的静态结构图与运行时示意图
└── README.md     # 实验说明
```

这个实验只有一个核心问题：Send 如何把一组资产动态分发出去，再把结果汇总回来。所以最核心的图逻辑、运行逻辑和验证入口都放在 `main.py`；类型定义和样例数据放在 `asset_schemas.py`；资产风险规则放在 `risk_rules.py`；导图细节放在 `graphviz_utils.py`，避免 `main.py` 被辅助代码淹没。

## 运行

从仓库根目录运行：

```bash
uv run \
  python labs/langgraph/foundations/experiments/20_asset_risk_map_reduce/main.py
```

只导出 LangGraph 静态结构图：

```bash
uv run \
  python labs/langgraph/foundations/experiments/20_asset_risk_map_reduce/main.py \
  --graphviz
```

按本次输入资产导出运行时 Map-Reduce 示意图：

```bash
uv run \
  python labs/langgraph/foundations/experiments/20_asset_risk_map_reduce/main.py \
  --runtime-graphviz
```

静态结构图只会出现一个 `check_asset` 节点，因为 LangGraph 里只定义了一个 Map 节点。运行时示意图会把每个资产展开成一个分支，更适合解释 `Send(asset_1)`、`Send(asset_2)` 这类动态分发。

## 自定义资产

可以传入一个 JSON 文件。格式是资产对象数组：

```json
[
  {
    "host": "test.example.com",
    "open_ports": [80, 8080],
    "has_https": false,
    "tags": ["test-env", "public"],
    "exposed_paths": ["/debug", "/actuator"]
  }
]
```

运行：

```bash
uv run \
  python labs/langgraph/foundations/experiments/20_asset_risk_map_reduce/main.py \
  --assets /path/to/assets.json
```
