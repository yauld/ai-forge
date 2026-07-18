"""资产风险等级判定规则。"""

from __future__ import annotations

from asset_schemas import Asset, RiskLevel


def assess_asset_by_rules(asset: Asset) -> tuple[RiskLevel, str]:
    """用稳定规则先给出风险等级，保证实验输出可复现。

    模型负责解释和建议；规则负责等级判定。这样读者能把注意力放在 Send 的分发
    与 reducer 的合并上，而不是被模型 JSON 格式问题打断。
    """
    open_ports = set(asset["open_ports"])
    tags = set(asset["tags"])
    exposed_paths = set(asset["exposed_paths"])

    high_risk_signals = []
    if "public" in tags and "test-env" in tags:
        high_risk_signals.append("公网暴露测试环境")
    if 8080 in open_ports:
        high_risk_signals.append("开放 8080 这类常见测试或管理端口")
    if not asset["has_https"]:
        high_risk_signals.append("未启用 HTTPS")
    if exposed_paths & {"/debug", "/actuator"}:
        high_risk_signals.append("暴露调试或运行时信息路径")

    if high_risk_signals:
        return "高", "；".join(high_risk_signals)

    medium_risk_signals = []
    if 22 in open_ports and "public" in tags:
        medium_risk_signals.append("公网资产开放 SSH")
    if "admin" in tags and "public" in tags:
        medium_risk_signals.append("公网暴露管理入口")

    if medium_risk_signals:
        return "中", "；".join(medium_risk_signals)

    return "低", "只暴露必要服务，未命中本实验中的高危或中危规则"

