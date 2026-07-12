# 07 | 脚本型 Skill：如何安全执行 scripts 与校验参数

阶段 5 已经搭出了一个教学用 Skills runtime：

```text
Registry -> Router -> Loader -> Executor -> Trace
```

它证明了一件事：Skill 不只是一个孤立的 `SKILL.md` 文件。真正运行起来时，需要有人负责扫描 Skill，有人负责路由，有人负责加载正文，有人负责执行动作，还有人负责记录过程。

但阶段 5 的 Executor 仍然很薄。它只是根据 Skill 声明的 `tools`，硬编码调用了一个 `text_stats` 函数：

```python
if tool_name == "text_stats":
    count_text_stats(content)
```

这足够说明“Executor 这个插槽存在”，却还没有回答另一个更接近真实工程的问题：

> 如果一个 Skill 想声明自己的本地脚本，runtime 应该如何安全执行？

本实验就围绕这个问题展开。我们会把阶段 5 的工具调用，升级成 Skill 私有 `scripts/` 的受控执行：Skill 可以声明脚本，但不能直接执行脚本；真正执行脚本的是 runtime，而且必须经过白名单、路径边界、参数校验和超时控制。

## 一、实验目标与配套文件

本实验要验证的不是“脚本能不能跑”，而是脚本执行边界能不能说清楚。

具体目标有四个：

1. 让 Skill 在 `SKILL.md` 中声明可调用脚本。
2. 让 Executor 不再硬编码每个具体脚本函数。
3. 新增通用 `ScriptRunner`，集中处理脚本白名单、路径边界、参数 schema 和超时。
4. 用 trace 记录合法调用和拒绝调用的证据。

配套代码位于：

```text
labs/skills/foundations/examples/stage7-script-skill/
```

目录结构如下：

```text
stage7-script-skill/
├── run_runtime_demo.py
├── runtime/
│   ├── app.py
│   ├── executor.py
│   ├── loader.py
│   ├── registry.py
│   ├── router.py
│   ├── script_runner.py
│   ├── trace.py
│   └── types.py
└── skills/
    ├── meeting-task-extractor/
    │   ├── SKILL.md
    │   └── scripts/
    │       └── extract_tasks.py
    └── writing-weekly-report/
        └── SKILL.md
```

这次的主角是 `meeting-task-extractor`：一个从会议纪要中提取待办事项的脚本型 Skill。

它解决的任务很小：

```markdown
# 本周例会

- 张三负责整理竞品清单，下周三前完成
- 李四需要更新项目排期
- 已讨论预算问题，暂不处理
```

期望得到结构化结果：

```json
{
  "tasks": [
    {
      "owner": "张三",
      "task": "整理竞品清单",
      "deadline": "下周三"
    },
    {
      "owner": "李四",
      "task": "更新项目排期",
      "deadline": null
    }
  ],
  "task_count": 2
}
```

案例故意选得很小。因为阶段 7 的重点不是写一个强大的会议纪要解析器，而是观察 runtime 如何安全地调用一个确定性脚本。

## 二、运行前提

本仓库使用 `uv` 管理 Python 环境。读者可以在仓库根目录运行下面的命令：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario legal
```

阶段 7 的默认路由是“规则优先”。默认任务里包含“会议纪要”“待办”“负责人”“截止时间”等关键词，规则能够直接命中 `meeting-task-extractor`，所以合法场景不依赖 Ollama。

如果想观察规则无法明确命中时的模型兜底，可以额外打开：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py \
  --model-fallback \
  --model qwen3-coder:30b
```

但这不是本实验的必要路径。阶段 7 关注的是脚本执行安全，不重新展开模型路由能力。

## 三、一次请求会经历什么

默认入口在 `run_runtime_demo.py`：

```python
DEFAULT_TASK = "请从这份会议纪要中提取待办事项、负责人和截止时间。"
DEFAULT_CONTENT = """# 本周例会

- 张三负责整理竞品清单，下周三前完成
- 李四需要更新项目排期
- 已讨论预算问题，暂不处理
"""
```

入口脚本创建 runtime：

```python
runtime = SkillRuntime(
    skills_root=example_root / "skills",
    model_name=args.model,
    use_model_fallback=args.model_fallback,
)
```

然后把任务和内容交给 runtime：

