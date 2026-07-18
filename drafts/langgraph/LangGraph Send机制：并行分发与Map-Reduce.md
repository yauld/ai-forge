# LangGraph Send机制：把一组任务分发出去，再把结果收回来

我有一组东西，每个都要处理，最后再汇总。

比如：10条用户反馈，要并行且分别提炼问题，再生成一份产品改进建议。

此时，可以考虑用LangGraph里的Send。

## 1. Send是什么

简单理解就是

> 在运行时，动态创建一个节点调用。

普通边像这样：

```text
当前节点结束后，去固定的下一个节点。
```

Send像这样：

```text
当前节点结束后，根据当前数据，临时发出N个任务。
```

比如当前有3条反馈：

```python
feedbacks = [
    "搜索结果不准",
    "页面加载太慢",
    "导出报表经常失败",
]
```

那就可以生成3个Send：

```text
Send(反馈1 -> analyze_feedback)
Send(反馈2 -> analyze_feedback)
Send(反馈3 -> analyze_feedback)
```

这不是提前定义了3个节点，图里仍然只有一个analyze_feedback节点，只是运行时，它会被调用多次。

## 2. Map是什么

Map的意思是：

> 对一组输入里的每个元素，分别执行同一段处理逻辑。

在这个例子里：

```text
一条用户反馈 -> 一条分析结果
```

这就是Map。

对应的节点可以叫analyze_feedback：

```python
async def analyze_feedback(state: FeedbackTaskState) -> AppState:
    feedback = state["feedback"]

    summary = await llm.ainvoke(
        f"请分析这条用户反馈，提炼核心问题：{feedback}"
    )

    return {
        "analyses": [summary.content]
    }
```

Map节点只处理一条反馈，其他的都不管，有点像一个单一的功能函数。

## 3. Send如何触发多个Map

关键的问题：怎么让每条反馈都进入analyze_feedback？

用Send

```python
from langgraph.types import Send


def send_each_feedback_to_analyzer(state: AppState) -> list[Send]:
    sends = []
    for feedback in state["feedbacks"]:
        sends.append(
            Send("analyze_feedback", {"feedback": feedback})
        )
    return sends
```

意思是：

```text
feedbacks里有几条反馈，就创建几个analyze_feedback调用。
```

如果有3条反馈，就创建3个任务，有100条反馈，就创建100个任务。。。

LangGraph看到这些Send后，才会去调度对应的节点调用。

## 4. Reduce是什么

Map处理完之后，会得到一堆中间结果。

比如：

```text
反馈1分析结果：搜索召回不稳定
反馈2分析结果：性能体验差
反馈3分析结果：报表导出链路不可靠
```

Reduce要干的事就是把这些中间结果合并成一个最终结果。

在这个例子里，Reduce节点可以叫summarize_feedbacks：

```python
async def summarize_feedbacks(state: AppState) -> AppState:
    analyses = state["analyses"]

    report = await llm.ainvoke(
        f"请根据这些用户反馈分析，生成一份产品改进建议：{analyses}"
    )

    return {
        "final_report": report.content
    }
```

前面的Map节点可能执行3次、30次、300次，但Reduce节点通常只执行1次，就是讲所有收集到的信息做一次大模型的调用总结。

## 5. Reducer：Map和Reduce中间的胶水

这里还有一个容易混淆的点：

Map节点返回了很多结果，它们怎么进入同一个state["analyses"]？

这要靠的是LangGraph的reducer（它与send里说的reduce不是一个玩意）

State可以这样定义：

```python
import operator
from typing import Annotated, TypedDict


class AppState(TypedDict):
    feedbacks: list[str]
    analyses: Annotated[list[str], operator.add]
    final_report: str
```

重点是这一行：

```python
analyses: Annotated[list[str], operator.add]
```

它告诉LangGraph：

```text
如果多个分支都返回analyses，就用列表加法把它们拼起来。
```

每个Map分支返回：

```python
{"analyses": [summary]}
```

多个分支合并后就变成：

```python
{
    "analyses": [
        "搜索召回不稳定",
        "性能体验差",
        "报表导出链路不可靠",
    ]
}
```

所以完整关系是：

```text
Send：把任务发出去
Map：分别处理每个任务
Reducer：把Map结果合并回来
Reduce：基于合并结果生成最终输出
```

## 6. 整个图长什么样

类似这样：

```text
START
  ↓
dispatch_feedbacks
  ├─ Send(feedback_1) -> analyze_feedback -> analysis_1
  ├─ Send(feedback_2) -> analyze_feedback -> analysis_2
  └─ Send(feedback_3) -> analyze_feedback -> analysis_3
                                      ↓
                              reducer合并analyses1、2、3
                                      ↓
                              summarize_feedbacks
                                      ↓
                                    END
```


## 7. 最小图代码

把上面的逻辑串起来，把它想象成这样：

```python
from langgraph.graph import START, END, StateGraph


builder = StateGraph(AppState)

builder.add_node("dispatch_feedbacks", dispatch_feedbacks)
builder.add_node("analyze_feedback", analyze_feedback)
builder.add_node("summarize_feedbacks", summarize_feedbacks)

builder.add_edge(START, "dispatch_feedbacks")

builder.add_conditional_edges(
    "dispatch_feedbacks",
    send_each_feedback_to_analyzer,
    ["analyze_feedback"],
)

builder.add_edge("analyze_feedback", "summarize_feedbacks")
builder.add_edge("summarize_feedbacks", END)

graph = builder.compile()
```

1. send_each_feedback_to_analyzer返回list[Send]
2. analyze_feedback每次只处理一条反馈
3. analyses字段用reducer合并多个Map结果


只要这三件事成立，Map-Reduce的骨架就成立了。

## 8. 什么时候适合用Send

可以用三个问题判断：

第一，输入是不是一组元素？

比如一组文档、一组反馈、一组告警、一组网页、一组候选方案。

第二，每个元素能不能先独立处理？

如果每条反馈可以单独分析，每篇文档可以单独总结，就适合Map。

第三，最后是不是需要统一汇总？

如果只是分别处理完就结束，那只是批处理。

如果最后还要生成总报告、总排序、总判断，那就是Map-Reduce。

## 9. LangGraph里的Send + Map-Reduce可以这样记

```text
一组输入
  ↓
Send动态分发
  ↓
Map分别处理
  ↓
Reducer合并结果
  ↓
Reduce生成最终输出
```

这就是它最核心的脉络。

---

完整实验代码：

https://github.com/yauld/ai-forge
labs/langgraph/foundations/experiments/20_asset_risk_map_reduce
