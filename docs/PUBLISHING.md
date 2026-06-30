# 公众号与 GitHub 联动规范

AI Forge 的目标不是把公众号文章写成超长技术手册，而是让公众号和 GitHub 分工协作。

## 发布原则

- 公众号讲清楚一个问题，不承担完整实验归档。
- GitHub 保存完整代码、Notebook、截图、实验数据和运行说明。
- 每篇文章只服务一条主线，避免把多个主题塞进同一篇。
- 公众号文章中只保留能帮助理解关键概念的代码块和截图。
- 读者需要深入复现时，引导到对应 GitHub 目录。

## 推荐文章结构

```text
标题：用一个具体问题命名，而不是用大而全的概念命名

1. 这个问题为什么重要
2. 先用一个最小例子建立直觉
3. 工程实现里真正要注意什么
4. 我在实验中的判断和取舍
5. 完整代码、Notebook、截图和运行说明放到 GitHub
```

后续新文章可以直接从 [ARTICLE_TEMPLATE.md](ARTICLE_TEMPLATE.md) 开始写，避免每次重新设计公众号和 GitHub 的分工。

## GitHub 配套目录建议

长期建议把成熟文章整理成下面这种结构：

```text
labs/
└── mcp/
    └── 01-what-is-mcp/
        ├── README.md
        ├── article.md
        ├── notebook.ipynb
        ├── assets/
        └── data/
```

旧 `notebooks/` 内容已经迁移到新结构中。迁移过程中不修改任何已完成文章正文和 Notebook 内容。

## 公众号结尾模板

```text
完整代码、Notebook、截图和运行说明已放在 GitHub：
https://github.com/yauld/ai-forge

如果你想系统学习 AI Engineering，我会把 LangChain、LangGraph、RAG、MCP、Agent 工程化等实践持续整理到这个仓库。
```

如果某篇文章已经有明确目录，优先链接到具体目录，而不是仓库首页：

```text
完整实验入口：
https://github.com/yauld/ai-forge/tree/main/labs/mcp
```

## GitHub 页面应包含什么

每个成熟实验页建议包含：

- 这节解决什么问题
- 适合谁阅读
- 文件清单
- 最小运行命令
- 关键代码入口
- 公众号文章链接
- 延伸阅读或下一篇

## 标题建议

公众号标题偏向“问题”和“读者收益”：

- MCP 是什么：先把它放回 AI 应用架构里理解
- LangGraph checkpoint：状态快照到底是什么
- Agent 为什么需要 Middleware：从失控风险讲起

GitHub 标题偏向“主题”和“可复现资产”：

- MCP 架构与订单分析示例
- LangGraph checkpoint 与状态恢复实验
- LangChain Middleware 工程化控制实验

## 内容拆分标准

适合放公众号：

- 背景、问题、概念解释
- 核心流程图
- 少量关键代码
- 工程判断
- 读者应该带走的结论

适合放 GitHub：

- 完整 Notebook
- 大段代码
- 多张截图
- 示例数据库
- 可运行 Server
- 排错记录和环境说明

## 维护节奏

- 先把现有文章和 Notebook 纳入内容地图。
- 再为高价值主题补 README。
- 最后逐步把成熟内容整理成 `topics/<domain>/<lesson>`。

## 新旧内容处理原则

- 已经发布到公众号的旧文章，优先保持正文稳定，只做目录、README 和内容地图层面的整理。
- 新文章从选题阶段就确定 GitHub 实验目录，不等发布后再补入口。
- 新文章的 GitHub 页面先完成，再发布公众号文章；公众号结尾链接到具体实验页。
- 旧内容如果要重写，按“新版文章”处理，而不是在原文末尾机械追加入口。