```python
trace = runtime.run(
    task=args.task,
    content=args.content,
    script_name=script_name,
    script_arguments=script_arguments,
)
```

这次请求的完整链路是：

```text
User
  -> Registry.scan()
  -> Router.route()
  -> Loader.load()
  -> Executor.execute()
  -> ScriptRunner.run()
  -> skills/meeting-task-extractor/scripts/extract_tasks.py
  -> ScriptRunner 解析结果
  -> Executor 汇总结果
  -> Trace 输出证据
```

阶段 7 和阶段 5 的主干没有变。真正新增的是：

```text
Executor -> ScriptRunner -> Skill 私有 scripts/
```

这条新增链路让 Executor 从“硬编码调用某个函数”，变成“根据 Skill 声明发起一个受控脚本调用”。

## 四、Skill 如何声明 scripts

`meeting-task-extractor/SKILL.md` 的 frontmatter 是：

```yaml
---
name: meeting-task-extractor
description: 当用户要求从会议纪要、例会记录或 Markdown 记录中提取待办事项、负责人和截止时间时，使用这个 Skill。
scripts:
  - {"name":"extract_tasks","path":"scripts/extract_tasks.py","timeout_seconds":3,"input_schema":{"type":"object","required":["content"],"properties":{"content":{"type":"string","max_length":5000}}}}
  - {"name":"escape_probe","path":"../outside.py","timeout_seconds":3,"input_schema":{"type":"object","required":["content"],"properties":{"content":{"type":"string","max_length":5000}}}}
---
```

这里有两个脚本声明。

第一个是合法脚本：

```text
extract_tasks -> scripts/extract_tasks.py
```

第二个是故意设计的路径越界样本：

```text
escape_probe -> ../outside.py
```

它不是为了真的执行，而是为了验证 `ScriptRunner` 是否会拒绝逃出当前 Skill `scripts/` 目录的脚本路径。

`SKILL.md` 正文只描述任务方法：

```markdown
1. 判断输入是否是会议纪要、讨论记录或任务记录。
2. 如果需要提取待办事项，调用 `extract_tasks` 脚本。
3. 不要自行猜测未出现的负责人、任务内容或截止时间。
4. 使用脚本返回的结构化结果作为事实来源。
```

这里要注意一个边界：Skill 只是声明脚本和使用规则，脚本能不能被执行，不由 Skill 自己说了算。

## 五、Registry：只解析声明，不执行脚本

Registry 仍然负责扫描：

```text
skills/*/SKILL.md
```

它解析 `name`、`description` 和 `scripts`，然后生成结构化 metadata。

阶段 7 的数据结构里多了一个 `ScriptDeclaration`：

```python
@dataclass(frozen=True)
class ScriptDeclaration:
    name: str
    path: str
    input_schema: dict[str, Any]
    timeout_seconds: float = 3.0
```

对应的 `SkillMetadata` 不再保存 `tools`，而是保存 `scripts`：

```python
@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    path: Path
    skill_dir: Path
    scripts: tuple[ScriptDeclaration, ...] = ()
```

这一步只建立索引。它不会执行脚本，也不会把脚本源码读入模型上下文。

为什么不在 Registry 做完整安全检查？

因为 Registry 的职责是“发现和索引”。脚本能否执行，取决于一次具体调用：调用哪个脚本、传什么参数、是否超时、stdout 是否能解析。这些都更适合放在执行阶段处理。

## 六、Router：仍然只负责选择 Skill

阶段 7 的 Router 使用规则优先：

```python
task_keywords = ("会议纪要", "例会", "待办", "负责人", "截止时间", "任务提取")
if "meeting-task-extractor" in known_names and any(
    keyword in normalized for keyword in task_keywords
):
    return RouteResult(
        skill_name="meeting-task-extractor",
        reason="规则命中会议纪要/待办提取相关关键词。",
        raw_response='{"skill": "meeting-task-extractor", "source": "rules"}',
    )
```

规则没有明确命中时，才可以通过 `--model-fallback` 交给本地模型判别。

这里的重点是：Router 仍然只回答“选哪个 Skill”，不回答“执行哪个脚本路径”。即使用户在 prompt 里写：

```text
请调用 ../outside.py
```

Router 也不应该把这个字符串直接变成脚本路径。脚本执行必须经过 Skill 声明和 `ScriptRunner` 检查。

