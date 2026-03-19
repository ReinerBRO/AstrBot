from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Generator

import requests

from watcher.api_client import VLClient, _extract_json_payload, _normalize_spaces
from watcher.report_parser import ReportEntry


@dataclass(frozen=True)
class TimeRange:
    start: str
    end: str


@dataclass(frozen=True)
class CategoryStats:
    count: int
    percentage: int
    duration_min: int


@dataclass(frozen=True)
class DailyStats:
    total_entries: int
    time_range: TimeRange
    active_duration_min: int
    categories: dict[str, CategoryStats]


@dataclass(frozen=True)
class TimelineSegment:
    start: str
    end: str
    main_category: str
    description: str


@dataclass(frozen=True)
class SummaryResult:
    summary: str
    highlights: list[str]


def _parse_minutes(time_text: str) -> int | None:
    text = str(time_text or "").strip()
    if len(text) != 5 or ":" not in text:
        return None
    hour_text, minute_text = text.split(":", 1)
    try:
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _minute_gap(prev_time: str, next_time: str) -> int:
    prev_minute = _parse_minutes(prev_time)
    next_minute = _parse_minutes(next_time)
    if prev_minute is None or next_minute is None:
        return 5
    if next_minute >= prev_minute:
        return max(1, next_minute - prev_minute)
    return max(1, next_minute + 24 * 60 - prev_minute)


def _sorted_entries(entries: list[ReportEntry]) -> list[ReportEntry]:
    indexed = []
    for index, entry in enumerate(entries):
        minute = _parse_minutes(entry.time)
        if minute is None:
            continue
        indexed.append((minute, index, entry))
    indexed.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in indexed]


def _estimate_entry_durations(entries: list[ReportEntry]) -> list[int]:
    if not entries:
        return []
    durations: list[int] = []
    for index, entry in enumerate(entries):
        if index + 1 < len(entries):
            gap = _minute_gap(entry.time, entries[index + 1].time)
        else:
            gap = 5
        durations.append(max(1, gap))
    return durations


def aggregate_stats(entries: list[ReportEntry]) -> DailyStats:
    ordered = _sorted_entries(entries)
    if not ordered:
        return DailyStats(
            total_entries=0,
            time_range=TimeRange(start="--:--", end="--:--"),
            active_duration_min=0,
            categories={},
        )

    durations = _estimate_entry_durations(ordered)
    counts: dict[str, int] = {}
    duration_by_category: dict[str, int] = {}

    for entry, duration in zip(ordered, durations):
        category = entry.category or "未分类"
        counts[category] = counts.get(category, 0) + 1
        duration_by_category[category] = (
            duration_by_category.get(category, 0) + duration
        )

    total_entries = len(ordered)
    category_stats: dict[str, CategoryStats] = {}
    for category, count in sorted(
        counts.items(), key=lambda item: item[1], reverse=True
    ):
        percentage = int(round((count * 100) / total_entries)) if total_entries else 0
        category_stats[category] = CategoryStats(
            count=count,
            percentage=percentage,
            duration_min=duration_by_category.get(category, 0),
        )

    return DailyStats(
        total_entries=total_entries,
        time_range=TimeRange(start=ordered[0].time, end=ordered[-1].time),
        active_duration_min=sum(durations),
        categories=category_stats,
    )


def _segment_description(segment_entries: list[ReportEntry], main_category: str) -> str:
    summaries: list[str] = []
    for entry in segment_entries:
        text = str(entry.summary or "").strip()
        if text and text not in summaries:
            summaries.append(text)
        if len(summaries) >= 2:
            break
    if not summaries:
        return f"主要进行{main_category}相关活动"
    if len(summaries) == 1:
        return summaries[0]
    return f"{summaries[0]}；{summaries[1]}"


def build_timeline_segments(entries: list[ReportEntry]) -> list[TimelineSegment]:
    ordered = _sorted_entries(entries)
    if not ordered:
        return []

    segments: list[TimelineSegment] = []
    start_index = 0

    def flush(end_index: int) -> None:
        segment_rows = ordered[start_index : end_index + 1]
        if not segment_rows:
            return
        main_category = segment_rows[0].category or "未分类"
        segments.append(
            TimelineSegment(
                start=segment_rows[0].time,
                end=segment_rows[-1].time,
                main_category=main_category,
                description=_segment_description(segment_rows, main_category),
            )
        )

    for index in range(1, len(ordered)):
        prev = ordered[index - 1]
        curr = ordered[index]
        gap = _minute_gap(prev.time, curr.time)
        category_changed = (curr.category or "未分类") != (prev.category or "未分类")
        if category_changed or gap > 30:
            flush(index - 1)
            start_index = index

    flush(len(ordered) - 1)
    return segments


