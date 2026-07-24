# LangGraph Handoff 之 Multi-Agent

上一篇《LangGraph Supervisor之Multi-Agent》中，讲的旅游规划的多agnet示例，控制权关系是：

```text
Supervisor -> 子Agent
子Agent做完 -> 回到Supervisor
Supervisor再决定下一个子Agent
```

这种示例当然也可以用Supervisor实现，靠的是让一个中心Agent统一读取State，再决定下一步调用哪个Agent。

但“下一步调用哪个Agent”，其实不一定非要回到Supervisorsor里才能知道，完全可以由当前处理的Agent自己判断出来，这就要用到另一种控制关系：handoff。

handoff的思想不是中心Agent统一调度所有角色，而是当前Agent在自己的职责边界处主动移交控制权。

---

当用户问：

```
我买的智能门锁第15天开始无法连接App，重启和重新配网都失败。
我现在想退货退款，但普通退货期好像已经过了。
```

我们用一个小的客服工单实验，来看Handoff是怎么设计实现的。

---

## 1. 先看请求是怎么流转

实验里设计三个Agent：

```text
refund_agent
  退款Agent，只负责退款政策判断，不能做技术故障诊断。

technical_agent
  技术Agent，只负责判断是否疑似商品故障，不能批准退款。

human_agent
  人工升级Agent，负责处理超过普通政策范围的例外审批。
```

用户的问题进来后，完整的预期效果是：

1. 先经过退款Agent，它先判断如果缺少故障证据，所以交给技术Agent。
2. 技术Agent完成初步诊断后，不能退款，所以交回退款Agent。
3. 退款Agent发现这是普通政策外的例外，所以交给人工升级Agent。
4. 人工升级Agent做最终处理，然后结束。

默认运行路径是：

![Handoff客服工单执行路径图](../../labs/langgraph/foundations/experiments/27_handoff_support_ticket/handoff_support_ticket_runtime.png)

## 2. 设计State

SupportState主要分三类字段：原始工单信息、各Agent写回的处理结果、Handoff过程记录。

```python
class SupportState(TypedDict, total=False):
    customer_message: str  # 用户提交的原始客服诉求
    order_days: int  # 下单距今天数，用于判断是否超过普通退货期
    product_name: str  # 当前工单涉及的商品名称
    amount: int  # 订单金额，人工审批时可作为参考

    refund_case: dict # 退款Agent将处理结果写在这里
    technical_diagnosis: dict # 技术审查Agent将结果写在这里
    human_review: dict  # 人工审查Agent将结果写在这里

    current_agent: str  # 当前拿到控制权的Agent
    handoff_count: int  # 已经发生的移交次数
    max_handoff_count: int  # 本次运行允许的最大移交次数
    handoff_reason: str  # 最近一次移交的原因
    handoff_history: Annotated[list[dict], operator.add]  # 完整移交历史
    trace: Annotated[list[str], operator.add]  # 简短运行轨迹
    final_status: str  # 最终状态，例如success或failed
```

一开始只有用户诉求、商品、订单天数、金额：

```python
initial_state: SupportState = {
    "customer_message": (
        "我买的智能门锁第15天开始无法连接App，重启和重新配网都失败。"
        "我现在想退货退款，但普通退货期好像已经过了。"
    ),
    "product_name": "智能门锁",
    "order_days": 15,
    "amount": 1299,
    "max_handoff_count": MAX_HANDOFF_COUNT,
}

result = graph.invoke(initial_state)
```

这也是传给graph.invoke的一份初始State

## 3. Agent不只返回结果，还要返回移交意图

Handoff和Supervisor最大的不同是，

Handoff中当前Agent处理完它自己的事后，他会主动告诉图它建议下一步交给哪个Agent

所以需要先定义一个HandoffDecision，它包含两个意图参数：target和reason

```python
class HandoffDecision(BaseModel):
    target: HandoffTarget # 下一步跳到哪个Agent
    reason: str = Field(min_length=1) # 为啥要跳到那个Agent的原因
```

然后，每个Agent的结构化输出都会带一个handoff，比如退款Agent

```python
class RefundResult(BaseModel):
    summary: str # 退款诉求和当前处理背景的简短概括
    policy_status: Literal[
        "needs_technical_evidence",
        "needs_human_approval",
        "approved",
        "rejected",
    ] # 当前退款政策状态
    decision: str # 退款Agent给出的政策判断说明
    handoff: HandoffDecision # <-- 重点是这里，退款Agent建议下一步交给谁，包括target和reason两个意图参数
```

技术Agent和人工升级Agent也同样的，一部分字段表示业务结果，最后的handoff表示移交意图。

## 4. 不能让模型随便跳节点

有了handoff.target后，不能说模型想去哪就去哪，比如

- 退款Agent如果直接跳finish，就绕过了技术诊断
- 技术Agent如果直接跳human_agent，就绕过了退款政策判断

所以还需要有人为的白名单这一层限制

```python
ALLOWED_HANDOFFS: dict[str, set[HandoffTarget]] = {
    "refund_agent": {"technical_agent", "human_agent", "finish"},
    "technical_agent": {"refund_agent"},
    "human_agent": {"finish"},
}
```
即：
- 退款Agent可以交给技术Agent、人工审核Agent，或者直接结束
- 技术Agent只能交回退款Agent
- 人工升级Agent只能结束

## 5. 封装一个统一函数来执行合法的Agent移交

Agent提出handoff.target之后，还不能直接跳转

中间需要自定义一个validate_and_execute_handoff的统一函数来做三件事：

```text
1. 检查目标是否在ALLOWED_HANDOFFS里
2. 检查移交次数是否超过上限
3. 通过后返回Command，让LangGraph真正跳到下一个节点
```
类似：

