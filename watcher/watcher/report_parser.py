from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPORT_LINE_RE = re.compile(
    r"^- (?P<time>\d{2}:\d{2}) \[(?P<category>[^\]]+)\](?: \{tree:(?P<tree_id>[^}]+)\})? (?P<summary>.*)$"
)


@dataclass(frozen=True)
class ReportEntry:
    time: str
    category: str
    tree_id: str | None
    summary: str
    source: str
    meta: dict[str, str]


def _parse_hhmm_to_minutes(text: str) -> int | None:
    value = str(text or "").strip()
    if not re.fullmatch(r"\d{2}:\d{2}", value):
        return None
    hour_text, minute_text = value.split(":", 1)
    try:
        hour = int(hour_text)
        minute = int(minute_text)
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return hour * 60 + minute


def _split_summary_meta(text: str) -> tuple[str, dict[str, str]]:
    summary = str(text or "").strip()
    marker = " (source="
    index = summary.rfind(marker)
    if index < 0 or not summary.endswith(")"):
        return summary, {}

    payload = summary[index + 2 : -1]
    meta: dict[str, str] = {}
    for chunk in payload.split(";"):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            meta[key] = value

    if "source" not in meta:
        return summary, {}
    return summary[:index].rstrip(), meta


def _normalize_source(raw_source: str) -> str:
    source = str(raw_source or "vl").strip().lower()
    if source == "fusion":
        return "vl+event"
    if source in {"vl", "event", "vl+event"}:
        return source
    return "vl"


def parse_daily_report(date_str: str, report_dir: str) -> list[ReportEntry]:
    normalized_date = date.fromisoformat(str(date_str)).isoformat()
    path = Path(report_dir) / f"{normalized_date}.md"
    if not path.exists():
        return []

    parsed_rows: list[tuple[int, int, ReportEntry]] = []
    for line_index, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines()
    ):
        line = raw_line.strip()
        if not line.startswith("- "):
            continue

        match = REPORT_LINE_RE.match(line)
        if match:
            time_text = (match.group("time") or "").strip()
            category = (match.group("category") or "").strip() or "写代码"
            tree_id = (match.group("tree_id") or "").strip() or None
            summary = (match.group("summary") or "").strip()
        else:
            content = line[2:].strip()
            parts = content.split(" ", 1)
            if len(parts) < 2:
                continue
            time_text = parts[0].strip()
            rest = parts[1].strip()
            category = "写代码"
            tree_id = None
            summary = rest

            if rest.startswith("[") and "]" in rest:
                end = rest.find("]")
                category = rest[1:end].strip() or "写代码"
                summary = rest[end + 1 :].strip()

            if summary.startswith("{tree:") and "}" in summary:
                end = summary.find("}")
                tree_text = summary[len("{tree:") : end].strip()
                tree_id = tree_text or None
                summary = summary[end + 1 :].strip()

        minute = _parse_hhmm_to_minutes(time_text)
        if minute is None:
            continue

        summary_text, meta = _split_summary_meta(summary)
        source = _normalize_source(meta.get("source", "vl"))

        entry = ReportEntry(
            time=time_text,
            category=category,
            tree_id=tree_id,
            summary=summary_text,
            source=source,
            meta=meta,
        )
        parsed_rows.append((minute, line_index, entry))

    parsed_rows.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in parsed_rows]
