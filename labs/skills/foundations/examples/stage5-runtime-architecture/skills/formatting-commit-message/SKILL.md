---
name: formatting-commit-message
description: 当用户要求根据变更摘要、diff 摘要、暂存文件列表或粗糙提交说明来编写、改写、清理或校验 Git commit message 时，使用这个 Skill。输出应包含清晰的提交类型，必要时包含 scope，只有在能补充有效上下文时才写正文。
tools:
  - text_stats
---

# Commit Message 整理

使用这个 Skill，把粗糙的变更说明整理成可读的 Git commit message。

## 执行步骤

1. 识别变更类型，例如 `feat`、`fix`、`docs`、`test` 或 `refactor`。
2. 调用 `text_stats` 观察输入摘要规模，判断是否需要拆分提交。
3. 生成一行清晰 subject，必要时补充 body。
4. 不把没有证据的动机、影响范围或 issue 编号写进提交信息。

