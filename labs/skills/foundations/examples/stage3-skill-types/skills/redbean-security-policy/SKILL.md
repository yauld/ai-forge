---
name: redbean-security-policy
description: 当任务需要理解 RedBean 的安全边界、Telegram 访问控制、FastAPI 暴露限制、文件工具、Shell 工具或长期记忆规则时，使用这个 Skill。
---

# RedBean 安全规则摘要

使用这份 Skill 判断 RedBean 的功能变更是否符合当前安全边界。它只提供规则和判断标准，不负责执行完整变更审查流程。

## 当前可信边界

- RedBean 是本地优先的个人 Agent。
- 可信边界包括当前本机、本机 `.env` 文件、`TELEGRAM_ALLOWED_USER_IDS` 中列出的 Telegram 数字用户 id。
- 模型输出只能当建议，不能当权限来源。

## 安全红线

- 不提交 `.env`。
- 不把 `TELEGRAM_BOT_TOKEN` 发到聊天、截图、日志、issue。
- 除非先实现 API 鉴权，否则保持 `REDBEAN_HOST=127.0.0.1`。
- Telegram bot 只响应白名单用户和私聊。
- 不添加无限制 shell 执行。
- 不添加无限制文件读写。
- 不允许模型自行决定任意本机路径。
- 除非有明确需求和保留策略，否则不长期保存 Telegram 消息原文。

## FastAPI 检查标准

- 无鉴权时，FastAPI 只能监听 `127.0.0.1`。
- 如果要让 FastAPI 被本机之外访问，至少先补 API token 鉴权、请求体大小限制、速率限制、带 secret 脱敏的访问日志，以及防火墙或反向代理访问限制。

## Telegram 检查标准

- `TELEGRAM_ALLOWED_USER_IDS` 只允许可信数字用户 id。
- Telegram bot 应忽略群聊、超级群和频道消息。
- BotFather 中应保持禁用加群。
- 不分享 bot token。

## 文件工具规则

- 新增文件工具前必须定义唯一 workspace 根目录。
- 对路径做解析和归一化。
- 拒绝 workspace 外路径。
- 拒绝符号链接逃逸。
- 增加读写大小限制。
- 记录文件操作日志，但不记录敏感内容。

## Shell 工具规则

- Shell 命令执行前必须显式确认。
- 执行前展示完整命令。
- 对低风险命令使用 allowlist。
- 默认禁止破坏性命令。
- 设置超时。
- 安全捕获输出。
- 不运行 `sudo`。

## 长期记忆规则

- 新增长期记忆前必须明确存什么。
- 明确保留多久。
- 提供查看和删除能力。
- 不存密钥。
