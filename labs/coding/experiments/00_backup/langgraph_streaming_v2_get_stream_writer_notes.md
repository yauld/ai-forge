# LangGraph Streaming v2 与 get_stream_writer 速查

这份笔记解释几个容易混在一起的概念：

- `graph.stream(...)`
- `stream_mode`
- `version="v2"`
- `get_stream_writer()`
- `custom`
- `updates`
- `event`

配套脚本：

```bash
uv run python labs/coding/examples/langgraph_get_stream_writer_demo.py
```

---

## 一、先记住一句话

```text
version="v2" 决定事件长什么样。
stream_mode 决定你要看哪些事件。
get_stream_writer() 只负责在节点里制造 custom 事件。
```

它们不是同一个东西。

---

## 二、graph.stream(...) 是什么

`graph.stream(...)` 表示：**运行这张图，并在运行过程中不断吐出事件**。

普通 `invoke()` 是等图全部跑完：

```python
result = graph.invoke(input_state)
```

`stream()` 是边跑边看：

```python
for event in graph.stream(
    input_state,
    stream_mode=["custom", "updates"],
    version="v2",
):
    print(event)
```

这里要区分两层：

```text
graph.stream(...)
    -> 返回一个事件流 / 可迭代对象，不是单个事件

for event in graph.stream(...):
    -> event 才是事件流里的一条事件
```

也就是说，`graph.stream(...)` 的返回值不是一条 `event`，而是一串可以逐个取出的事件。

---

## 三、version="v2" 是什么

`version="v2"` 是 streaming 的事件格式。

之所以叫 v2，是因为 LangGraph 早期已经有一套旧的 streaming 返回格式。旧格式在单个 `stream_mode` 和多个 `stream_mode` 时，返回结构不完全一致；v2 的目标就是把事件结构统一起来。

开启后，每条事件统一长这样：

```python
{
    "type": "custom",
    "ns": (),
    "data": {...},
}
```

三个字段分别是：

| 字段 | 含义 |
| --- | --- |
| `type` | 事件类型，例如 `custom`、`updates`、`values`、`messages` |
| `ns` | namespace，后面遇到子图时用于区分事件来源 |
| `data` | 真正的数据 |

所以 `version="v2"` 解决的是：

```text
不管你开一个 mode 还是多个 mode，事件都按同一种结构返回。
```

简化对比：

```text
旧格式：不同 stream_mode 组合下，返回结构可能变化。
v2 格式：统一返回 {"type": ..., "ns": ..., "data": ...}。
```

---

## 四、stream_mode 是什么

`stream_mode` 决定你要订阅哪些事件类型。

常见选项：

| stream mode | 含义 |
| --- | --- |
| `updates` | 看节点写回 State 的增量 |
| `values` | 看每一步之后的完整 State |
| `custom` | 看节点主动发出的自定义过程事件 |
| `messages` | 看模型逐 token 输出 |

例如：

```python
stream_mode=["custom", "updates"]
```

意思是：

```text
这次运行图，我同时想看 custom 事件和 updates 事件。
```

---

## 五、updates 是什么

`updates` 表示：**节点 return 写回 State 之后产生的状态更新事件**。

节点里：

```python
def load_asset_profile(state):
    return {
        "asset_profile": "公网 Web 服务器",
    }
```

外层开启：

```python
graph.stream(
    input_state,
    stream_mode="updates",
    version="v2",
)
```

就能看到类似事件：

```python
{
    "type": "updates",
    "ns": (),
    "data": {
        "load_asset_profile": {
            "asset_profile": "公网 Web 服务器"
        }
    },
}
```

所以 `updates` 回答的是：

```text
刚刚哪个节点执行完了？
它往 State 里写了什么？
```

---

## 六、custom 是什么

`custom` 表示：**节点主动发出来的自定义过程事件**。

节点里：

```python
from langgraph.config import get_stream_writer


def load_asset_profile(state):
    writer = get_stream_writer()
    writer({
        "stage": "asset",
        "message": "正在读取资产画像",
    })

    return {
        "asset_profile": "公网 Web 服务器",
    }
```

外层开启：

```python
graph.stream(
    input_state,
    stream_mode="custom",
    version="v2",
)
```

就能看到类似事件：

```python
{
    "type": "custom",
    "ns": (),
    "data": {
        "stage": "asset",
        "message": "正在读取资产画像",
    },
}
```

所以 `custom` 回答的是：

```text
节点运行过程中，想额外告诉外部什么？
```

典型用途：

- 进度提示；
- 当前阶段；
- 正在处理哪个对象；
- 前端状态条；
- 审计面板里的过程信息。

---

## 七、get_stream_writer() 是什么

`get_stream_writer()` 是 LangGraph 提供的函数，用来在节点内部拿到一个 `writer`。

这个 `writer` 可以发送 `custom` 事件：

```python
writer = get_stream_writer()
writer({"message": "正在处理"})
```

它只负责一件事：

```text
在节点内部制造 custom 事件。
```

它不负责：

