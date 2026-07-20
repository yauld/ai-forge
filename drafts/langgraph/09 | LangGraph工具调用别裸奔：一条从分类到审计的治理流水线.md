# 09 | LangGraph工具调用别裸奔：一条从分类到审计的治理流水线

假设你在一个类似AI安全运维系统里问了下面一句

```text
给我封禁这个IP: xx.xx.xx.xx
```

如果这还只是一个demo系统，Agent可能很快按照一段漂亮流程执行：

```text
识别用户意图
  ↓
选择block_ip工具
  ↓
执行封禁
  ↓
回复用户：已处理
```

看起来智能，但若是一个真实的接入生产的安全运维系统，这个搞法有点吓人。

封禁IP这类敏感的写操作，不是查天气，也不是总结一段文本，而是一个有副作用的动作，它可能会改变外部系统状态，可能影响真实用户、真实服务、真实业务。。

所以在Agent调用block_ip之前，最好还要搞清下面这些地方都咋处理

1、它凭什么能调用block_ip？

2、谁批准的？

3、失败了怎么办？

4、事后怎么查？

5、等

## 1. 问题不在block_ip，而在少了中间关卡

【识别用户意图=》选择block_ip工具=》执行封禁=》回复用户：已处理】，这条流程最大的问题是

```text
模型刚说“我觉得应该封这个IP”，
系统马上就真的去封了。
```

这中间少了一步确认

```text
这个请求真的是封禁请求吗？
block_ip这个工具适合当前请求吗？
这个动作不需要人批准吗？
```

模型最多只能提出建议：觉得这里应该调用block_ip，参数大概是这些，

但系统必须再检查一遍：这次到底允不允许执行？

所以我们需要把一次工具调用拆开。

不是

```text
模型决定 -> 工具执行
```

而是类似下面的处理思路

```text
分类 -> 规划 -> 策略 -> 审批 -> 执行 -> 错误处理 -> 重试/降级 -> 审计 -> 回复
```

我暂且把这个线路叫做【工具调用的治理流水线】，乍一看节点线路是挺长，也挺绕的，但每一段都有明确作用。

对应到Graph里，大概是这样

![工具调用治理流水线](../../labs/langgraph/foundations/experiments/23_tool_governance_console/tool_governance_graphviz.png)

读图时可以先不用纠结每条分支，只记住一个大方向：请求从分类、规划、策略、审批一路往下走；能执行才进入execute_tool，不能执行或已经被拒绝，就直接进入审计。

## 2. 这个请求先经过分类节点

问题问的是：帮我封禁这个IP，第一步不是调用工具，而是先分类。

在安全运维工具执行台里，我们把动作粗略分成三类：

```text
readonly：只读查询这一类
high_risk_write：高风险写操作这一类
unknown：无法判断，转人工的这一类
```

而封禁IP显然不是只读查询，它应该被分到：high_risk_write

这一步简单但关键，因为后面的策略、审批、执行，都是基于这个分类继续走的。

## 3. 然后进入规划节点

分类之后，才是规划，规划节点负责把用户请求变成：

```text
准备调用哪个工具？
准备传什么参数？
```

对于“封禁这个IP”的这个问题，规划结果可能是：

```text
planned_tool: block_ip
tool_args:
  ip: 192.0.2.10
  reason: 用户请求封禁可疑来源
```

到治理它还依然只是形成了一个“准备执行的计划”，搞清这个区别很重要：

```text
planned_tool不是已经执行的工具。
tool_args也不是已经发送出去的参数。
```

它们只是后续检查的对象。

## 4. 第一道真正的门：策略检查

分类节点可以知道你的问题类型是readonly，还是high_risk_write还是unknown

规划节点可以知道你的问题打算要用的是哪个工具，使用啥参数

有了分类，也有了规划之后，策略检查其实就问一个问题：

```text
这个问题类型，是否允许使用这个工具？
```

比如问题类型是readonly，那它只应该使用只读工具，类似下面这几个
```text
lookup_asset
query_exposure
check_ip_reputation
```

再比如问题类型如果是high_risk_write，它就应该仅使用支持的是写操作工具

```text
block_ip
add_account_to_watchlist
```

策略检查这个节点，也可以这么简单的理解：

1、readonly请求，只能使用readonly工具。

2、high_risk_write请求，只能使用写操作工具。

3、unknown请求，不自动执行，直接转人工。

代码逻辑大概是：

```python
def enforce_tool_policy(state):
    action_type = state.get("action_type")
    planned_tool = state.get("planned_tool")
    allowed_tools = ALLOWED_TOOLS_BY_ACTION_TYPE.get(action_type, {})

    if planned_tool in allowed_tools:
        return {"tool_status": "pending"}

    return {
        "tool_status": "failed",
        "tool_error": {"type": "tool_not_allowed"},
    }
```

所以策略检查只回答：这个工具在这个动作类型下能不能被允许？

## 5. 第二道门：人工审批

现在请求已经走到这里，看一下当前的state

```text
分类：high_risk_write
规划：block_ip
策略：允许进入下一关
```

因为block_ip是高风险写操作，所以还不能直接执行这个工具调用，需要人工审批。（readonly的工具调用一般情况下不需要人工审批）

这里的人工审批，用LangGraph里的interrupt()，让图停下来

```python
approval_result = interrupt(
    {
        "question": "这个高风险工具动作是否允许执行？",
        "planned_tool": state.get("planned_tool", ""),
        "tool_args": state.get("tool_args", {}),
        "expected_resume_shape": {
            "decision": "approved 或 denied",
            "operator": "审批人",
            "reason": "审批原因",
        },
    }
)
```

意思是