## 七、Executor 与 ScriptRunner 如何分工

阶段 5 的 Executor 是硬编码 demo：

```python
if tool_name == "text_stats":
    count_text_stats(content)
```

这意味着每新增一个工具，就要改一次 Executor。

阶段 7 把职责拆开：

```text
Executor：决定这次调用哪个脚本、组装参数、汇总结果。
ScriptRunner：检查脚本声明、路径边界、参数 schema、超时和输出格式。
```

在 `executor.py` 中，默认脚本选择很简单：

```python
def _default_script_name(loaded_skill: LoadedSkill) -> str | None:
    if not loaded_skill.metadata.scripts:
        return None
    return loaded_skill.metadata.scripts[0].name
```

如果没有额外指定 `script_name`，Executor 就调用当前 Skill 声明的第一个脚本，也就是 `extract_tasks`。

然后 Executor 把请求交给 `ScriptRunner`：

```python
script_call = self.script_runner.run(
    skill_dir=loaded_skill.metadata.skill_dir,
    declarations=loaded_skill.metadata.scripts,
    script_name=selected_script,
    arguments=arguments,
)
```

到这里，Executor 仍然不知道 `extract_tasks.py` 的内部实现。它只是发起一个脚本调用请求。

真正的门禁在 `script_runner.py`。

### 1. 白名单检查

`ScriptRunner` 先检查脚本是否在当前 Skill 的声明里：

```python
declaration = _find_declaration(declarations, script_name)
if declaration is None:
    return ScriptCallResult(
        name=script_name,
        path="",
        status="rejected",
        error="script is not declared by selected skill",
    )
```

这能挡住“调用一个 Skill 没声明过的脚本”。

### 2. 路径边界检查

脚本路径必须是相对路径，并且最终解析后必须留在当前 Skill 的 `scripts/` 目录里：

```python
scripts_dir = (skill_dir / "scripts").resolve()
script_path = (skill_dir / raw_path).resolve()

if scripts_dir not in script_path.parents:
    return script_path, "script path must stay inside selected skill scripts directory"
```

这能挡住 `../outside.py` 之类的路径逃逸。

### 3. 参数 schema 检查

本实验实现了一个很小的 schema 校验器，只覆盖当前实验需要的字段：

```python
required = schema.get("required", [])
for key in required:
    if key not in arguments:
        return f"missing required argument: {key}"
```

对 `content` 字段，它会检查类型和最大长度：

```python
if expected_type == "string" and not isinstance(value, str):
    return f"argument {key} must be a string"

if isinstance(max_length, int) and isinstance(value, str) and len(value) > max_length:
    return f"argument {key} exceeds max_length {max_length}"
```

注意：非法参数不是用户的整段 prompt，而是 runtime 准备传给脚本的结构化参数。例如：

```json
{"content": 123}
```

这会被拒绝，因为 `content` 必须是字符串。

### 4. 受控 subprocess 执行

前面三道检查都通过后，`ScriptRunner` 才执行脚本：

```python
completed = subprocess.run(
    [sys.executable, str(script_path)],
    input=json.dumps(arguments, ensure_ascii=False),
    text=True,
    capture_output=True,
    timeout=declaration.timeout_seconds,
    cwd=skill_dir,
    check=False,
)
```

这里有几个教学重点：

- 参数通过 stdin 传入 JSON，不拼 shell 命令。
- `timeout` 来自脚本声明。
- `cwd` 固定在当前 Skill 目录。
- 捕获 stdout、stderr 和 exit code。
- 脚本输出必须是 JSON object。

这仍然不是生产级沙箱。它没有做系统调用隔离、网络隔离或资源配额控制。但对于阶段 7 的教学目标来说，它足以说明：脚本执行不能由模型随口拼命令，必须由 runtime 控制。

## 八、场景一：合法调用