```python
next_count = state.get("handoff_count", 0) + 1
max_count = state.get("max_handoff_count", MAX_HANDOFF_COUNT)
allowed = ALLOWED_HANDOFFS.get(current_agent, set())

if decision.target not in allowed:
    violation = f"{current_agent} 不允许移交给 {decision.target}"
elif next_count > max_count:
    violation = f"Handoff次数 {next_count} 超过上限 {max_count}"
```

如果模型提出非法目标，target会被改成failed，合法才返回Command继续走

```python
return Command(
    update={
        **update,
        "current_agent": target,
        "handoff_count": next_count,
        "handoff_reason": record["reason"],
        "handoff_history": [record],
    },
    goto=target,
)
```

而Command就看两个字段

```text
update：写回业务结果和移交历史
goto：跳到下一个节点
```

敲重点：goto用的是经过程序校验后的target，所以基本可放心跳转。

## 6. refund_agent：第一次为什么交给technical_agent

图从退款Agent开始：

```python
builder.add_edge(START, "refund_agent")
```

第一次进入refund_agent时，State里还没有technical_diagnosis

所以退款Agent不能直接做最终退款判断。

兜底逻辑

```python
if not isinstance(technical_diagnosis, dict):
    refund_case["policy_status"] = "needs_technical_evidence"
    decision = HandoffDecision(
        target="technical_agent",
        reason="退款判断缺少故障证据，需要技术Agent先确认问题性质",
    )
```

第一次运行时就没经过技术Agent判断，所以能看到

```text
政策状态：needs_technical_evidence
下一步移交：technical_agent，原因：退款判断缺少故障证据，需要技术Agent先确认问题性质

[refund_agent] handoff -> technical_agent: 退款判断缺少故障证据，需要技术Agent先确认问题性质
```

说明了，当前Agent不是固定往下走，而是根据当前State判断自己缺什么，然后把控制权交给能补信息的Agent。

## 7. technical_agent：诊断完为什么交回refund_agent

技术Agent只做技术判断，不批准退款。

提示词里也写得很清楚

```text
你是技术Agent，只负责判断商品是否存在故障，不负责退款审批。
诊断完成后handoff.target必须是refund_agent，把故障证据交回退款Agent。
```

运行时输出类似

```text
诊断商品：智能门锁
是否疑似商品故障：True
下一步移交：refund_agent，原因：已完成技术故障诊断，需移交退款审批

[technical_agent] handoff -> refund_agent: 已完成技术故障诊断，需移交退款审批
```

再敲重点：当前实现里的“诊断结论”是模型根据用户描述做出的初步推断（它自己盲猜的）。

## 8. refund_agent：第二次为什么交给human_agent

技术Agent把technical_diagnosis写回State后，退款Agent第二次拿到工单。

这时候它看到defect_likely为True，order_days是15

意思是【疑似商品故障成立，但普通退货期已经过了】属于政策例外了，会要求升级到人工Agent来处理

```python
elif technical_diagnosis.get("defect_likely") and state.get("order_days", 0) > 7:
    refund_case["policy_status"] = "needs_human_approval"
    decision = HandoffDecision(
        target="human_agent",
        reason="技术诊断确认疑似商品故障，但订单已超过普通退货期，需要人工审批",
    )
```

运行输出：

```text
政策状态：needs_human_approval
下一步移交：human_agent，原因：技术诊断确认疑似商品故障，但订单已超过普通退货期，需要人工审批

[refund_agent] handoff -> human_agent: 技术诊断确认疑似商品故障，但订单已超过普通退货期，需要人工审批
```

这一步很Handoff，体现在，退款Agent已经明确知道这超出普通退款政策，应该升级给human_agent。

## 9. human_agent：最终审批并结束

人工升级Agent读取refund_case和technical_diagnosis，然后给出最终处理意见：

```text
最终决定：approve_refund
下一步移交：finish，原因：已完成例外退款审批

[human_agent] handoff -> finish: 已完成例外退款审批
[finish] Handoff流程正常结束
```

human_agent的白名单只有

```python
"human_agent": {"finish"}
```

所以它完成最终处理后，只能结束。

## 10. 用handoff_history回看完整移交过程

如果只看最终结果，很难知道几个Agent是怎么配合的，所以实验里记录了handoff_history

```text
{'from': 'refund_agent', 'to': 'technical_agent', 'reason': '退款判断缺少故障证据，需要技术Agent先确认问题性质', 'count': 1}

{'from': 'technical_agent', 'to': 'refund_agent', 'reason': '已完成技术故障诊断，需移交退款审批', 'count': 2}

{'from': 'refund_agent', 'to': 'human_agent', 'reason': '技术诊断确认疑似商品故障，但订单已超过普通退货期，需要人工审批', 'count': 3}

{'from': 'human_agent', 'to': 'finish', 'reason': '已完成例外退款审批', 'count': 4}
```

这份记录能回答你：
```
谁把控制权交出去了，交给了谁，为什么交。在真实业务里，这就是审计线索。
```

## 11. Handoff和Supervisor到底差在哪

Supervisor是

```text
Supervisor -> 子Agent -> Supervisor -> 子Agent -> Supervisor
```

Handoff是

```text
Agent A -> Agent B -> Agent A -> Agent C -> finish
```

差别在控制权：

1、Supervisor模式里，中心Agent掌握全局调度权，专业Agent做完后回到中心。

2、Handoff模式里，当前Agent根据自己的结果主动提出下一个接手者，程序只负责检查这个移交是否合法。

---

```text
GitHub 仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/langgraph/foundations/27 | Handoff 多 Agent：多个 Agent 如何自主移交控制权.md

实验代码：
labs/langgraph/foundations/experiments/27_handoff_support_ticket/
```
