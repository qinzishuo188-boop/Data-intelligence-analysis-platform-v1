from __future__ import annotations

import re
from io import StringIO
from typing import Any

import pandas as pd


PLATFORMS = ("京东", "天猫", "淘宝", "拼多多", "抖音", "快手", "小红书", "微信", "美团", "线下")
REGIONS = (
    "华东", "华南", "华北", "华中", "西南", "西北", "东北", "全国",
    "北京", "上海", "广州", "深圳", "杭州", "成都", "苏州", "武汉",
)
CATEGORIES = (
    "水果", "粮油", "日用品", "3C", "3C数码", "家电", "服饰", "家居",
    "美妆", "食品", "饮料", "手机", "电脑", "穿戴", "母婴", "汽车",
)
METRIC_PATTERN = re.compile(
    r"(?P<label>市场规模|销售额|成交额|GMV|采购金额|采购额|金额|营收|收入|客单价|日活用户|月活用户|活跃用户|人均使用时长|使用时长|销量|销售量|订单量|用户数|人数|占比|份额|渗透率|同比增长|同比|环比增长|环比|增长率|增长|增速)"
    r"(?:为|达|约|同比|环比)?"
    r"\s*(?P<value>-?\d+(?:\.\d+)?)\s*(?P<unit>亿元|万元|元|%|件|台|单|人|亿|分钟)?"
)
TIME_PATTERN = re.compile(
    r"(20\d{2}年(?:Q[1-4]|[一二三四]季度|\d{1,2}月)?|20\d{2}[/-]\d{1,2}(?:[/-]\d{1,2})?|Q[1-4]|[一二三四]季度)"
)
USER_PROFILE_PATTERN = re.compile(
    r"((?:\d{1,2}\s*-\s*\d{1,2}岁)?[^，。；\n]{0,14}(?:用户|人群)[^，。；\n]{0,14})"
)


def normalize_text(text: str) -> str:
    normalized = str(text or "")
    normalized = normalized.translate(str.maketrans("０１２３４５６７８９．－，％：；（）", "0123456789.-,%:;()"))
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def parse_numeric_value(text: str, unit: str = "") -> float:
    value = float(text)
    if unit == "亿元":
        return value * 100000000
    if unit == "亿":
        return value * 100000000
    if unit == "万元":
        return value * 10000
    return value


def split_clauses(text: str) -> list[str]:
    normalized = normalize_text(text)
    return [item.strip(" ，,;；。") for item in re.split(r"[;\n；。]", normalized) if item.strip(" ，,;；。")]


def parse_delimited_text(text: str) -> pd.DataFrame | None:
    lines = [line.strip() for line in normalize_text(text).splitlines() if line.strip()]
    for separator in (",", "\t", "|", ";"):
        matched = [line for line in lines if separator in line]
        if len(matched) < 2:
            continue
        if all((":" in line or "：" in line) for line in matched):
            continue
        try:
            table = pd.read_csv(StringIO("\n".join(matched)), sep=re.escape(separator), engine="python")
            if table.shape[1] >= 2 and len(table) >= 1:
                return table
        except Exception:
            continue
    return None


def parse_key_value_lines(text: str) -> pd.DataFrame | None:
    records: list[dict[str, Any]] = []
    for line in normalize_text(text).splitlines():
        match = re.match(r"^(.+?)[:：]\s*(.+?)$", line.strip())
        if not match:
            continue
        key = match.group(1).strip()
        raw_value = match.group(2).strip()
        if any(token in raw_value for token in (",", "，", ";", "；")):
            continue
        numeric = None
        metric_match = re.search(r"(-?\d+(?:\.\d+)?)\s*(亿元|万元|元|%|件|台|单|人)?", raw_value)
        if metric_match:
            numeric = parse_numeric_value(metric_match.group(1), metric_match.group(2) or "")
        records.append({
            "字段": key,
            "值": numeric if numeric is not None else raw_value,
            "原始值": raw_value,
        })
    return pd.DataFrame(records) if len(records) >= 2 else None


def find_first(items: tuple[str, ...], text: str) -> str:
    for item in items:
        if item in text:
            return item
    return ""


def extract_subject(clause: str) -> str:
    metric_match = METRIC_PATTERN.search(clause)
    prefix = clause[:metric_match.start()] if metric_match else clause
    prefix = re.split(r"(其中|平台上|平台以|数据显示|报告指出|根据|在)", prefix)[-1]
    prefix = re.sub(r"(为主|贡献最高|表现突出|增速最高|领先)$", "", prefix)
    prefix = prefix.strip(" ，,：:")
    if not prefix:
        return "文本片段"
    if len(prefix) > 28:
        prefix = prefix[:28].rstrip("，, ")
    return prefix


def extract_metrics(clause: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for match in METRIC_PATTERN.finditer(clause):
        label = match.group("label")
        unit = match.group("unit") or ""
        metrics[label] = parse_numeric_value(match.group("value"), unit)
        if unit and label not in {"同比增长", "同比", "环比增长", "环比", "增长率", "增长", "增速", "占比", "份额", "渗透率"}:
            metrics[f"{label}单位"] = unit
    return metrics


def robust_text_to_table(text: str) -> pd.DataFrame | None:
    normalized = normalize_text(text)
    if not normalized:
        return None

    clauses = split_clauses(normalized)
    if not clauses:
        return None

    context: dict[str, Any] = {}
    records: list[dict[str, Any]] = []

    for clause in clauses:
        time_value = TIME_PATTERN.search(clause)
        if time_value:
            context["时间"] = time_value.group(1)

        platform = find_first(PLATFORMS, clause)
        if platform:
            context["平台"] = platform

        region = find_first(REGIONS, clause)
        if region:
            context["地域"] = region

        category = find_first(CATEGORIES, clause)
        if category:
            context["品类"] = category

        user_profile = USER_PROFILE_PATTERN.search(clause)
        if user_profile:
            context["用户画像"] = user_profile.group(1).strip()

        metrics = extract_metrics(clause)
        if not metrics:
            continue

        record = dict(context)
        record["项目"] = extract_subject(clause)
        record["原文片段"] = clause
        record.update(metrics)

        if any(keyword in clause for keyword in ("领先", "高于", "低于", "优于", "弱于", "对比", "竞争", "差异", "排名")):
            record["对比关系"] = "是"
        if any(keyword in clause for keyword in ("上升", "下降", "增长", "回落", "走高", "走低", "提升", "下滑")):
            record["趋势"] = "是"

        records.append(record)

    if records:
        return pd.DataFrame(records)

    for parser in (parse_delimited_text, parse_key_value_lines):
        table = parser(normalized)
        if table is not None and not table.empty:
            return table

    return pd.DataFrame({"文本片段": clauses})
