# 02 | 让 Agent 找到正确 Skill：最小 SKILL.md 的两个关键字段

写第一个 `SKILL.md` 时，最容易沿用普通 Prompt 的写法。

比如：

```text
你是一个擅长写周报的助手，请根据材料生成结构清晰的周报。
```

这句prompt最大的问题在于它只描述了这一次要做什么：扮演周报助手，根据材料生成周报。

但它没有告诉 Agent：这类能力叫什么，什么请求应该触发它，哪些输入算匹配，哪些边界不能越过。

Skill 要先被 Agent 找到。真实运行时里，系统通常不会一开始就把所有 Skill 正文都塞进上下文，而是先看少量 metadata，判断当前请求和哪一个 Skill 相关。最小 `SKILL.md` 里，最重要的是两个字段：

- `name`：稳定标识，让系统知道这份 Skill 叫什么；
- `description`：路由条件，让系统知道什么时候该用它。

例如：

```yaml
name: writing-weekly-report
description: 当用户要求把周度工作材料、会议记录、任务更新、指标快照、阻塞风险或零散进展整理成结构化周报时，使用这个 Skill。输出必须基于输入事实，标注不确定信息，不能编造进展、指标、负责人或日期。
```

正文是在命中以后才读的。如果 `name` 和 `description` 写不好，后面的步骤再完整，Agent 也未必会打开这份 Skill。

## 一、name：稳定指向这份 Skill

`name` 不需要解释全部能力，它只要稳定、简短、可读。像这样就够了：

```text
writing-weekly-report
formatting-commit-message
reviewing-roadmap
```

它们承担的是系统标识。日志、路由结果、配置引用、评测用例，都可能靠这个名字指向同一份 Skill。

所以 `name` 不要太泛，比如 `writing`；也不要太像一句标题。可以把它当函数名看：不承担全部解释，但能让人一眼知道大概指向什么。

## 二、description：不是简介，是触发条件

`description` 如果只写一句介绍：

```text
用于生成高质量周报。
```

这对路由帮助很小。“高质量”是什么？输入来自会议记录、任务更新，还是指标快照？如果用户只是问“怎么写周报更好”，要不要触发？

`description` 至少要说清三件事：

- 处理什么任务；
- 常见输入长什么样；
- 哪些边界不能越过。

周报 Skill 的描述里，故意写了“周度工作材料、会议记录、任务更新、指标快照、阻塞风险、零散进展”，用来覆盖用户真实表达。用户不一定会说“请使用周报 Skill”。他更可能说：

```text
根据这些会议记录和任务更新，整理一份本周运营周报。
```

描述里还写了“不能编造进展、指标、负责人或日期”。周报任务真正危险的地方，常常不是格式不漂亮，而是把没有提供的信息写得像真的一样。

## 三、正文是命中后的事

可以先把 `SKILL.md` 分成两层：

```text
metadata：让 Agent 判断要不要加载
body：让 Agent 知道加载后怎么做
```

`description` 不应该塞满执行步骤。它只负责让 Agent 判断“这份 Skill 是否相关”。正文再去写输入、处理步骤、输出结构、约束和示例。

比如 Commit Message 格式化 Skill，`description` 说明它适用于变更摘要、diff 摘要、暂存文件列表或粗糙提交说明；正文再规定提交信息格式、type 选择和 body 写法。职责清楚以后，发现阶段只判断“是不是这类任务”，执行阶段才处理“具体怎么做”。

## 四、一个最小检查

写最小 `SKILL.md` 时，可以先问三件事：

```text
1. name 是否稳定、简短、能唯一指向这份 Skill？
2. description 是否说清触发场景、输入形态和边界？
3. 正文是否说明执行步骤、输出结构和不能做什么？
```

Skill 不是加长版的一次性 Prompt。它是一份能被发现、被加载、被执行的方法包。第一步先让 Agent 找得到、选得中，也能在不相关时拒绝加载。

---
更多实验细节见：
```text
GitHub 仓库：
https://github.com/yauld/ai-forge

完整实验文章：
labs/skills/foundations/02 | 最小 SKILL.md：一个 Skill 如何被发现和使用.md

实验代码：
labs/skills/foundations/examples/stage2-minimal-skills/
```
