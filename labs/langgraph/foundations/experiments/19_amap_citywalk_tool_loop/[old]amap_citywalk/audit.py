"""Host 侧可审计边界：POI、坐标、路线和最终回答校验。"""

from __future__ import annotations

import re
from typing import Any


def collect_verified_pois(tool_result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """从 maps_around_search 结果中提取可用于后续地图生成的 POI 白名单。"""
    verified: dict[str, dict[str, Any]] = {}
    pois = tool_result.get("pois")
    if not isinstance(pois, list):
        return verified

    for poi in pois:
        if not isinstance(poi, dict):
            continue
        poi_id = str(poi.get("id") or "").strip()
        name = str(poi.get("name") or "").strip()
        if not poi_id or not name:
            continue
        verified[poi_id] = {
            "name": name,
            "address": poi.get("address"),
            "typecode": poi.get("typecode"),
        }
    return verified


def parse_location(value: Any) -> dict[str, float] | None:
    """解析高德 location 字段，格式通常是 "lon,lat"。"""
    if not isinstance(value, str):
        return None
    raw_lon, separator, raw_lat = value.partition(",")
    if not separator:
        return None
    try:
        return {"lon": float(raw_lon), "lat": float(raw_lat)}
    except ValueError:
        return None


def collect_verified_poi_coordinates(
    arguments: dict[str, Any],
    tool_result: dict[str, Any],
    verified_pois: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, float]]]:
    """把 maps_geo 结果绑定到查询文本中明确出现的白名单 POI。"""
    query = " ".join(str(arguments.get(key) or "") for key in ("address", "city"))
    matched_poi_ids = [
        poi_id
        for poi_id, poi in verified_pois.items()
        if poi["name"] and poi["name"] in query
    ]
    if not matched_poi_ids:
        return {}

    results = tool_result.get("results")
    if not isinstance(results, list):
        return {}

    coordinates = [
        coordinate
        for result in results
        if isinstance(result, dict)
        if (coordinate := parse_location(result.get("location"))) is not None
    ]
    if not coordinates:
        return {}

    return {poi_id: coordinates for poi_id in matched_poi_ids}


def coordinates_match(point: dict[str, Any], candidates: list[dict[str, float]]) -> bool:
    """判断地图点坐标是否来自同一个 POI 的 maps_geo 结果。"""
    try:
        lon = float(point.get("lon"))
        lat = float(point.get("lat"))
    except (TypeError, ValueError):
        return False

    return any(
        abs(lon - candidate["lon"]) < 0.000001
        and abs(lat - candidate["lat"]) < 0.000001
        for candidate in candidates
    )


def extract_duration(text: str) -> str | None:
    """从路线标题中提取建议停留时间。"""
    match = re.search(r"约?\s*\d+(?:\.\d+)?\s*(?:小时|分钟|h|min)", text, re.I)
    if match is None:
        return None
    return match.group(0).replace(" ", "")


def validate_personal_map_pois(
    arguments: dict[str, Any],
    verified_pois: dict[str, dict[str, Any]],
    verified_poi_coordinates: dict[str, list[dict[str, float]]],
) -> str | None:
    """校验个人地图中的点是否来自真实 POI，且坐标绑定到同一个 POI。"""
    line_list = arguments.get("lineList")
    if not isinstance(line_list, list):
        return "Host校验失败：maps_schema_personal_map 的 lineList 中没有有效地点。"

    checked_points = 0
    for line in line_list:
        if not isinstance(line, dict):
            continue
        title = str(line.get("title") or "").strip()
        if extract_duration(title) is None:
            return (
                "Host校验失败：每个路线段 title 必须包含建议停留时间，"
                "例如「第1站：晓风书屋(阅见西湖店)（约1小时）」。"
            )
        point_info_list = line.get("pointInfoList")
        if not isinstance(point_info_list, list):
            continue

        for point in point_info_list:
            if not isinstance(point, dict):
                continue
            checked_points += 1
            poi_id = str(point.get("poiId") or "").strip()
            name = str(point.get("name") or "").strip()
            verified = verified_pois.get(poi_id)
            if verified is None:
                return (
                    "Host校验失败：地图点 "
                    f"{name or '<未命名>'} 使用的 poiId={poi_id or '<缺失>'} "
                    "不在 maps_around_search 返回的 POI 白名单中。请只使用搜索结果里的 "
                    "id/name 组织路线；缺坐标时可以再用 maps_geo 补坐标。"
                )
            if name != verified["name"]:
                return (
                    "Host校验失败：地图点名称必须与搜索结果完全一致。"
                    f"poiId={poi_id} 的真实名称是「{verified['name']}」，"
                    f"但模型传入了「{name or '<未命名>'}」。"
                )
            coordinates = verified_poi_coordinates.get(poi_id, [])
            if not coordinates:
                return (
                    "Host校验失败：地图点 "
                    f"「{name}」还没有经过 maps_geo 坐标绑定。请使用该 POI 的精确名称"
                    "调用 maps_geo，例如把搜索结果里的 name 和 address 一起作为查询文本；"
                    "不能用其他地点的地理编码结果代替。"
                )
            if not coordinates_match(point, coordinates):
                return (
                    "Host校验失败：地图点 "
                    f"「{name}」的 lon/lat 没有出现在该 POI 绑定过的 maps_geo 结果中。"
                    "请重新用该 POI 的精确名称调用 maps_geo，并使用返回的坐标。"
                )

    if checked_points == 0:
        return "Host校验失败：maps_schema_personal_map 的 lineList 中没有有效地点。"

    return None


def summarize_verified_pois(
    verified_pois: dict[str, dict[str, Any]],
    limit: int = 8,
) -> str:
    """生成白名单摘要，帮助模型被拒绝后改正。"""
    items = list(verified_pois.items())[:limit]
    return "；".join(f"{poi['name']}({poi_id})" for poi_id, poi in items)


UNVERIFIED_FINAL_CLAIMS = (
    "室内",
    "全程室内",
    "少走路",
    "一楼",
    "一层",
    "大堂",
    "内设",
    "步行",
    "间距",
    "距离",
    "紧邻",
    "集中",
    "顺直",
    "无需绕路",
    "不影响游玩",
    "氛围",
    "知名",
    "文艺",
)


def find_unverified_final_claims(text: str) -> list[str]:
    """找出最终回答中常见的未验证行程描述。"""
    return [claim for claim in UNVERIFIED_FINAL_CLAIMS if claim in text]
