"""Runtime App：串联 Registry、Router、Loader、ReferenceLoader 和 Trace。"""

from __future__ import annotations

from pathlib import Path

from .access_policy import AccessPolicy
from .loader import SkillLoader
from .reference_loader import ReferenceLoader
from .reference_planner import OllamaReferencePlanner
from .registry import SkillRegistry
from .router import OllamaSkillRouter
from .trace import TraceRecorder


class SkillRuntime:
    """阶段 6 的 references 边界 runtime。

    这一阶段不重新发明阶段 5 的架构，而是在标准链路里补上
    ReferencePlanner 和 ReferenceLoader，专门观察 references 的路径边界。
    """

    def __init__(self, skills_root: Path, model_name: str, role: str) -> None:
        # AccessPolicy 模拟企业里的角色权限：不同角色只能看到自己有权限的 Skill。
        # 这一步解决的是“Router 能不能看到某个 Skill”的问题，不等于后续资源读取就安全了。
        self.access_policy = AccessPolicy(role)
        self.registry = SkillRegistry(skills_root)
        self.router = OllamaSkillRouter(model_name)
        self.loader = SkillLoader()
        self.reference_planner = OllamaReferencePlanner(model_name)
        self.reference_loader = ReferenceLoader()

    def run(self, task: str) -> TraceRecorder:
        # Trace 是本实验的观察窗口。每一步都写入 trace，读者不用猜 runtime
        # 到底扫描了什么、授权了什么、模型请求了什么、最后是否被拦截。
        recorder = TraceRecorder(task, role=self.access_policy.role)

        # 第一步仍然扫描完整 Skill 库。企业系统通常也会先有一个全量目录，
        # 再根据用户身份过滤出当前会话可见的 Skill。
        skills = self.registry.scan()
        recorder.trace.registry_skills = [skill.name for skill in skills]
        recorder.add_step(
            "registry.scan",
            "扫描 Skills 目录，读取每个 Skill 的 metadata。",
            skills=recorder.trace.registry_skills,
        )

        # 这是第一道权限门：Router 只能在当前角色授权的 Skill 中选择。
        # 例如 engineer 只能看到 writing-weekly-report，看不到薪酬审查 Skill。
        authorized_skills = self.access_policy.filter_skills(skills)
        recorder.trace.authorized_skills = [skill.name for skill in authorized_skills]
        recorder.add_step(
            "access_policy.filter",
            "根据当前用户角色，只把有权限的 Skills 暴露给 Router。",
            role=self.access_policy.role,
            authorized_skills=recorder.trace.authorized_skills,
        )

        # Router 只基于授权后的 metadata 做选择。这样可以证明：
        # 如果后面发生越权读取，问题不是 Router 看到了未授权 Skill，
        # 而是 reference 加载层没有守住当前 Skill 的资源边界。
        route = self.router.route(task, authorized_skills)
        recorder.trace.selected_skill = route.skill_name
        recorder.trace.route_reason = route.reason
        recorder.add_step(
            "router.route",
            "调用 Ollama，根据 name / description 选择 Skill。",
            selected_skill=route.skill_name,
            reason=route.reason,
            raw_response=route.raw_response,
        )

        if route.skill_name is None:
            recorder.trace.status = "no_matching_skill"
            recorder.add_step("runtime.stop", "没有匹配 Skill，停止加载。")
            return recorder

        metadata = self.registry.get(route.skill_name)
        if metadata is None:
            recorder.trace.status = "unknown_skill"
            recorder.add_step("runtime.stop", "Router 返回了 Registry 中不存在的 Skill。")
            return recorder

        # Loader 只读取命中的 SKILL.md 正文，不读取 references。
        # 这保持了渐进式加载：先选中 Skill，再让后续模块决定是否需要附属资料。
        loaded_skill = self.loader.load(metadata)
        recorder.trace.loaded_files = [str(path) for path in loaded_skill.loaded_files]
        recorder.add_step(
            "loader.load",
            "读取命中 Skill 的 SKILL.md 正文。",
            loaded_files=recorder.trace.loaded_files,
        )

        # ReferencePlanner 使用模型把自然语言任务转成 read_reference(file) 请求。
        # 注意：这里的 file 来自模型输出，可能被用户提示词污染，所以不能被 runtime 信任。
        plan = self.reference_planner.plan(task, loaded_skill)
        recorder.trace.reference_request = {
            "file": plan.file,
            "reason": plan.reason,
            "raw_response": plan.raw_response,
        }
        recorder.add_step(
            "reference_planner.plan",
            "调用 Ollama，把用户任务和 Skill 正文转换成 read_reference 请求。",
            file=plan.file,
            reason=plan.reason,
            raw_response=plan.raw_response,
        )

        # 用同一个模型请求跑两种读取器：
        # - unsafe_read 展示“直接拼路径”会怎样越权；
        # - safe_read 展示 runtime 应如何把路径限制在当前 Skill 的 references 目录内。
        # 对照结果能说明：Skill 权限不能只在 Router 层检查，资源加载层也必须防守。
        unsafe_result = self.reference_loader.unsafe_read(loaded_skill, plan.file)
        safe_result = self.reference_loader.safe_read(loaded_skill, plan.file)
        recorder.trace.unsafe_reference_read = unsafe_result.to_dict()
        recorder.trace.safe_reference_read = safe_result.to_dict()
        recorder.trace.status = "completed"
        recorder.add_step(
            "reference_loader.compare",
            "用同一个 read_reference 请求对比不安全读取和安全读取。",
            unsafe=unsafe_result.to_dict(),
            safe=safe_result.to_dict(),
        )

        return recorder