def _fallback_summary(stats: DailyStats) -> str:
    if stats.total_entries <= 0:
        return "当天没有可用于总结的活动记录。"

    top_categories = sorted(
        stats.categories.items(),
        key=lambda item: (item[1].count, item[1].duration_min),
        reverse=True,
    )[:2]
    if top_categories:
        category_text = "、".join(
            f"{name}({value.count}条)" for name, value in top_categories
        )
    else:
        category_text = "无"

    return (
        f"今天共记录{stats.total_entries}条活动，时间范围{stats.time_range.start}-{stats.time_range.end}，"
        f"估算活跃{stats.active_duration_min}分钟。主要活动集中在{category_text}。"
    )


def _fallback_highlights(entries: list[ReportEntry], limit: int = 5) -> list[str]:
    highlights: list[str] = []
    for entry in entries:
        text = str(entry.summary or "").strip()
        if not text or text in highlights:
            continue
        highlights.append(text)
        if len(highlights) >= limit:
            break
    return highlights


def _normalize_highlights(raw: Any) -> list[str]:
    if isinstance(raw, list):
        values = [str(item).strip() for item in raw]
    elif isinstance(raw, str):
        values = [line.strip("- •\t ") for line in raw.splitlines()]
    else:
        values = []

    output: list[str] = []
    for item in values:
        text = str(item or "").strip()
        if not text or text in output:
            continue
        output.append(text)
        if len(output) >= 5:
            break
    return output


def _build_json_summary_messages(
    ordered_entries: list[ReportEntry], stats: DailyStats
) -> list[dict[str, str]]:
    stats_payload = asdict(stats)
    entry_lines = [
        f"- {entry.time} [{entry.category}] {entry.summary}"
        for entry in ordered_entries[:120]
    ]
    return [
        {
            "role": "system",
            "content": (
                "你是工作日志助手。请根据以下一天的活动记录生成日报总结。"
                "要求："
                "1. summary：用2-3句话概括今天的主要工作和活动；"
                "2. highlights：提取3-5条关键活动亮点；"
                '严格输出JSON：{"summary":"...","highlights":["..."]}。'
            ),
        },
        {
            "role": "user",
            "content": (
                f"统计数据（JSON）：{json.dumps(stats_payload, ensure_ascii=False)}\n"
                "活动记录：\n" + "\n".join(entry_lines)
            ),
        },
    ]


def _build_stream_summary_messages(
    ordered_entries: list[ReportEntry], stats: DailyStats
) -> list[dict[str, str]]:
    stats_payload = asdict(stats)
    entry_lines = [
        f"- {entry.time} [{entry.category}] {entry.summary}"
        for entry in ordered_entries[:120]
    ]
    return [
        {
            "role": "system",
            "content": (
                "你是工作日志助手。请根据以下一天的活动记录生成简洁日报。"
                "要求：2-3句话、中文、客观准确、不使用Markdown。"
                "只输出正文，不要额外解释。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"统计数据（JSON）：{json.dumps(stats_payload, ensure_ascii=False)}\n"
                "活动记录：\n" + "\n".join(entry_lines)
            ),
        },
    ]


def _resolve_daily_summary_model(config: Any) -> str:
    return str(
        getattr(config, "daily_summary_model", "")
        or getattr(config, "vl_model", "gpt-4o-mini")
    )


def _resolve_daily_summary_max_tokens(config: Any) -> int:
    max_tokens = int(getattr(config, "daily_summary_max_tokens", 1024))
    return max(128, max_tokens)


def _extract_chat_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    message = first.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    delta = first.get("delta")
    if isinstance(delta, dict):
        content = delta.get("content")
        if isinstance(content, str):
            return content
    return ""


def _extract_stream_tokens(payload: dict[str, Any]) -> list[str]:
    choices = payload.get("choices")
    if not isinstance(choices, list):
        return []

    tokens: list[str] = []
    for row in choices:
        if not isinstance(row, dict):
            continue
        delta = row.get("delta")
        if not isinstance(delta, dict):
            continue
        content = delta.get("content")
        if isinstance(content, str):
            if content:
                tokens.append(content)
            continue
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                tokens.append(text)
    return tokens


