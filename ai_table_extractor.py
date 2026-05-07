from __future__ import annotations

import json
import os
import re
import hashlib
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "runtime" / "ai_provider_config.json"
DEFAULT_BASE_URL = "https://api.ichenfu.cn/v1"
DEFAULT_MODEL = "MiMo-V2.5-Pro"
DEFAULT_TIMEOUT = 120
PROMPT_VERSION = "2026-04-fast-json-v1"
AI_CACHE_DIR = ROOT_DIR / "cache" / "_ai"


def load_ai_config() -> dict[str, Any]:
    config: dict[str, Any] = {}
    if DEFAULT_CONFIG_PATH.exists():
        config = json.loads(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))

    base_url = os.environ.get("CHART_AI_BASE_URL") or config.get("base_url") or DEFAULT_BASE_URL
    api_key = os.environ.get("CHART_AI_API_KEY") or config.get("api_key") or ""
    model = os.environ.get("CHART_AI_MODEL") or config.get("model") or DEFAULT_MODEL
    enabled = str(os.environ.get("CHART_AI_ENABLED", config.get("enabled", True))).lower() not in {"0", "false", "no"}
    timeout = int(os.environ.get("CHART_AI_TIMEOUT", config.get("timeout", DEFAULT_TIMEOUT)))
    max_workers = int(os.environ.get("CHART_AI_MAX_WORKERS", config.get("max_workers", 3)))

    return {
        "enabled": enabled and bool(api_key),
        "base_url": str(base_url).rstrip("/"),
        "api_key": str(api_key).strip(),
        "model": str(model).strip(),
        "timeout": timeout,
        "max_workers": max(1, min(max_workers, 6)),
    }


