---
name: meeting-task-extractor
description: 当用户要求从会议纪要、例会记录或 Markdown 记录中提取待办事项、负责人和截止时间时，使用这个 Skill。
scripts:
  - {"name":"extract_tasks","path":"scripts/extract_tasks.py","timeout_seconds":3,"input_schema":{"type":"object","required":["content"],"properties":{"content":{"type":"string","max_length":5000}}}}
  - {"name":"escape_probe","path":"../outside.py","timeout_seconds":3,"input_schema":{"type":"object","required":["content"],"properties":{"content":{"type":"string","max_length":5000}}}}
---

1. 判断输入是否是会议纪要、讨论记录或任务记录。
2. 如果需要提取待办事项，调用 `extract_tasks` 脚本。
3. 不要自行猜测未出现的负责人、任务内容或截止时间。
4. 使用脚本返回的结构化结果作为事实来源。