先运行合法基线：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario legal
```

关键输出如下：

```json
{
  "registry_skills": [
    "meeting-task-extractor",
    "writing-weekly-report"
  ],
  "selected_skill": "meeting-task-extractor",
  "route_reason": "规则命中会议纪要/待办提取相关关键词。",
  "script_calls": [
    {
      "name": "extract_tasks",
      "path": "scripts/extract_tasks.py",
      "status": "completed",
      "exit_code": 0,
      "result": {
        "tasks": [
          {
            "owner": "张三",
            "task": "整理竞品清单",
            "deadline": "下周三"
          },
          {
            "owner": "李四",
            "task": "更新项目排期",
            "deadline": null
          }
        ],
        "task_count": 2
      }
    }
  ],
  "rejected_calls": [],
  "status": "completed"
}
```

这份 trace 可以证明几件事。

第一，Registry 发现了两个 Skill：

```text
meeting-task-extractor
writing-weekly-report
```

第二，Router 选中了 `meeting-task-extractor`，原因是规则命中了会议纪要和待办提取相关关键词。

第三，Loader 只加载了命中的 `meeting-task-extractor/SKILL.md`。

第四，Executor 请求调用 `extract_tasks`，`ScriptRunner` 允许执行，并成功返回两个待办。

第五，`rejected_calls` 为空，说明这次没有触发安全拒绝。

## 九、场景二：未知脚本被拒绝

运行未知脚本场景：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario unknown-script
```

入口脚本会把 `script_name` 改成：

```python
script_name = "delete_everything"
```

这个脚本并没有出现在 `meeting-task-extractor/SKILL.md` 的 `scripts` 声明里。

关键输出：

```json
{
  "script_calls": [
    {
      "name": "delete_everything",
      "path": "",
      "status": "rejected",
      "error": "script is not declared by selected skill"
    }
  ],
  "rejected_calls": [
    {
      "name": "delete_everything",
      "status": "rejected",
      "error": "script is not declared by selected skill"
    }
  ],
  "status": "rejected"
}
```

这证明第一道边界有效：即使 Executor 收到一个脚本名，`ScriptRunner` 也会先检查它是否属于当前 Skill 的声明白名单。

没有声明，就不执行。

## 十、场景三：非法参数被拒绝

运行非法参数场景：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario invalid-args
```

入口脚本会把参数改成：

```python
script_arguments = {"content": 123}
```

而 `SKILL.md` 声明的 schema 要求：

```json
{
  "content": {
    "type": "string",
    "max_length": 5000
  }
}
```

关键输出：

```json
{
  "script_calls": [
    {
      "name": "extract_tasks",
      "path": "scripts/extract_tasks.py",
      "status": "rejected",
      "error": "argument content must be a string"
    }
  ],
  "status": "rejected"
}
```

这证明第二道边界有效：脚本参数不是随便传的。即使脚本名合法，只要参数不符合 schema，也不会进入 subprocess 执行。

这也回答了一个容易混淆的问题：非法参数不是用户 prompt 本身，而是 runtime 准备传给脚本的结构化 JSON 参数。

## 十一、场景四：路径逃逸被拒绝

运行路径逃逸场景：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario path-escape
```

入口脚本会请求调用：

```python
script_name = "escape_probe"
```

这个脚本确实被声明了，但它的路径是：

```text
../outside.py
```

也就是说，它试图逃出当前 Skill 的 `scripts/` 目录。

关键输出：

```json
{
  "script_calls": [
    {
      "name": "escape_probe",
      "path": "../outside.py",
      "status": "rejected",
      "error": "script path must stay inside selected skill scripts directory"
    }
  ],
  "status": "rejected"
}
```

这证明第三道边界有效：即使脚本名在白名单中，只要声明路径越界，仍然不能执行。

这个场景很重要。因为只做“脚本名白名单”还不够，如果白名单里的路径可以写成 `../outside.py`，那 Skill 目录边界就形同虚设。路径归一化和目录限制必须在执行前做。

## 十二、完整回归命令

为了确认四个场景都符合预期，可以连续运行：

```bash
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario legal
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario unknown-script
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario invalid-args
uv run python labs/skills/foundations/examples/stage7-script-skill/run_runtime_demo.py --scenario path-escape
```

判断标准如下：

| 场景 | 预期状态 | 关键证据 |
| --- | --- | --- |
| `legal` | `completed` | `script_calls[0].status` 是 `completed`，`task_count` 是 `2` |
| `unknown-script` | `rejected` | `error` 是 `script is not declared by selected skill` |
| `invalid-args` | `rejected` | `error` 是 `argument content must be a string` |
| `path-escape` | `rejected` | `error` 是 `script path must stay inside selected skill scripts directory` |

这四个场景覆盖了阶段 7 最核心的证据链：

