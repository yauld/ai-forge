"""Runtime App：串联 Registry、Router、Loader、Executor、ScriptRunner 和 Trace。"""

from __future__ import annotations

from pathlib import Path

from .executor import SkillExecutor
from .loader import SkillLoader
from .registry import SkillRegistry
from .router import RuleFirstSkillRouter
from .trace import TraceRecorder


class SkillRuntime:
    """阶段 7 的脚本型 Skills runtime。

    它继承阶段 5 的主干，并把 Executor 后面的执行动作改造成
    Skill 私有 scripts 的受控调用。

    这个类可以理解成 runtime 的“总调度器”。它本身不负责解析脚本、
    不负责判断脚本路径是否安全，也不负责实现具体业务逻辑；它只把
    一次请求按固定顺序交给 Registry、Router、Loader、Executor 和 Trace。
    这样每个模块的职责都比较薄，后续要替换某一层时不会牵动整条链路。
    """

    def __init__(
        self,
        skills_root: Path,
        model_name: str,
        *,
        use_model_fallback: bool = True,
    ) -> None:
        # Registry 只负责建立 Skill 索引：扫描 skills/*/SKILL.md，
        # 并读取 frontmatter 中的 name、description、scripts 等 metadata。
        # 注意：这里不会读取 Skill 正文，也不会检查脚本是否真的安全。
        self.registry = SkillRegistry(skills_root)

        # Router 只负责“选哪个 Skill”。阶段 7 采用规则优先的路由策略：
        # 命中明确关键词时直接返回；规则不确定时才可选择交给本地模型兜底。
        # 这能让脚本执行实验在没有 Ollama 的情况下也能稳定运行。
        self.router = RuleFirstSkillRouter(
            model_name,
            use_model_fallback=use_model_fallback,
        )

        # Loader 只在 Router 选中 Skill 之后读取对应 SKILL.md 正文。
        # 这延续阶段 5 的渐进式加载思想：发现阶段只看 metadata，
        # 命中后才把具体执行说明加载进来。
        self.loader = SkillLoader()

        # Executor 是执行编排层：它决定本次请求要调用哪个脚本、
        # 如何构造参数，并把真正的安全执行委托给 ScriptRunner。
        # 因此 app.py 不需要知道 extract_tasks.py 的内部实现。
        self.executor = SkillExecutor()

    def run(
        self,
        task: str,
        content: str,
        *,
        script_name: str | None = None,
        script_arguments: dict | None = None,
    ) -> TraceRecorder:
        # TraceRecorder 是本实验的可观察性入口。
        # 每经过一个 runtime 模块，就往 trace 里写一条 step，
        # 方便从最终 JSON 反查请求到底经历了哪些处理。
        recorder = TraceRecorder(task)

        # 1. Registry 阶段：扫描 Skill 目录，建立可路由的候选列表。
        # 这里读取的是 frontmatter metadata，而不是完整 SKILL.md 正文。
        # 对阶段 7 来说，scripts 声明也会在这里进入 metadata，
        # 但 Registry 不执行脚本，也不承担安全策略。
        skills = self.registry.scan()
        recorder.trace.registry_skills = [skill.name for skill in skills]
        recorder.add_step(
            "registry.scan",
            "扫描 Skills 目录，读取每个 Skill 的 metadata。",
            skills=recorder.trace.registry_skills,
        )

        # 2. Router 阶段：根据用户任务选择一个 Skill。
        # 这一步仍然只看 name / description，不看 Skill 正文，
        # 也不允许模型直接指定任意脚本路径。
        route = self.router.route(task, skills)
        recorder.trace.selected_skill = route.skill_name
        recorder.trace.route_reason = route.reason
        recorder.add_step(
            "router.route",
            "规则优先，根据 name / description 选择 Skill；规则模糊时可交给 Ollama。",
            selected_skill=route.skill_name,
            reason=route.reason,
            raw_response=route.raw_response,
        )

        # 如果没有任何 Skill 匹配，就在这里停止。
        # 这条分支能证明 runtime 不会为了“完成任务”而绕过路由，
        # 更不会在未选中 Skill 的情况下调用脚本。
        if route.skill_name is None:
            recorder.trace.status = "no_matching_skill"
            recorder.add_step("runtime.stop", "没有匹配 Skill，停止加载和执行。")
            return recorder

        # Router 返回的是 Skill name。真正的 SkillMetadata 仍然必须回到
        # Registry 查询，避免 Router 返回一个并不存在的 Skill。
        metadata = self.registry.get(route.skill_name)
        if metadata is None:
            recorder.trace.status = "unknown_skill"
            recorder.add_step("runtime.stop", "Router 返回了 Registry 中不存在的 Skill。")
            return recorder

        # 3. Loader 阶段：命中后才读取 SKILL.md 正文。
        # 到这里，runtime 已经知道用户请求应该交给哪个 Skill，
        # 所以只加载这一个 Skill 的正文，而不是把所有 Skill 全部塞进上下文。
        loaded_skill = self.loader.load(metadata)
        recorder.trace.loaded_files = [str(path) for path in loaded_skill.loaded_files]
        recorder.add_step(
            "loader.load",
            "读取命中 Skill 的 SKILL.md 正文。",
            loaded_files=recorder.trace.loaded_files,
            declared_scripts=[script.name for script in loaded_skill.metadata.scripts],
        )

        # 4. Executor 阶段：执行层入口。
        # Executor 接收已加载的 Skill、用户任务和内容，然后决定调用哪个脚本。
        # script_name / script_arguments 是为了实验安全场景预留的覆盖参数：
        # - legal：不传，Executor 默认调用 Skill 声明的第一个脚本；
        # - unknown-script：传一个未声明脚本名，验证白名单拒绝；
        # - invalid-args：传非法参数，验证 schema 拒绝；
        # - path-escape：传声明了但路径越界的脚本名，验证路径边界拒绝。
        result = self.executor.execute(
            loaded_skill,
            task=task,
            content=content,
            script_name=script_name,
            script_arguments=script_arguments,
        )

        # 5. Trace 汇总阶段：把 Executor / ScriptRunner 的结果转成
        # 最终 trace JSON 中稳定可读的字段。
        # 这里刻意保留 stdout/stderr 的 preview，而不是完整输出，
        # 是为了让 trace 具备调试价值，同时避免日志无限膨胀。
        recorder.trace.status = result.status
        recorder.trace.script_calls = [
            {
                "name": call.name,
                "path": call.path,
                "status": call.status,
                "exit_code": call.exit_code,
                "result": call.result,
                "stdout_preview": call.stdout_preview,
                "stderr_preview": call.stderr_preview,
                "error": call.error,
            }
            for call in result.script_calls
        ]

        # rejected_calls 是从 script_calls 中派生出来的快捷视图。
        # 文章或实验讲解时可以直接看这个字段，确认哪些调用被安全层挡住。
        recorder.trace.rejected_calls = [
            call for call in recorder.trace.script_calls if call["status"] == "rejected"
        ]
        recorder.add_step(
            "executor.execute",
            "Executor 选择脚本并交给 ScriptRunner 做受控执行。",
            summary=result.summary,
            script_calls=recorder.trace.script_calls,
            rejected_calls=recorder.trace.rejected_calls,
        )

        return recorder