```text
图先停在这
把要执行的工具和参数展示给外部审批人
等外部用Command(resume=...)把审批结果传回来
```

倘若传回来的是

```python
{"decision": "approved", "operator": "alice", "reason": "已确认恶意来源"}
```

图就继续往下走，进入真正的工具执行节点了，这一步把“模型建议调用工具”和“人批准执行工具”分开，其实就是进入Human-in-the-loop了。

## 6. 批准之后，工具才真正执行

只有当审批结果是approved，才会走到execute_tool，才是真的调用block_ip

```text
block_ip(
  ip="192.0.2.10",
  reason="用户请求封禁可疑来源"
)
```

所以至此，完整主线是

```text
用户请求封禁IP
  ↓
分类为high_risk_write
  ↓
规划成block_ip
  ↓
策略检查通过
  ↓
interrupt暂停等待审批
  ↓
人工approved
  ↓
执行block_ip
  ↓
写入审计日志
  ↓
回复用户
```

回看一下你会发现，这已经和文章一开始那种【模型规划后直接执行】的“漂亮的智能的流程”完全不是一回事了。

## 7. 如果人工拒绝呢？

再看同一个请求的另一条岔路，还是：帮我封禁这个IP。的这个问题

分类、规划、策略检查都一样，图依然会停在审批节点，但这次审批人传回：

```python
{"decision": "denied", "operator": "alice", "reason": "证据不足"}
```

这时流程会直接进入审计，不会进入execute_tool（第1节给出的graph结构也是这个逻辑）

而audit_log里记录了下面这些，说明危险动作确实被挡住了。

```text
approval: denied
tool_status: denied
```

## 8. 如果规划错了呢？

换一个请求，比如问的是：请查询xxxx错误示例，

因为有“查询”这个关键字，所以第一个节点的分类结果是：readonly

正常情况下，readonly只能使用只读工具，比如query_exposure、lookup_asset。

但为了测试策略检查节点有没有用，我们故意让规划节点犯错，让它使用：

```text
planned_tool: block_ip
```

翻译过来就是

```text
用户明明是普通的查询（只读类型
规划却给了一个封禁工具（可写工具
```

这时候策略节点会发现

```text
action_type: readonly
planned_tool: block_ip
allowed_tools: lookup_asset, query_exposure, check_ip_reputation
```

block_ip不在readonly允许工具集合里，所以结果是

```text
tool_status: failed
tool_error.type: tool_not_allowed
```

然后，流程直接进入审计，不会进入工具执行。

这个也证明了一件事：就算规划错了，策略节点也能在执行前拦住越权工具。

## 9. 如果工具自己失败了呢？

再看一个只读请求：请查询unstable.example.com的暴露服务。

分类结果是readonly

规划结果是query_exposure

策略检查也能通过

只读动作不需要人工审批，所以会直接进入工具执行。

上面这些都没问题，但！！！这个工具执行时超时了

```text
error：exposure scanner timeout
```

如果异常直接抛出去，整张图就崩了。（崩了：后面没有重试，没有人工工单，没有审计，更没有llm给你回复了）

所以execute_tool节点要捕获异常，把它写回State：

```python
try:
    result = tool(**tool_args)
    return {
        "tool_status": "success",
        "tool_result": result,
        "tool_error": {},
    }
except Exception as exc:
    return {
        "tool_status": "failed",
        "tool_error": {
            "type": "tool_runtime_error",
            "message": str(exc),
        },
    }
```

Exception里的return异常，要确保的是，工具执行可以失败，但图不能走不下去，工具失败只是进入了一个可处理状态。

接下来，在retry_or_fallback节点里会判断：
```
如果没有触发最大重试次数，就重试
```

如果达到最大重试次数后仍然失败，就创建人工处理工单

```text
tool_status: ticket_created
manual_ticket: SEC-MANUAL-001
```

这比直接报错要稳得多，系统没有假装成功，也没有无限重试，更没有让整张图崩掉。

## 10. 最后一定要有audit_log

前面看了几类测试路径：

```text
审批通过：执行工具
审批拒绝：不执行工具
策略拦截：执行前拒绝
工具失败：重试后转人工
```

这些路径最后都是要进入audit_log，因为审计日志要回答的是

```text
用户请求是什么？
系统怎么分类？
规划了哪个工具？
参数是什么？
策略有没有放行？
审批人是谁？
审批结果是什么？
工具有没有执行？
结果是什么？
失败后有没有重试？
最后有没有转人工？
```

audit_log代表的是这次工具调用的证据链，其重要性不需要过多解释。

## 11. 现在再看整条工具治理流水线

```text
分类 -> 规划 -> 策略 -> 审批 -> 执行 -> 错误处理 -> 重试/降级 -> 审计 -> 回复
```

它其实是在回答一次工具调用里的几个现实问题

```text
1、分类：这是什么类型的动作？
2、规划：准备调用哪个工具？
3、策略：这个类型允许用这个工具吗？
4、审批：危险动作有没有人批准？
5、执行：工具什么时候才真正被调用？
6、错误处理：失败后图会不会崩？
7、重试/降级：失败后怎么收场？
8、审计：事后怎么查？
9、回复：怎么把最终状态解释给用户？
```

上面这条流水线算是提供一种工具调用治理的思想，说实话是比普通tool loop长的多，但至少说明agent在工具调用治理方面，我们能做，也需要做的事儿还是挺多的。

---

实验细节

```text
GitHub 仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/langgraph/foundations/23 | LangGraph 工具调用治理：让工具执行可控、可恢复、可审计.md

实验代码：
labs/langgraph/foundations/experiments/23_tool_governance_console/
```