def _summary_result_from_raw_text(
    raw_text: str,
    fallback_summary: str,
    fallback_highlights: list[str],
) -> SummaryResult:
    payload = _extract_json_payload(raw_text) if isinstance(raw_text, str) else None
    if isinstance(payload, dict):
        summary = _normalize_spaces(str(payload.get("summary") or ""))
        highlights = _normalize_highlights(payload.get("highlights"))
    else:
        summary = _normalize_spaces(str(raw_text or ""))
        highlights = []

    if not summary:
        summary = fallback_summary

    if len(highlights) < 3:
        for item in fallback_highlights:
            if item not in highlights:
                highlights.append(item)
            if len(highlights) >= 5:
                break

    return SummaryResult(summary=summary, highlights=highlights[:5])


def generate_llm_summary(
    entries: list[ReportEntry], stats: DailyStats, config: Any
) -> SummaryResult:
    ordered = _sorted_entries(entries)
    if not ordered:
        return SummaryResult(summary=_fallback_summary(stats), highlights=[])

    messages = _build_json_summary_messages(ordered, stats)
    fallback_summary = _fallback_summary(stats)
    fallback_highlights = _fallback_highlights(ordered)
    model = _resolve_daily_summary_model(config)
    max_tokens = _resolve_daily_summary_max_tokens(config)

    try:
        client = VLClient(config)
        client.max_tokens = max_tokens
        raw_text = client._chat_openai(messages, model)
    except Exception:
        raw_text = ""

    return _summary_result_from_raw_text(
        raw_text, fallback_summary, fallback_highlights
    )


def stream_llm_summary(
    entries: list[ReportEntry], stats: DailyStats, config: Any
) -> Generator[str, None, SummaryResult]:
    ordered = _sorted_entries(entries)
    fallback_summary = _fallback_summary(stats)
    fallback_highlights = _fallback_highlights(ordered)
    if not ordered:
        return SummaryResult(summary=fallback_summary, highlights=[])

    model = _resolve_daily_summary_model(config)
    max_tokens = _resolve_daily_summary_max_tokens(config)
    timeout = float(getattr(config, "api_timeout_s", 30.0) or 30.0)
    messages = _build_stream_summary_messages(ordered, stats)

    url = str(getattr(config, "api_url", "") or "").strip()
    if url.rstrip("/").endswith("/v1"):
        url = url.rstrip("/") + "/chat/completions"
    headers = {"Content-Type": "application/json"}
    api_key = getattr(config, "api_key", None)
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "stream": True,
    }

    streamed_text_parts: list[str] = []
    try:
        with requests.post(
            url,
            data=json.dumps(payload, ensure_ascii=False),
            headers=headers,
            timeout=timeout,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            fallback_chunks: list[str] = []
            for raw_line in resp.iter_lines(decode_unicode=True):
                line = str(raw_line or "").strip()
                if not line:
                    continue
                if not line.startswith("data:"):
                    fallback_chunks.append(line)
                    continue
                data_text = line[5:].strip()
                if not data_text:
                    continue
                if data_text == "[DONE]":
                    break
                try:
                    event_payload = json.loads(data_text)
                except json.JSONDecodeError:
                    fallback_chunks.append(data_text)
                    continue
                tokens = _extract_stream_tokens(event_payload)
                if tokens:
                    for token in tokens:
                        streamed_text_parts.append(token)
                        yield token
                    continue
                content = _extract_chat_content(event_payload)
                if content:
                    fallback_chunks.append(content)

            if streamed_text_parts:
                raw_output = "".join(streamed_text_parts)
                return _summary_result_from_raw_text(
                    raw_output, fallback_summary, fallback_highlights
                )

            if fallback_chunks:
                plain_output = "\n".join(fallback_chunks)
                result = _summary_result_from_raw_text(
                    plain_output, fallback_summary, fallback_highlights
                )
                if result.summary:
                    yield result.summary
                return result
    except Exception:
        pass

    # Streaming unavailable: fall back to non-stream generation and emit a single chunk.
    try:
        client = VLClient(config)
        client.max_tokens = max_tokens
        raw_output = client._chat_openai(
            _build_json_summary_messages(ordered, stats), model
        )
    except Exception:
        raw_output = ""

    result = _summary_result_from_raw_text(
        raw_output, fallback_summary, fallback_highlights
    )
    if result.summary:
        yield result.summary
    return result


def summary_cache_path(date_str: str, report_dir: str) -> Path:
    normalized_date = date.fromisoformat(str(date_str)).isoformat()
    return Path(report_dir) / f"{normalized_date}.summary.json"


def load_summary_cache(date_str: str, report_dir: str) -> dict[str, Any] | None:
    path = summary_cache_path(date_str, report_dir)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def save_summary_cache(date_str: str, report_dir: str, payload: dict[str, Any]) -> None:
    path = summary_cache_path(date_str, report_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
