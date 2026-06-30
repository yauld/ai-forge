# 01 | 我给 Codex 写了一个写作 Skill：把反复改稿变成固定工作流

我几乎每天都要写微信公众号文章。

Codex 能写，速度也快，但过去经常出现一种尴尬：

```text
生成初稿
 -> 发现太啰嗦
 -> 修改
 -> 发现知识顺序不对
 -> 再修改
 -> 发现案例提前讲了后面的内容
 -> 继续修改
```

模型并不笨，问题出在另一边：写作要求虽然说过很多次，却没有变成一套稳定、可执行、可检查的工作流。

所以这次我没有继续补提示词，而是给 Codex 设计了一个专门编写技术公众号文章的 Skill：

```text
write-tech-wechat
```

它的目标不是让 Codex“文采突然觉醒”，而是让它在动笔前先完成必要的判断，写完后再主动检查，尽量把多轮返工压缩到一次交付。

## 一、Skill 到底是什么

Skill 可以理解为交给 Codex 的一套可复用工作手册。

它通常由一个必需的 `SKILL.md` 和若干可选资源组成：

```text
write-tech-wechat/
├── SKILL.md                       # 定义何时使用，以及完整工作流程
├── agents/
│   └── openai.yaml                # Codex 界面中的名称、简介和默认提示
├── references/
│   ├── article-contract.md        # 写作前的文章契约
│   ├── writing-style.md           # 语言和排版要求
│   ├── approved-patterns.md       # 已认可的表达模式
│   └── review-checklist.md        # 发布前检查表
└── scripts/
    └── check_article.py           # 自动检查文章
```

Skill 不会重新训练模型，也不会修改模型参数。

它做的是：

```text
任务出现
 -> Codex 识别应该使用哪个 Skill
 -> 读取对应的 SKILL.md
 -> 按需读取 references 或运行 scripts
 -> 按固定流程完成任务
```

这套机制叫作**渐进式披露**。

Codex 平时只需要知道 Skill 的名称和描述。真正使用时，才加载完整说明；更详细的参考资料也只在需要时读取。这样既保留了复杂工作流，又不会每次对话都把一大本写作规范塞进上下文。

## 二、Skill 是如何被调用的

Codex 可以通过两种方式启用 Skill。

### 1. 显式调用

在提示词中直接指定：

```text
使用 $write-tech-wechat 编写这篇技术文章
```

这种方式最稳定，适合重要文章或者第一次使用某个 Skill。

### 2. 隐式调用

如果任务与 Skill 的 `description` 高度匹配，Codex 也可以自动选择它。

当前 Skill 的开头是：

```yaml
---
name: write-tech-wechat
description: Write, revise, or review Chinese technical articles for
  WeChat Official Accounts using a contract-first workflow...
---
```

其中：

- `name` 是调用名称；
- `description` 不只是介绍，更是触发条件；
- 正文才是 Skill 被选中后需要执行的具体流程。

所以描述不能只写成“帮助写文章”。范围太宽，Codex 不知道什么时候该用，也不知道什么时候不该用。

## 三、为什么只有 Skill 还不够

这次最终采用的并不是一个孤零零的 Skill，而是四层结构：

```text
AGENTS.md
 + 写作 Skill
 + 参考样本
 + 自动检查脚本
```

它们解决的问题并不相同。

| 组成 | 解决什么问题 |
| --- | --- |
| `AGENTS.md` | 当前仓库或目录必须长期遵守什么规则 |
| `SKILL.md` | 完成一篇文章时应该按什么步骤执行 |
| `references/` | 什么样的表达、结构和审查标准才算合格 |
| `check_article.py` | 哪些错误可以由程序稳定检查 |

如果只使用一段很长的提示词，所有内容都会混在一起。模型既要记住风格，又要判断流程，还要检查图片路径，难免顾此失彼。

分层之后，每种信息待在最合适的位置。

`MEMORY.md` 可以保存长期偏好，但不适合作为项目规则的唯一强制入口。

当前官方文档也建议：必须稳定执行的项目规则放进 `AGENTS.md`；Memory 更适合帮助 Codex 回忆长期偏好，不能代替项目必须遵守的规则。

## 四、`AGENTS.md` 如何控制作用范围

`AGENTS.md` 是 Codex 的项目级长期规则。

项目可以使用两层规则：

```text
项目根目录/
├── AGENTS.md
└── labs/
    └── langgraph/
        └── AGENTS.md
```

根目录文件负责通用要求，例如：

- 修改前先读取相关文件；
- 技术文章不能包含无关的私人环境信息；
- 优先使用真实项目代码；
- 完成后运行文章检查器。

`labs/langgraph/AGENTS.md` 只约束 LangGraph 系列，例如：

- 文章面向初学者；
- 最多八个大章节；
- 01、02、03、04、05 分别讲什么；
- 03 不能提前讲工具循环；
- 图片必须适合手机阅读；
- 版本必须从项目锁文件确认。

