"""资产风险 Map-Reduce 实验的状态类型和样例数据。"""

from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


RiskLevel = Literal["高", "中", "低"]


class Asset(TypedDict):
    """一次资产检查需要的最小输入。"""

    host: str
    open_ports: list[int]
    has_https: bool
    tags: list[str]
    exposed_paths: list[str]


class Finding(TypedDict):
    """单个资产的 Map 结果。"""

    host: str
    risk: RiskLevel
    rule_reason: str
    model_analysis: str


class RiskScanState(TypedDict, total=False):
    """Graph 的共享状态。

    `findings` 和 `trace` 会被多个并行的 check_asset 节点同时更新，所以必须声明
    reducer。这里用列表拼接，把每个分支返回的一条结果合并成最终列表。
    """

    assets: list[Asset]
    findings: Annotated[list[Finding], operator.add]
    final_report: str
    trace: Annotated[list[str], operator.add]


class AssetTaskState(TypedDict):
    """Send 发给单个 check_asset 节点的局部状态。"""

    asset: Asset


SAMPLE_ASSETS: list[Asset] = [
    {
        "host": "api.example.com",
        "open_ports": [80, 443],
        "has_https": True,
        "tags": ["api", "production", "public"],
        "exposed_paths": ["/health"],
    },
    {
        "host": "admin.example.com",
        "open_ports": [22, 443],
        "has_https": True,
        "tags": ["admin", "production", "public"],
        "exposed_paths": ["/login"],
    },
    {
        "host": "vpn.example.com",
        "open_ports": [443],
        "has_https": True,
        "tags": ["vpn", "production"],
        "exposed_paths": [],
    },
    {
        "host": "test.example.com",
        "open_ports": [80, 8080],
        "has_https": False,
        "tags": ["test-env", "public"],
        "exposed_paths": ["/debug", "/actuator"],
    },
]
