---
name: formatting-commit-message
description: 当用户要求根据变更摘要、diff 摘要、暂存文件列表或粗糙提交说明来编写、改写、清理或校验 Git commit message 时，使用这个 Skill。输出应包含清晰的提交类型，必要时包含 scope，只有在能补充有效上下文时才写正文。
---

# Commit Message 格式化

使用这个 Skill，把粗糙的变更说明整理成可读的 Git commit message。

## 输入

可以接收以下任意组合：

- 粗糙提交说明
- 简短变更摘要
- 变更文件列表
- diff 摘要
- 用户提供的项目提交规范

## 工作流

1. 识别这次变更的主要意图。
2. 选择一个提交类型：
   - `feat`：用户可感知的新能力
   - `fix`：缺陷修复
   - `docs`：文档修改
   - `test`：测试相关
   - `refactor`：不改变行为的代码调整
   - `chore`：维护性工作
3. 只有当 scope 能帮助理解时才添加，例如 `docs(skills)` 或 `fix(auth)`。
4. subject 使用祈使语气，表达具体变化。
5. 只有当原因、迁移说明或取舍无法放进 subject 时，才添加正文。
6. 移除 `update stuff`、`misc`、`fix issues` 这类含糊表达。
7. 检查提交信息描述的是改了什么，而不是工作有多辛苦。

## 输出结构

默认使用：

```text
type(scope): concise subject

Optional body explaining why the change was needed.
```

如果 scope 没有帮助，省略它：

```text
type: concise subject
```

## 约束

- 除非文件名能帮助理解变化，否则不要在提交信息里罗列文件。
- 不要编造变更摘要里没有体现的行为。
- 默认只给一个提交信息；只有多个意图都合理时，才给备选。
- 如果输入混合了多个无关改动，说明这次提交可能应该拆分。
