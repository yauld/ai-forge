"""AccessPolicy：根据用户角色过滤可用 Skill。"""

from __future__ import annotations

from .types import SkillMetadata


ROLE_SKILLS: dict[str, tuple[str, ...]] = {
    "engineer": ("writing-weekly-report",),
    "finance": ("reviewing-salary-adjustment",),
}


class AccessPolicy:
    """教学用角色权限表。

    阶段 6 的风险前提是：Router 层已经按角色限制了可用 Skill，
    但后续 reference 读取如果不守当前 Skill 边界，仍可能绕过权限。
    """

    def __init__(self, role: str) -> None:
        if role not in ROLE_SKILLS:
            known_roles = ", ".join(sorted(ROLE_SKILLS))
            raise ValueError(f"unknown role {role!r}; choose one of: {known_roles}")
        self.role = role
        self.allowed_skill_names = set(ROLE_SKILLS[role])

    def filter_skills(self, skills: list[SkillMetadata]) -> list[SkillMetadata]:
        """只把当前角色有权限的 Skill 暴露给 Router。"""
        return [skill for skill in skills if skill.name in self.allowed_skill_names]