Codex 会从项目根目录向当前工作目录逐层读取规则，越靠近当前文件的规则越具体。

因此，LangGraph 的特殊要求不会误伤 LangChain、RAG 或其他系列。

## 五、Skill 如何减少写完再返工

这个 Skill 最关键的设计，不是文风，而是要求 Codex 在编辑前先建立一份**文章契约**：

```text
Article question:
Reader already knows:
Allowed concepts:
Reserved concepts:
Practical outcome:
Format: Markdown / Notebook
Code needed: yes / no, because
Images needed: yes / no, because
One-sentence conclusion:
```

它不会默认展示给作者，而是作为动笔前的内部检查。

例如编写 LangGraph Studio 数据流文章时，契约会先确定：

```text
本文问题：
云端 Studio 如何调用本地 Graph？

读者已经知道：
CLI 会启动本地 Agent Server。

允许出现：
浏览器、baseUrl、Agent Server、Tracing。

暂不展开：
State、Node、Edge、ToolNode、工具循环。
```

这一步解决了过去最常见的问题：文章写到一半，作者觉得某个知识“顺便讲一下也不错”，结果主线越走越远。

Skill 随后要求执行两个静默审查：

1. **初学者审查**：连续阅读上一篇和当前篇，寻找知识跳跃；
2. **编辑审查**：删除重复结论、旁支内容和没有必要的术语。

先确定边界，再写；写完主动删。比“先写一大篇，再等人指出问题”省事得多。

## 六、为什么还要写自动检查脚本

有些问题适合模型判断，例如文章是否自然、案例是否合适。

另一些问题没有必要每次都让模型重新思考：

- 大章节是否超过八个；
- 图片和本地链接是否存在；
- Markdown 代码块是否闭合；
- 是否出现重复段落；
- Notebook 是否能正确解析；
- 某一篇是否提前出现后续文章的关键术语。

所以 Skill 中加入了：

```text
scripts/check_article.py
```

使用方式：

```bash
python scripts/check_article.py "labs/skills/文章.md"
```

核心检查逻辑类似：

```python
# 编号大章节超过 8 个时直接报错
if numbered_count > 8:
    errors.append("numbered H2 sections exceed the maximum")

# Markdown 中引用的本地图片必须真实存在
for image in markdown_images:
    if not image.exists():
        errors.append(f"missing local image: {image}")

# 对特定系列检查是否提前引入后续概念
if article_number == "03" and "ToolNode" in text:
    warnings.append("article 03 may introduce later concepts early")
```

脚本负责确定性检查，Codex 负责需要理解语义的判断。

这比要求模型“请仔细检查所有问题”更可靠，也更节省 Token。

## 七、如何安装和使用这套 Skill

本次 Skill 的可维护源码保存在项目中：

```text
skills/write-tech-wechat/
```

这个目录便于版本管理和继续修改，但它本身只是源码目录。为了让其他项目也能调用，我们又复制了一份到当前 Codex 用户环境：

```text
~/.codex/skills/write-tech-wechat/
```

这是本次 Codex 环境实际发现并加载 Skill 的位置。

按照当前官方文档，用户级 Skill 推荐放在：

```text
~/.agents/skills/
```

仓库级 Skill 推荐放在：

```text
.agents/skills/
```

也就是说，本次环境的实际目录与当前官方推荐目录存在差异。不同版本或安装方式可能保留兼容路径，因此不要只凭一篇文章猜目录；创建新 Skill 时，应优先查看当前官方文档，并确认它是否已经出现在 Codex 的 Skill 列表中。

以后写文章时，可以直接输入：

```text
使用 $write-tech-wechat，
按照学习路线编写下一篇文章。
```

Codex 接下来会：

```text
读取 AGENTS.md
 -> 读取学习路线和前后文章
 -> 查看真实代码与版本
 -> 建立文章契约
 -> 编写正文
 -> 模拟初学者审查
 -> 删除重复和越界内容
 -> 运行自动检查脚本
 -> 交付文章
```

如果修改 Skill 后没有立即出现在列表中，可以重新启动 Codex 或新建线程再试。

## 小结

Skill 的价值，不是保存一段更长的提示词，而是把反复发生的工作变成可复用流程。

这次写作系统的分工可以归纳为：

```text
AGENTS.md 规定长期边界
SKILL.md 规定执行步骤
references 提供写作标准
scripts 执行机械检查
```

过去每一篇文章都要重新解释“怎么写”，现在只需说明“写什么”。

至于它能不能彻底消灭改稿，当然不能。写作毕竟不是编译代码，不会因为通过检查器就自动成为十万加。

但它至少能先消灭那些本来就不该反复出现的问题。

## 参考资料

- [Codex Agent Skills](https://developers.openai.com/codex/skills)
- [Codex 自定义：AGENTS.md、Skills 与 MCP](https://developers.openai.com/codex/concepts/customization)
- [Codex 中的 AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [Agent Skills 开放规范](https://agentskills.io/specification)