```text
合法脚本可以执行；
未声明脚本不能执行；
参数不合法不能执行；
路径越界不能执行。
```

## 十三、实验边界

这个实验故意保持教学版，不把所有工程问题一次性做完。

它已经做了：

- Skill 私有 `scripts/` 目录；
- `SKILL.md` 中的脚本声明；
- 规则优先的 Skill 路由；
- Executor 和 ScriptRunner 的职责拆分；
- 脚本白名单检查；
- 相对路径和 `scripts/` 目录边界检查；
- 简化版参数 schema 校验；
- subprocess 超时控制；
- stdout JSON object 解析；
- trace 中记录脚本调用和拒绝原因。

它还没有做：

- 完整 YAML 解析；
- 完整 JSON Schema 校验；
- 操作系统级沙箱；
- 网络隔离；
- CPU、内存、文件写入配额；
- 多脚本智能选择；
- 人工确认；
- 审计日志脱敏；
- 脚本返回结果的业务级校验。

这些都值得做，但不应该塞进阶段 7。阶段 7 只需要把一个核心边界讲清楚：Skill 可以声明脚本，runtime 才能受控执行脚本。

## 十四、常见问题

**1. `script_runner.py` 是只服务 `meeting-task-extractor` 吗？**

不是。它是通用脚本执行安全层。后续任何 Skill 只要在自己的 `SKILL.md` 中声明 `scripts`，理论上都可以复用同一个 `ScriptRunner`。

**2. 为什么不让 Executor 直接调用 `extract_tasks.py`？**

因为那会回到阶段 5 的硬编码模式。每新增一个脚本，Executor 就要新增一个分支。阶段 7 的目标是让 Executor 只负责编排，把通用安全检查交给 `ScriptRunner`。

**3. 为什么 `escape_probe` 明明在 Skill 里声明了，仍然被拒绝？**

因为白名单只解决“有没有声明”，不解决“路径是否安全”。`escape_probe` 的路径是 `../outside.py`，解析后不在当前 Skill 的 `scripts/` 目录内，所以必须拒绝。

**4. 为什么默认不使用 Ollama？**

因为本阶段研究重点是脚本执行安全，不是模型路由。默认用规则命中可以让实验更稳定、更容易复现。需要观察模型兜底时，再打开 `--model-fallback`。

**5. 这个实验是不是生产级安全方案？**

不是。它是教学用边界实验。生产环境还需要更强的沙箱、权限隔离、资源限制、审计和人工确认。这个实验只负责解释 runtime 层至少应该有哪些基本检查。

## 十五、验收清单

完成本实验后，至少应该能确认：

```text
1. 能运行 legal 场景，并看到 selected_skill 是 meeting-task-extractor。
2. legal 场景中 script_calls 出现 extract_tasks。
3. legal 场景中 task_count 是 2。
4. unknown-script 场景被拒绝，原因是脚本未声明。
5. invalid-args 场景被拒绝，原因是 content 不是字符串。
6. path-escape 场景被拒绝，原因是脚本路径逃出 scripts/ 目录。
7. trace 能展示 Registry、Router、Loader、Executor 和 ScriptRunner 的完整链路。
8. 能解释 Executor 和 ScriptRunner 的区别：前者负责执行编排，后者负责安全执行。
```

如果这些都成立，就说明阶段 7 的目标已经达到：脚本型 Skill 不再只是“在提示词里说可以运行脚本”，而是进入了 runtime 可控制、可观察、可拒绝的执行链路。

## 小结

阶段 5 让我们看清了 Skills runtime 的基本骨架：

```text
Registry -> Router -> Loader -> Executor -> Trace
```

阶段 7 在这个骨架上补上了脚本执行边界：

```text
Executor -> ScriptRunner -> Skill scripts/
```

这一步的关键判断是：

> Skill 负责声明任务方法和可用脚本，Executor 负责发起执行意图，ScriptRunner 负责安全检查和受控执行。

把这条边界拆开以后，后续新增脚本型 Skill 时，就不必不断修改 Executor 的硬编码分支。更重要的是，runtime 能清楚记录：哪些脚本被允许执行，哪些调用被拒绝，拒绝发生在哪一层。

对于 Skills 学习路线来说，这就是从“提示词式能力描述”走向“可执行能力包”的关键一步。