def _cache_key(text: str, source_name: str, config: dict[str, Any]) -> str:
    fingerprint = json.dumps(
        {
            "version": PROMPT_VERSION,
            "base_url": config["base_url"],
            "model": config["model"],
            "source": source_name or "",
            "text": text,
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()


def _read_cached_table(cache_key: str) -> tuple[pd.DataFrame, dict[str, Any]] | None:
    cache_file = AI_CACHE_DIR / f"{cache_key}.json"
    if not cache_file.exists():
        return None
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
        table = pd.DataFrame(payload.get("rows") or [])
        if table.empty:
            return None
        meta = payload.get("meta") or {}
        meta["cached"] = True
        return table, meta
    except Exception:
        return None


def _write_cached_table(cache_key: str, table: pd.DataFrame, meta: dict[str, Any]) -> None:
    try:
        AI_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = AI_CACHE_DIR / f"{cache_key}.json"
        cache_file.write_text(
            json.dumps(
                {
                    "rows": table.where(pd.notnull(table), None).to_dict(orient="records"),
                    "meta": meta,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def get_ai_status() -> dict[str, Any]:
    config = load_ai_config()
    return {
        "enabled": bool(config["enabled"]),
        "configured": bool(config["api_key"]),
        "baseUrl": config["base_url"],
        "model": config["model"],
    }


def _extract_json_block(content: str) -> str:
    text = str(content or "").strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, flags=re.S)
    if fenced:
        return fenced.group(1).strip()

    start_positions = [pos for pos in (text.find("{"), text.find("[")) if pos >= 0]
    if not start_positions:
        return text
    return text[min(start_positions):].strip()


def _payload_to_dataframe(payload: Any) -> pd.DataFrame:
    if isinstance(payload, dict) and "table" in payload:
        payload = payload["table"]

    if isinstance(payload, dict) and "rows" in payload:
        rows = payload.get("rows") or []
        if isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows):
            return pd.DataFrame(rows)

    if isinstance(payload, list) and payload and all(isinstance(item, dict) for item in payload):
        return pd.DataFrame(payload)

    if isinstance(payload, dict):
        if all(isinstance(value, list) for value in payload.values()):
            return pd.DataFrame(payload)
        return pd.DataFrame([{"field": key, "value": value} for key, value in payload.items()])

    raise ValueError("AI response did not contain a usable table.")


def _request_ai_table_once(text: str, source_name: str, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    endpoint = f"{config['base_url']}/chat/completions"
    prompt_text = str(text or "").strip()[:12000]
    payload = {
        "model": config["model"],
        "temperature": 0.1,
        "max_tokens": 1800,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract chart-ready structured data from Chinese business text, OCR text, reports, "
                    "meeting notes, and copied tables. Return JSON only. "
                    "Do not add markdown or explanations. "
                    "If the text contains repeated entities and metrics, return one row per entity as a list of objects. "
                    "Merge multiple metrics for the same entity into the same row. "
                    "If the text is key-value style, convert it into rows with item/value style columns. "
                    "Never invent values that are not present in the input."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Source: " + (source_name or "text input") + "\n"
                    "Please convert the following content into a JSON object with this shape:\n"
                    "{\n"
                    '  "table": {\n'
                    '    "rows": [\n'
                    '      {"项目": "...", "采购金额": 123, "同比增长": 0.126, "占比": 0.34}\n'
                    "    ]\n"
                    "  }\n"
                    "}\n"
                    "Requirements:\n"
                    "1. Use Chinese column names when possible.\n"
                    "2. Keep numeric fields as numbers, not strings, when the text provides numeric values.\n"
                    "3. Preserve categories such as 时间, 平台, 品类, 地区, 用户画像, 指标, 占比, 同比, 环比 if they appear.\n"
                    "4. If there are multiple metrics for one entity, put them in the same row.\n"
                    "5. Prefer business rows such as 商品, 平台, 地区, 品类, 时间段. Do not split every single number into separate rows unless no entity exists.\n"
                    "6. Return at least one structured table only.\n\n"
                    "Example transformation:\n"
                    "Input: 红富士苹果采购金额126000元，同比增长12.6%；花牛苹果采购金额87000元，同比增长6.2%。\n"
                    "Output:\n"
                    "{\n"
                    '  "table": {\n'
                    '    "rows": [\n'
                    '      {"项目": "红富士苹果", "采购金额": 126000, "同比增长": 0.126},\n'
                    '      {"项目": "花牛苹果", "采购金额": 87000, "同比增长": 0.062}\n'
                    "    ]\n"
                    "  }\n"
                    "}\n\n"
                    "Input text:\n"
                    + prompt_text
                ),
            },
        ],
    }

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config['api_key']}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=config["timeout"]) as response:
            body = response.read().decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"AI request failed with HTTP {exc.code}: {error_body[:400]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"AI request failed: {exc.reason}") from exc

    response_json = json.loads(body)
    content = (
        response_json.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    if not content:
        raise RuntimeError("AI returned an empty response.")

    json_block = _extract_json_block(content)
    parsed = json.loads(json_block)
    table = _payload_to_dataframe(parsed)
    if table.empty:
        raise RuntimeError("AI returned an empty table.")

    return table, {
        "mode": "ai",
        "provider": "ichenfu-openai-compatible",
        "baseUrl": config["base_url"],
        "model": config["model"],
        "endpoint": endpoint,
    }


def _chunk_text_for_ai(text: str, max_chars: int = 1200) -> list[str]:
    normalized = str(text or "").strip()
    if not normalized:
        return []

    parts = re.split(r"(?<=[。；;\n])", normalized)
    chunks: list[str] = []
    current = ""
    for part in parts:
        piece = part.strip()
        if not piece:
            continue
        if current and len(current) + len(piece) > max_chars:
            chunks.append(current.strip())
            current = piece
        else:
            current = f"{current}{piece}"
    if current.strip():
        chunks.append(current.strip())
    return chunks or [normalized]


def extract_structured_table_with_ai(text: str, source_name: str = "") -> tuple[pd.DataFrame, dict[str, Any]]:
    normalized_text = str(text or "").strip()
    if not normalized_text:
        raise ValueError("Empty text cannot be sent to AI extraction.")

    config = load_ai_config()
    if not config["enabled"]:
        raise RuntimeError("AI extraction is not configured.")

    cache_key = _cache_key(normalized_text, source_name, config)
    cached = _read_cached_table(cache_key)
    if cached is not None:
        return cached

    try:
        table, meta = _request_ai_table_once(normalized_text, source_name, config)
        _write_cached_table(cache_key, table, meta)
        return table, meta
    except Exception as first_error:
        chunks = _chunk_text_for_ai(normalized_text)
        if len(chunks) <= 1:
            raise first_error

        frames: list[tuple[int, pd.DataFrame]] = []
        max_workers = min(config["max_workers"], len(chunks))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(_request_ai_table_once, chunk, f"{source_name} chunk {index}", config): index
                for index, chunk in enumerate(chunks, start=1)
            }
            for future in as_completed(future_map):
                index = future_map[future]
                try:
                    table, _ = future.result()
                except Exception:
                    continue
                if not table.empty:
                    frames.append((index, table))

        if not frames:
            raise first_error

        merged = pd.concat([table for _, table in sorted(frames, key=lambda item: item[0])], ignore_index=True, sort=False)
        meta = {
            "mode": "ai",
            "provider": "ichenfu-openai-compatible",
            "baseUrl": config["base_url"],
            "model": config["model"],
            "endpoint": f"{config['base_url']}/chat/completions",
            "chunked": True,
            "chunkCount": len(chunks),
        }
        _write_cached_table(cache_key, merged, meta)
        return merged, meta
