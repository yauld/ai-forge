---
name: reviewing-redbean-change
description: 当用户要求审查 RedBean 的新能力、配置变更、入口暴露、文件工具、Shell 工具或长期记忆设计是否安全时，使用这个 Skill。
---

# RedBean 新能力安全审查流程

使用这份 Skill 审查 RedBean 的功能变更。执行判断时，需要参考 `redbean-security-policy` 中的安全标准。

## 输入

- 变更需求或设计说明
- 涉及的入口，例如 Telegram、FastAPI、本地工具、长期记忆
- 相关配置变化
- 预期用户和访问范围

## 引用资料

- `../redbean-security-policy/SKILL.md`

## 工作流

1. 识别变更涉及的入口和能力类型。
   - 判断是否涉及 Telegram、FastAPI、文件工具、Shell 工具、长期记忆或密钥配置。

2. 检查是否触碰安全红线。
   - 参考 `redbean-security-policy` 的「安全红线」。
   - 命中红线时，优先输出“阻塞”，不要继续假设可以直接上线。

3. 检查 FastAPI 暴露范围。
   - 参考 `redbean-security-policy` 的「FastAPI 检查标准」。
   - 如果要监听 `0.0.0.0` 或被本机之外访问，确认是否已有鉴权、限流、请求大小限制和日志脱敏。

4. 检查 Telegram 入口。
   - 参考 `redbean-security-policy` 的「Telegram 检查标准」。
   - 确认是否仍然只响应白名单用户和私聊。

5. 检查文件读写能力。
   - 参考 `redbean-security-policy` 的「文件工具规则」。
   - 确认是否定义 workspace 根目录、拒绝路径逃逸和符号链接逃逸，并限制读写大小。

6. 检查 Shell 执行能力。
   - 参考 `redbean-security-policy` 的「Shell 工具规则」。
   - 确认是否显式确认、展示完整命令、使用 allowlist、设置超时、禁止 `sudo`。

7. 检查长期记忆设计。
   - 参考 `redbean-security-policy` 的「长期记忆规则」。
   - 确认是否明确存储内容、保留时间、查看删除能力，并禁止保存密钥。

8. 输出审查结论。
   - `允许`：没有触碰红线，关键安全条件已经满足。
   - `阻塞`：触碰安全红线或缺少关键保护。
   - `需要补充设计`：方向可行，但缺少必要安全机制。
   - `需要人工确认`：规则无法直接判断，或涉及权衡。

## 输出结构

必须使用下面的结构输出，不要改成自由格式：

```text
审查结论：
涉及能力：
阻塞项：
需要补充设计：
需要人工确认：
对应安全标准：
```

## 约束

- 不要把模型输出当作权限来源。
- 不要默认允许暴露本地服务、任意文件读写或任意 shell 执行。
- 不要编造 redbean-security-policy 中不存在的保护措施。
- 只要变更命中 redbean-security-policy 的安全红线，审查结论必须包含“阻塞”，不能给出“可选”或“推荐但不强制”的结论。
- 对应安全标准必须列出引用的 redbean-security-policy 章节，例如「安全红线」「FastAPI 检查标准」「文件工具规则」「Shell 工具规则」。
- 如果信息不足，输出“需要补充设计”或“需要人工确认”。
