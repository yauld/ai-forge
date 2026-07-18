# 07 | LangGraph Command goto也能干普通条件边的活儿

通常，Langtraph的一个节点做完判断以后，既要把判断结果写进状态，又要决定下一步去哪。

比如前台接待员检查一张报名表的例子，报名表有三个字段：

- 姓名
- 手机号
- 报名课程

如果信息完整，就进入办理流程，如果缺手机号，就进入补充资料流程。

实现倒是不难，但需要知道的是，其实LangGraph中有两种写法：

```text
普通条件边的写法：节点只更新状态，条件边负责跳转。
Command goto的写法：节点用Command同时更新状态和决定跳转。
```

两种写法对比一下看看。

## 1. 先看普通条件边

普通条件边的思路是：

```text
节点负责产出状态
router负责读取状态
条件边根据router结果决定下一步
```

放到报名表场景里，类似这样：

```text
validate_request检查报名表
  ↓
写入valid / missing_fields / validation_note
  ↓
route_after_validation读取valid
  ↓
valid=True  -> process
valid=False -> ask_for_more
```

代码实现逻辑大概长这样：

```python
def validate_request(state):
    missing_fields = []

    if not state.get("name"):
        missing_fields.append("姓名")

    if not state.get("phone"):
        missing_fields.append("手机号")

    if not state.get("workshop"):
        missing_fields.append("报名课程")

    if missing_fields:
        return {
            "valid": False,
            "missing_fields": missing_fields,
            "validation_note": "报名表缺少：手机号。",
        }

    return {
        "valid": True,
        "missing_fields": [],
        "validation_note": "报名表信息完整，可以进入办理。",
    }
```

这个节点检查报名表，把结果写进状态，然后，下一步去哪交给另一个路由函数：

```python
def route_after_validation(state):
    if state.get("valid") is True:
        return "process"

    return "ask_for_more"
```

这就是普通的条件边，用的比较多的就这样种，它省心的地方是节点不关心图怎么连，router专门负责路由。

但这个例子里，对于validate_request的逻辑明明已经知道：

```text
缺手机号 -> 去ask_for_more
信息完整 -> 去process
```

它先把valid写进state，再让另一个router把valid翻译成下一步节点，逻辑上多绕了一下，有没有感觉到？

同样的案例，看一下用command goto是怎么搞的。

## 2. 再看Command goto

Command让节点在返回时同时会做两件事，一个是update，一个是goto

```text
update：要写进State的字段
goto：下一步要去的节点
```

相同的示例，代码可以这样写：

```python
from langgraph.types import Command


def validate_request(state):
    missing_fields = []

    if not state.get("name"):
        missing_fields.append("姓名")

    if not state.get("phone"):
        missing_fields.append("手机号")

    if not state.get("workshop"):
        missing_fields.append("报名课程")

    if missing_fields:
        return Command(
            update={
                "valid": False,
                "missing_fields": missing_fields,
                "validation_note": "报名表缺少：手机号。",
            },
            goto="ask_for_more",
        )

    return Command(
        update={
            "valid": True,
            "missing_fields": [],
            "validation_note": "报名表信息完整，可以进入办理。",
        },
        goto="process",
    )
```

代码的意思已经非常直接了

```text
如果缺字段：
  把valid=False、missing_fields、validation_note写进State
  下一步去ask_for_more

如果信息完整：
  把valid=True、missing_fields=[]、validation_note写进State
  下一步去process
```

看到update，就知道这个节点写了什么状态。

看到goto，就知道这个节点下一步要去哪。

## 3. 别把Command(resume=...)混进来

还有一个容易混淆的地方，就是，LangGraph里也会看到这种写法：

```python
Command(resume=...)
```

它和本文说的Command(update=..., goto=...)不是一回事

本文讲的是节点返回值：

```python
return Command(
    update={...},
    goto="process",
)
```

意思是当前节点运行结束后，更新状态，并跳到指定节点。

而Command(resume=...)这个玩意是用于人工中断后的恢复执行。

这两个语法长得确实是有点像，而且langgraph里这种长得像的写法其实还挺多的。。。

## 6. 普通条件边vs command goto，咋选

个人认为

如果一个节点做出的判断，天然决定了它下一步去哪，就用Command。

比如：

```text
校验通过 -> process
校验失败 -> ask_for_more
审批通过 -> execute
审批拒绝 -> stop
风险高 -> human_review
风险低 -> auto_handle
```

如果一个节点只是产生一个结果，而“这个结果如何路由”属于外部流程编排，就用条件边。

比如：

```text
分类节点只输出category
图结构根据category决定进入哪个业务流程
```
---

GitHub 仓库：https://github.com/yauld/ai-forge

实验代码：
labs/langgraph/foundations/experiments/21_command_registration_desk/