- 更新 State；
- 控制节点跳转；
- 替代日志库；
- 替代 `return {...}`。

最重要的区别：

```text
writer({...}) 发 custom 事件，不写 State。
return {...} 写 State，产生 updates 事件。
```

---

## 八、它们之间的关系

可以按三层理解。

第一层：事件格式

```python
version="v2"
```

决定每条事件统一长这样：

```python
{"type": ..., "ns": ..., "data": ...}
```

第二层：订阅哪些事件

```python
stream_mode=["custom", "updates"]
```

表示外层要同时看：

- `custom`：节点主动发出的过程事件；
- `updates`：节点写回 State 的更新事件。

第三层：制造 custom 事件

```python
writer = get_stream_writer()
writer({...})
```

表示节点内部主动发一条 `custom` 事件。

---

## 九、一个节点会产生几条事件

看这个节点：

```python
def summarize_risk(state):
    writer = get_stream_writer()

    writer({"stage": "summary", "message": "开始汇总风险"})
    writer({"stage": "summary", "message": "正在应用风险规则"})

    return {"risk_level": "high"}
```

如果外层开启：

```python
stream_mode=["custom", "updates"]
```

那么这个节点可能产生：

```text
第 1 条 custom：开始汇总风险
第 2 条 custom：正在应用风险规则
第 3 条 updates：{"risk_level": "high"}
```

所以可以这样记：

```text
writer(...) 调几次，就可能有几条 custom event。
return {...} 一次，就通常有一条 updates event。
```

---

## 十、event 是什么

在这段代码里：

```python
for event in graph.stream(
    input_state,
    stream_mode=["custom", "updates"],
    version="v2",
):
    print(event)
```

`event` 是：

```text
graph.stream(...) 这条事件流里吐出来的一条事件。
```

如果 `event["type"] == "custom"`：

```python
event["data"]
```

就是节点里 `writer({...})` 传入的内容。

如果 `event["type"] == "updates"`：

```python
event["data"]
```

就是节点 `return {...}` 后产生的 State 更新。

所以常见处理方式是：

```python
for event in graph.stream(
    input_state,
    stream_mode=["custom", "updates"],
    version="v2",
):
    if event["type"] == "custom":
        print("过程事件：", event["data"])

    elif event["type"] == "updates":
        print("状态更新：", event["data"])
```

---

## 十一、常见误区

### 误区 1：Streaming v2 必须配合 get_stream_writer 使用

不对。

`version="v2"` 可以单独使用：

```python
graph.stream(
    input_state,
    stream_mode="updates",
    version="v2",
)
```

这完全不需要 `get_stream_writer()`。

更准确的说法是：

```text
只有当你想使用 custom 事件时，才需要 get_stream_writer()。
```

### 误区 2：writer({...}) 会更新 State

不对。

`writer({...})` 只发送 custom 事件。

要更新 State，必须：

```python
return {"some_field": "some_value"}
```

### 误区 3：custom 和 updates 是自己随便起的名字

不对。

`custom` 和 `updates` 是 LangGraph 预定义的 stream mode 名字。

你可以自定义的是 `writer({...})` 里面的内容：

```python
writer({
    "stage": "asset",
    "message": "正在读取资产画像",
    "progress": 0.3,
})
```

这里的 `stage`、`message`、`progress` 是你自己定义的。

### 误区 4：开启 custom 就一定有 custom 事件

不一定。

你外层写了：

```python
stream_mode="custom"
```

但节点里没有调用：

```python
writer({...})
```

那就没有 custom 事件可看。

---

## 十二、最小完整例子

```python
from typing import TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph


class State(TypedDict):
    asset_id: str
    risk_level: str


def check_asset(state: State):
    writer = get_stream_writer()

    # custom 事件
    writer({
        "stage": "check",
        "message": f"正在检查 {state['asset_id']}",
    })

    # updates 事件
    return {
        "risk_level": "high",
    }


builder = StateGraph(State)
builder.add_node("check_asset", check_asset)
builder.add_edge(START, "check_asset")
builder.add_edge("check_asset", END)
graph = builder.compile()

input_state = {
    "asset_id": "asset-prod-01",
    "risk_level": "",
}

for event in graph.stream(
    input_state,
    stream_mode=["custom", "updates"],
    version="v2",
):
    print(event)
```

你会看到两类事件：

```text
custom：来自 writer({...})
updates：来自 return {...}
```

---

## 十三、最终心智模型

```text
节点内部：

    writer({...})
        -> 发过程事件
        -> 外层用 stream_mode="custom" 接收

    return {...}
        -> 写回 State
        -> 外层用 stream_mode="updates" 接收


图运行外层：

    graph.stream(..., stream_mode=[...], version="v2")
        -> 决定订阅哪些事件
        -> 每条事件统一是 {"type": ..., "ns": ..., "data": ...}
```

一句话收束：

```text
stream_mode 决定你看什么；
version="v2" 决定事件格式；
get_stream_writer() 只负责发 custom 过程事件。
```
