from __future__ import annotations

import re
from typing import Any

import pandas as pd

PREVIEW_ROWS = 50


def _normalize_text(text: str) -> str:
    normalized = str(text or "")
    normalized = normalized.translate(str.maketrans("０１２３４５６７８９．－，％", "0123456789.-,%"))
    normalized = re.sub(r"\r\n?", "\n", normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def parse_numeric_value(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = _normalize_text(value)
    if not text:
        return None

    compact = text.replace(",", "").replace(" ", "")
    multiplier = 1.0
    if "亿元" in compact or compact.endswith("亿"):
        multiplier = 100000000.0
    elif "万元" in compact or compact.endswith("万"):
        multiplier = 10000.0

    match = re.search(r"-?\d+(?:\.\d+)?", compact)
    if not match:
        return None
    return float(match.group()) * multiplier


def clean_table_enhanced(table: pd.DataFrame) -> pd.DataFrame:
    cleaned = table.copy()
    cleaned.columns = [
        str(column).strip() if str(column).strip() else f"字段{index + 1}"
        for index, column in enumerate(cleaned.columns)
    ]
    cleaned = cleaned.dropna(how="all").reset_index(drop=True)
    for column in cleaned.columns:
        if cleaned[column].dtype == object:
            converted = cleaned[column].map(parse_numeric_value)
            if converted.notna().sum() >= max(2, len(cleaned) // 2):
                cleaned[column] = converted
    return cleaned


def choose_preferred_category_column(table: pd.DataFrame, category_columns: list[str]) -> str:
    if not category_columns:
        return ""

    priority = ("平台", "项目", "品类", "分类", "名称", "地域", "时间")

    def score(column: str) -> tuple[int, int, int]:
        series = table[column].fillna("").astype(str).str.strip()
        unique_count = series.replace("", pd.NA).dropna().nunique()
        priority_score = 0
        for index, keyword in enumerate(priority):
            if keyword in column:
                priority_score = len(priority) - index
                break
        return (priority_score, unique_count, -category_columns.index(column))

    return sorted(category_columns, key=score, reverse=True)[0]


def recommend_charts_enhanced(
    table: pd.DataFrame,
    numeric_columns: list[str],
    category_columns: list[str],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    if numeric_columns and category_columns:
        x_field = choose_preferred_category_column(table, category_columns)
        primary = numeric_columns[: min(3, len(numeric_columns))]
        suggestions.extend([
            {"type": "horizontalBar", "x": x_field, "y": primary[:1], "title": f"{x_field} 横向对比图", "reason": "适合展示各分类之间的高低差异和排名关系。"},
            {"type": "bar", "x": x_field, "y": primary[:1], "title": f"{x_field} 柱状图", "reason": "适合展示分类数据的绝对值对比。"},
            {"type": "line", "x": x_field, "y": primary[:1], "title": f"{x_field} 趋势折线图", "reason": "适合展示时间序列或阶段变化趋势。"},
            {"type": "pie", "x": x_field, "y": primary[:1], "title": f"{x_field} 占比饼图", "reason": "适合展示单指标的结构占比。"},
            {"type": "rosePie", "x": x_field, "y": primary[:1], "title": f"{x_field} 玫瑰图", "reason": "适合突出各类别占比差异和视觉层次。"},
            {"type": "funnel", "x": x_field, "y": primary[:1], "title": f"{x_field} 漏斗图", "reason": "适合展示流程递进、转化和阶段流失关系。"},
        ])
        if len(primary) >= 2:
            suggestions.extend([
                {"type": "stackedBar", "x": x_field, "y": primary, "title": f"{x_field} 堆叠柱状图", "reason": "适合展示多个指标在同一分类下的组合对比。"},
                {"type": "radar", "x": x_field, "y": primary[: min(5, len(primary))], "title": f"{x_field} 雷达图", "reason": "适合展示多指标综合表现和能力轮廓。"},
            ])
    elif len(numeric_columns) >= 2:
        suggestions.append({"type": "scatter", "x": numeric_columns[0], "y": [numeric_columns[1]], "title": "双指标散点图", "reason": "适合识别两个核心指标之间的相关性和异常点。"})
        suggestions.append({"type": "bar", "x": "", "y": [numeric_columns[0]], "title": f"{numeric_columns[0]} 排名图", "reason": "适合没有明确分类字段时的数值排序展示。"})
    elif len(numeric_columns) == 1:
        suggestions.extend([
            {"type": "bar", "x": category_columns[0] if category_columns else "", "y": [numeric_columns[0]], "title": f"{numeric_columns[0]} 柱状图", "reason": "适合展示单一核心指标的分类差异。"},
            {"type": "line", "x": category_columns[0] if category_columns else "", "y": [numeric_columns[0]], "title": f"{numeric_columns[0]} 折线图", "reason": "适合展示单一指标的变化趋势。"},
        ])
    return suggestions[:8]


def _top_record_text(table: pd.DataFrame, category_column: str, metric_column: str) -> str | None:
    series = pd.to_numeric(table[metric_column], errors="coerce")
    valid = table.loc[series.notna()].copy()
    if valid.empty:
        return None
    max_row = valid.loc[series[series.notna()].idxmax()]
    value = float(max_row[metric_column])
    formatted = f"{value:,.0f}" if abs(value) >= 100 else f"{value:,.2f}"
    return f"{metric_column} 最高的是 {max_row.get(category_column, max_row.iloc[0])}，达到 {formatted}。"


def _collect_detected_entities(table: pd.DataFrame, raw_text: str) -> dict[str, list[str]]:
    text = _normalize_text(raw_text)
    columns = [str(column) for column in table.columns]
    detected: dict[str, list[str]] = {
        "时间": [],
        "品类": [],
        "平台": [],
        "金额": [],
        "增长率": [],
        "占比": [],
        "用户画像": [],
        "地域": [],
        "趋势": [],
        "对比关系": [],
    }

    def add_value(key: str, value: str) -> None:
        value = str(value).strip()
        if value and value not in detected[key]:
            detected[key].append(value)

    for match in re.findall(r"(20\d{2}年(?:\d{1,2}月)?|20\d{2}[/-]\d{1,2}(?:[/-]\d{1,2})?|Q[1-4]|[一二三四]季度|近\d+[天月年])", text):
        add_value("时间", match)
    for column in columns:
        if any(keyword in column for keyword in ("时间", "日期", "月份", "季度", "年份", "周期")):
            add_value("时间", column)

    for match in re.findall(r"((?:水果|粮油|日用品|3C数码|家电|服饰|家居|平台|渠道|行业|手机|电脑)[^,，；。]{0,10}(?:类|品类|行业)?)", text):
        add_value("品类", match)
    for column in columns:
        if any(keyword in column for keyword in ("品类", "分类", "类目", "商品", "项目", "行业")):
            add_value("品类", column)

    for platform in ("天猫", "淘宝", "京东", "拼多多", "抖音", "快手", "小红书", "微信", "APP", "线下", "美团"):
        if platform in text:
            add_value("平台", platform)
    for column in columns:
        if "平台" in column or "渠道" in column:
            add_value("平台", column)

    for column in columns:
        if any(keyword in column for keyword in ("金额", "销售额", "成交额", "GMV", "收入", "营收", "采购额", "客单价", "价格")):
            add_value("金额", column)
    for match in re.findall(r"-?\d+(?:\.\d+)?\s*(?:亿元|万元|元)", text):
        add_value("金额", match.replace(" ", ""))

    for column in columns:
        if any(keyword in column for keyword in ("增长", "增速", "同比", "环比", "涨幅")):
            add_value("增长率", column)
    for match in re.findall(r"-?\d+(?:\.\d+)?\s*%", text):
        add_value("增长率", match.replace(" ", ""))

    for column in columns:
        if any(keyword in column for keyword in ("占比", "份额", "渗透率", "贡献率")):
            add_value("占比", column)

    for column in columns:
        if any(keyword in column for keyword in ("用户", "人群", "画像", "年龄", "性别", "城市等级", "消费层级")):
            add_value("用户画像", column)
    for match in re.findall(r"(?:\d{1,2}\s*-\s*\d{1,2}岁[^，。；\n]{0,12}|[^，。；\n]{0,8}(?:男性|女性|家庭)用户[^，。；\n]{0,10})", raw_text):
        add_value("用户画像", match)
    for keyword in ("用户画像", "核心用户", "年轻用户", "家庭用户", "高消费人群", "新一线城市用户"):
        if keyword in text:
            add_value("用户画像", keyword)

    for column in columns:
        if any(keyword in column for keyword in ("地域", "地区", "区域", "城市", "省份", "产地")):
            add_value("地域", column)
    for region in ("华东", "华南", "华北", "华中", "西南", "西北", "东北", "北京", "上海", "广州", "深圳", "杭州", "成都"):
        if region in text:
            add_value("地域", region)

    for keyword in ("上升", "下降", "增长", "回落", "走高", "走低", "趋势", "提升", "下滑"):
        if keyword in text:
            add_value("趋势", keyword)

    for keyword in ("对比", "领先", "高于", "低于", "优于", "弱于", "竞争", "差异", "排名"):
        if keyword in text:
            add_value("对比关系", keyword)

    return detected


def build_analysis_output(
    table: pd.DataFrame,
    source_name: str,
    numeric_columns: list[str],
    category_columns: list[str],
    raw_text: str,
) -> dict[str, Any]:
    chart_suggestions = recommend_charts_enhanced(table, numeric_columns, category_columns)
    detected = _collect_detected_entities(table, raw_text)
    preview_df = table.head(PREVIEW_ROWS)
    preview_rows = preview_df.where(pd.notnull(preview_df), None).to_dict(orient="records")

    title = f"{source_name}数据智能分析"
    summary = (
        f"系统已完成文本理解、数据结构化、字段识别、表格生成和图表推荐。"
        f"当前共识别 {len(table)} 行数据、{len(table.columns)} 个字段，并输出 {len(chart_suggestions)} 个推荐图表，"
        "结果适合商业汇报、PPT、行业分析和数据可视化展示。"
    )

    insights: list[str] = []
    for column in numeric_columns[:3]:
        series = pd.to_numeric(table[column], errors="coerce").dropna()
        if not series.empty:
            mean_value = float(series.mean())
            max_value = float(series.max())
            mean_text = f"{mean_value:,.0f}" if abs(mean_value) >= 100 else f"{mean_value:,.2f}"
            max_text = f"{max_value:,.0f}" if abs(max_value) >= 100 else f"{max_value:,.2f}"
            insights.append(f"{column} 的均值为 {mean_text}，最大值为 {max_text}。")

    if category_columns and numeric_columns:
        top_text = _top_record_text(table, category_columns[0], numeric_columns[0])
        if top_text:
            insights.append(top_text)

    recognized_labels = [f"{key}：{'、'.join(values[:4])}" for key, values in detected.items() if values]
    if recognized_labels:
        insights.append("已自动识别关键字段，包括 " + "；".join(recognized_labels[:4]) + "。")
    if raw_text.strip():
        insights.append("原始文本已完成自动纠错、单位补全和数字规范化，可直接用于图表展示与汇报材料生成。")

    tables = [{
        "title": "结构化明细表",
        "rowCount": int(len(table)),
        "columns": list(table.columns),
        "previewRows": preview_rows,
    }]

    field_rows = [{"字段": key, "识别结果": "、".join(values)} for key, values in detected.items() if values]
    if field_rows:
        tables.append({
            "title": "识别字段总览",
            "rowCount": len(field_rows),
            "columns": ["字段", "识别结果"],
            "previewRows": field_rows,
        })

    return {
        "title": title,
        "summary": summary,
        "tables": tables,
        "charts": chart_suggestions,
        "insights": insights[:6],
        "recognizedFields": detected,
    }
