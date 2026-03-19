import json
import re
import threading
from dataclasses import asdict
from datetime import date, datetime, time, timedelta
from io import StringIO
from pathlib import Path
from typing import Any
from uuid import uuid4
import csv
import base64

from watcher.config import load_config
from watcher.event_source.click_listener import check_accessibility_permission
from watcher.capture import get_available_monitors, capture_monitor, to_jpeg_bytes
from watcher.daily_summary import (
    aggregate_stats,
    build_timeline_segments,
    generate_llm_summary,
    load_summary_cache,
    save_summary_cache,
    stream_llm_summary,
)
from watcher.report_parser import ReportEntry, parse_daily_report

REPORT_LINE_RE = re.compile(
    r"^- (?P<time>\d{2}:\d{2}) \[(?P<category>[^\]]+)\](?: \{tree:(?P<tree_id>[^}]+)\})? (?P<summary>.*)$"
)
CARD_ID_RE = re.compile(r"^(?P<date>\d{8})-(?P<hhmm>\d{4})-(?P<seq>\d{3,6})$")


def _parse_hhmm(text: str, fallback: time) -> time:
    if not text:
        return fallback
    try:
        return time.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("time format must be HH:MM") from exc


def _parse_interval(text: Any, fallback: int) -> int:
    if text in (None, ""):
        return fallback
    try:
        value = int(text)
    except (TypeError, ValueError) as exc:
        raise ValueError("interval_s must be integer seconds") from exc
    return max(5, min(value, 3600))


def _parse_categories(raw: Any, fallback: tuple[str, ...]) -> tuple[str, ...]:
    if raw in (None, ""):
        return fallback
    if isinstance(raw, str):
        parts = [part.strip() for part in raw.split(",")]
    elif isinstance(raw, list):
        parts = [str(part).strip() for part in raw]
    else:
        raise ValueError("categories must be comma-separated string or list")
    categories = [part for part in parts if part]
    if not categories:
        return fallback
    unique: list[str] = []
    for category in categories:
        if category not in unique:
            unique.append(category)
    return tuple(unique[:8])


def _validate_date_or_today(text: str | None) -> str:
    if not text:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError as exc:
        raise ValueError("date must be YYYY-MM-DD") from exc


def _hhmm_to_minutes(value: str) -> int:
    hour_text, minute_text = value.split(":")
    return int(hour_text) * 60 + int(minute_text)


def _minutes_to_hhmm(value: int) -> str:
    normalized = value % (24 * 60)
    hour = normalized // 60
    minute = normalized % 60
    return f"{hour:02d}:{minute:02d}"


def _normalize_category(value: str, categories: tuple[str, ...]) -> str:
    if not categories:
        return "写代码"
    text = (value or "").strip().lower()
    if not text:
        return categories[0]
    for category in categories:
        if text == category.lower():
            return category
    alias = {
        "work": "写代码",
        "coding": "写代码",
        "code": "写代码",
        "study": "研究",
        "research": "研究",
        "other": "娱乐",
        "fun": "娱乐",
        "entertainment": "娱乐",
    }
    mapped = alias.get(text)
    if mapped and mapped in categories:
        return mapped
    return categories[0]


def _parse_tree_name(name: Any, fallback: str) -> str:
    text = str(name or "").strip()
    if not text:
        return fallback
    return text[:48]


def _resolve_category_value(value: str, categories: tuple[str, ...]) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    lower = text.lower()
    for category in categories:
        if lower == category.lower():
            return category
    alias = {
        "work": "写代码",
        "coding": "写代码",
        "code": "写代码",
        "study": "研究",
        "research": "研究",
        "other": "娱乐",
        "fun": "娱乐",
        "entertainment": "娱乐",
    }
    mapped = alias.get(lower)
    if mapped and mapped in categories:
        return mapped
    return None


def _parse_card_id(card_id: str) -> tuple[str, str, int]:
    raw = (card_id or "").strip()
    match = CARD_ID_RE.match(raw)
    if not match:
        raise ValueError("card_id format invalid")
    date_raw = match.group("date")
    hhmm = match.group("hhmm")
    seq = int(match.group("seq"))
    try:
        parsed_date = datetime.strptime(date_raw, "%Y%m%d").date().isoformat()
    except ValueError as exc:
        raise ValueError("card_id date invalid") from exc
    return parsed_date, hhmm, seq


def _parse_filters_list(raw: Any) -> list[str]:
    if raw in (None, ""):
        return []
    if isinstance(raw, str):
        return [item.strip() for item in raw.split(",") if item.strip()]
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [str(raw).strip()] if str(raw).strip() else []


def _split_summary_meta(text: str) -> tuple[str, dict[str, str], str]:
    summary = (text or "").strip()
    marker = " (source="
    index = summary.rfind(marker)
    if index < 0 or not summary.endswith(")"):
        return summary, {}, ""
    meta_suffix = summary[index:]
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
        return summary, {}, ""
    return summary[:index].rstrip(), meta, meta_suffix


def _normalize_source(meta: dict[str, str]) -> str:
    source = meta.get("source", "vl").strip().lower()
    if source == "fusion":
        return "vl+event"
    if source in {"vl", "event", "vl+event"}:
        return source
    return "vl"


def _extract_confidence(meta: dict[str, str]) -> float:
    raw_conf = meta.get("confidence", "").strip()
    if raw_conf:
        try:
            value = float(raw_conf)
            return max(0.0, min(1.0, value))
        except ValueError:
            pass
    reason = meta.get("reason", "")
    for token in re.findall(r"\b(?:0(?:\.\d+)?|1(?:\.0+)?)\b", reason):
        try:
            value = float(token)
        except ValueError:
            continue
        return max(0.0, min(1.0, value))
    return 0.0


def _date_span(start_date: date, end_date: date) -> list[str]:
    begin, end = (
        (start_date, end_date) if start_date <= end_date else (end_date, start_date)
    )
    values: list[str] = []
    current = begin
    while current <= end:
        values.append(current.isoformat())
        current += timedelta(days=1)
    return values


def _parse_event_ts(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return None


class WatcherService:
    def __init__(self):
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._stop_event = None
        self._watcher: Any = None
        self._config = load_config()

    @staticmethod
    def _watcher_cls():
        from watcher.runner import Watcher

        return Watcher

    @staticmethod
    def _meta_path(config: Any, date_str: str) -> Path:
        return Path(config.report_dir) / f"{date_str}.trees.json"

    @staticmethod
    def _event_log_path(config: Any, date_str: str) -> Path:
        return Path(config.event_log_dir) / f"click-events-{date_str}.jsonl"

    @staticmethod
    def _summary_path(config: Any, date_str: str) -> Path:
        return Path(config.report_dir) / f"{date_str}.summary.json"

    def _fallback_event_source_status(self, config: Any) -> dict:
        return {
            "enabled": bool(config.enable_event_source),
            "listener_running": False,
            "permission_granted": check_accessibility_permission(),
            "recent_apps": self._fallback_recent_apps(config, limit=5),
        }

    def _fallback_recent_apps(self, config: Any, limit: int = 5) -> list[str]:
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = self._event_log_path(config, date_str)
        if not path.exists():
            return []
        rows = path.read_text(encoding="utf-8").splitlines()[-800:]
        counter: dict[str, int] = {}
        for raw in rows:
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            app_name = str(payload.get("app_name", "")).strip() or "Unknown"
            counter[app_name] = counter.get(app_name, 0) + 1
        pairs = sorted(counter.items(), key=lambda item: item[1], reverse=True)
        return [name for name, _ in pairs[: max(1, min(limit, 20))]]

    def _fallback_event_source_summary(self, config: Any) -> dict:
        now_ts = datetime.now().timestamp()
        start_ts = now_ts - config.event_buffer_window_s
        date_str = datetime.now().strftime("%Y-%m-%d")
        path = self._event_log_path(config, date_str)
        if not path.exists():
            return {
                "click_count": 0,
                "app_switch_count": 0,
                "active_seconds": 0.0,
                "top_app": "Unknown",
                "top_keywords": [],
            }

        click_count = 0
        app_switch_count = 0
        top_app = "Unknown"
        app_counter: dict[str, int] = {}
        keyword_counter: dict[str, int] = {}
        first_ts = None
        last_ts = None
        last_app = None

        for raw in path.read_text(encoding="utf-8").splitlines()[-1200:]:
            try:
                payload = json.loads(raw)
            except Exception:
                continue
            event_ts = _parse_event_ts(payload.get("ts"))
            if event_ts is None or event_ts < start_ts or event_ts > now_ts:
                continue
            kind = str(payload.get("kind", "")).strip().lower() or "click"
            app_name = str(payload.get("app_name", "")).strip() or "Unknown"
            if kind == "switch":
                app_switch_count += 1
            if kind == "click":
                click_count += 1
                app_counter[app_name] = app_counter.get(app_name, 0) + 1
                window_title = str(payload.get("window_title", "")).lower()
                for token in re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]{2,}", window_title):
                    if token in {"new", "tab", "untitled", "window", "settings"}:
                        continue
                    keyword_counter[token] = keyword_counter.get(token, 0) + 1
                if last_app is not None and app_name != last_app:
                    app_switch_count += 1
                last_app = app_name
                if first_ts is None or event_ts < first_ts:
                    first_ts = event_ts
                if last_ts is None or event_ts > last_ts:
                    last_ts = event_ts

        if app_counter:
            top_app = max(app_counter, key=app_counter.get)
        active_seconds = 0.0
        if first_ts is not None and last_ts is not None:
            active_seconds = max(
                0.0, min(last_ts - first_ts, config.event_buffer_window_s)
            )
        top_keywords = [
            token
            for token, _ in sorted(
                keyword_counter.items(), key=lambda item: item[1], reverse=True
            )[:5]
        ]
        return {
            "click_count": click_count,
            "app_switch_count": app_switch_count,
            "active_seconds": round(active_seconds, 2),
            "top_app": top_app,
            "top_keywords": top_keywords,
        }

    def _read_tree_meta(self, config: Any, date_str: str) -> list[dict]:
        path = self._meta_path(config, date_str)
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        trees = payload.get("trees")
        if not isinstance(trees, list):
            return []
        rows: list[dict] = []
        for item in trees:
            if not isinstance(item, dict):
                continue
            tree_id = str(item.get("id", "")).strip()
            if not tree_id:
                continue
            rows.append(
                {
                    "id": tree_id,
                    "name": _parse_tree_name(item.get("name"), tree_id),
                    "created_at": str(item.get("created_at", "")).strip(),
                    "deleted": bool(item.get("deleted", False)),
                }
            )
        return rows

    def _write_tree_meta(self, config: Any, date_str: str, trees: list[dict]) -> None:
        path = self._meta_path(config, date_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"trees": trees}
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _upsert_tree_meta(
        self,
        config: Any,
        date_str: str,
        tree_id: str,
        *,
        name: str | None = None,
        deleted: bool | None = None,
    ) -> dict:
        trees = self._read_tree_meta(config, date_str)
        now_iso = datetime.now().isoformat(timespec="seconds")
        for row in trees:
            if row["id"] != tree_id:
                continue
            if name is not None:
                row["name"] = _parse_tree_name(name, row["name"])
            if deleted is not None:
                row["deleted"] = bool(deleted)
            if not row.get("created_at"):
                row["created_at"] = now_iso
            self._write_tree_meta(config, date_str, trees)
            return row

        created = {
            "id": tree_id,
            "name": _parse_tree_name(name, f"Tree {datetime.now().strftime('%H:%M')}"),
            "created_at": now_iso,
            "deleted": bool(deleted) if deleted is not None else False,
        }
        trees.append(created)
        self._write_tree_meta(config, date_str, trees)
        return created

    def _new_tree(self, config: Any, date_str: str, name: str | None = None) -> dict:
        tree_id = f"tree-{datetime.now().strftime('%H%M%S')}-{uuid4().hex[:6]}"
        fallback_name = f"Tree {datetime.now().strftime('%H:%M')}"
        return self._upsert_tree_meta(
            config, date_str, tree_id, name=_parse_tree_name(name, fallback_name)
        )

    def _read_entries_for_date(self, config: Any, date_str: str) -> list[dict]:
        report_path = Path(config.report_dir) / f"{date_str}.md"
        if not report_path.exists():
            return []

        parsed: list[dict] = []
        for line_index, raw_line in enumerate(
            report_path.read_text(encoding="utf-8").splitlines()
        ):
            line = raw_line.strip()
            if not line.startswith("- "):
                continue
            match = REPORT_LINE_RE.match(line)
            if match:
                time_text = match.group("time")
                category = (match.group("category") or "").strip() or "写代码"
                summary = (match.group("summary") or "").strip()
                tree_id = (match.group("tree_id") or "").strip() or None
            else:
                content = line[2:].strip()
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    continue
                time_text = parts[0]
                rest = parts[1]
                category = "写代码"
                summary = rest
                if rest.startswith("[") and "]" in rest:
                    end = rest.find("]")
                    category = rest[1:end].strip() or "写代码"
                    summary = rest[end + 1 :].strip()
                tree_id = None

            try:
                minute = _hhmm_to_minutes(time_text)
            except Exception:
                continue

            parsed.append(
                {
                    "time": time_text,
                    "minute": minute,
                    "category": _normalize_category(category, config.task_categories),
                    "summary": summary,
                    "tree_id": tree_id,
                    "_order": line_index,
                }
            )
        parsed.sort(key=lambda item: (item["minute"], item["_order"]))
        return parsed

    @staticmethod
    def _group_entries(
        entries: list[dict],
    ) -> tuple[list[dict], dict[str, list[dict]]]:
        groups: dict[str, list[dict]] = {}
        auto_index = 0
        auto_tree_id: str | None = None
        last_auto_minute: int | None = None
        last_explicit_tree: str | None = None
        tree_first_order: dict[str, int] = {}

        for entry in entries:
            tree_id = entry.get("tree_id")
            if tree_id:
                last_explicit_tree = tree_id
            else:
                current_minute = entry["minute"]
                if last_explicit_tree and last_auto_minute is not None:
                    if current_minute - last_auto_minute <= 20:
                        tree_id = last_explicit_tree
                    else:
                        last_explicit_tree = None
                if not tree_id:
                    if (
                        auto_tree_id is None
                        or last_auto_minute is None
                        or current_minute - last_auto_minute > 45
                    ):
                        auto_index += 1
                        auto_tree_id = f"auto-{auto_index}"
                    tree_id = auto_tree_id
                last_auto_minute = current_minute

            entry["tree_id"] = tree_id
            groups.setdefault(tree_id, []).append(entry)
            tree_first_order.setdefault(tree_id, entry["_order"])

        trees: list[dict] = []
        for tree_id, rows in groups.items():
            rows.sort(key=lambda item: (item["minute"], item["_order"]))
            start_minute = rows[0]["minute"]
            end_minute = rows[-1]["minute"]
            categories = sorted({row["category"] for row in rows})
            tree_name = (
                f"{_minutes_to_hhmm(start_minute)} - {_minutes_to_hhmm(end_minute)}"
            )
            trees.append(
                {
                    "id": tree_id,
                    "name": tree_name,
                    "count": len(rows),
                    "start_time": _minutes_to_hhmm(start_minute),
                    "end_time": _minutes_to_hhmm(end_minute),
                    "categories": categories,
                    "_order": tree_first_order.get(tree_id, 0),
                }
            )
        trees.sort(key=lambda item: item["_order"])
        return trees, groups

    def _merge_trees(
        self, config: Any, date_str: str, inferred_trees: list[dict]
    ) -> list[dict]:
        meta_rows = self._read_tree_meta(config, date_str)
        deleted_ids = {row["id"] for row in meta_rows if row.get("deleted")}
        inferred_map = {
            row["id"]: row for row in inferred_trees if row["id"] not in deleted_ids
        }

        merged: list[dict] = []
        for index, meta in enumerate(meta_rows):
            if meta.get("deleted"):
                continue
            existing = inferred_map.pop(meta["id"], None)
            if existing:
                merged.append(
                    {
                        "id": meta["id"],
                        "name": meta["name"] or existing["name"],
                        "count": existing["count"],
                        "start_time": existing["start_time"],
                        "end_time": existing["end_time"],
                        "categories": existing["categories"],
                        "_order": index,
                    }
                )
            else:
                merged.append(
                    {
                        "id": meta["id"],
                        "name": meta["name"],
                        "count": 0,
                        "start_time": "--:--",
                        "end_time": "--:--",
                        "categories": [],
                        "_order": index,
                    }
                )

        offset = len(meta_rows)
        for add_index, item in enumerate(inferred_map.values()):
            merged.append(
                {
                    **item,
                    "_order": offset + add_index,
                }
            )

        merged.sort(key=lambda item: item["_order"])
        for row in merged:
            row.pop("_order", None)
        return merged

    @staticmethod
    def _available_dates(report_dir: str) -> list[str]:
        path = Path(report_dir)
        if not path.exists():
            return []
        values: set[str] = set()
        for item in path.iterdir():
            name = item.name
            stem = ""
            if name.endswith(".md"):
                stem = item.stem
            elif name.endswith(".trees.json"):
                stem = name[: -len(".trees.json")]
            else:
                continue
            try:
                values.add(date.fromisoformat(stem).isoformat())
            except ValueError:
                continue
        return sorted(values, reverse=True)[:180]

    def _ensure_tree(self, config: Any, date_str: str, tree_id: str) -> dict:
        trees = self._read_tree_meta(config, date_str)
        for row in trees:
            if row["id"] == tree_id and not row.get("deleted"):
                return row
        fallback = f"Tree {datetime.now().strftime('%H:%M')}"
        return self._upsert_tree_meta(
            config, date_str, tree_id, name=fallback, deleted=False
        )

    def status(self) -> dict:
        with self._lock:
            config = self._config
            watcher = self._watcher
            running = self._running
        return {
            "running": running,
            "start_time": config.start_time.isoformat(timespec="minutes"),
            "end_time": config.end_time.isoformat(timespec="minutes"),
            "interval_s": config.interval_s,
            "categories": list(config.task_categories),
            "vl_model": config.vl_model,
            "event_summary_model": config.event_summary_model,
            "fusion_summary_model": config.fusion_summary_model,
            "active_tree_id": getattr(watcher, "tree_id", None),
            "api_ready": bool(config.api_url),
        }

    def event_source_status(self) -> dict:
        with self._lock:
            config = self._config or load_config()
            watcher = self._watcher
            running = self._running

        if (
            running
            and watcher is not None
            and hasattr(watcher, "get_event_source_status")
        ):
            payload = watcher.get_event_source_status()
        else:
            payload = self._fallback_event_source_status(config)
        return {
            **payload,
            "running": running,
        }

    def event_source_summary(self) -> dict:
        with self._lock:
            config = self._config or load_config()
            watcher = self._watcher
            running = self._running

        if (
            running
            and watcher is not None
            and hasattr(watcher, "get_event_source_summary")
        ):
            payload = watcher.get_event_source_summary()
        else:
            payload = self._fallback_event_source_summary(config)
        return {
            **payload,
            "window_seconds": config.event_buffer_window_s,
        }

    def get_monitors(self) -> dict:
        """获取所有可用显示器列表"""
        try:
            monitors = get_available_monitors()
            return {
                "ok": True,
                "monitors": monitors,
                "current": self._config.monitor_index if self._config else 1,
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "monitors": [],
                "current": 1,
            }

    def get_monitor_preview(self, monitor_index: int) -> dict:
        """获取指定显示器的预览图"""
        try:
            image = capture_monitor(monitor_index)
            # 生成缩略图 (320px宽)
            jpeg_bytes = to_jpeg_bytes(image, quality=60, resize_width=320)
            base64_data = base64.b64encode(jpeg_bytes).decode("utf-8")
            return {
                "ok": True,
                "preview": f"data:image/jpeg;base64,{base64_data}",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
            }

    def update_monitor(self, monitor_index: int) -> dict:
        """更新当前使用的显示器"""
        with self._lock:
            if self._watcher and hasattr(self._watcher, "config"):
                # 如果watcher正在运行，需要重启才能应用新的显示器设置
                return {
                    "ok": False,
                    "message": "请先停止监控，再切换显示器",
                }
            # 更新环境变量（下次启动时生效）
            import os

            os.environ["MONITOR_INDEX"] = str(monitor_index)
            return {
                "ok": True,
                "message": f"已切换到显示器 {monitor_index}",
            }

    def start(
        self,
        start_time_text: str,
        end_time_text: str,
        interval_s: Any = None,
        categories: Any = None,
        tree_id: str = "",
    ) -> dict:
        with self._lock:
            if self._running:
                return {"ok": True, "message": "already running"}
            config = load_config()
            if not config.api_url:
                return {"ok": False, "message": "VL_API_URL is missing"}

            start_time = _parse_hhmm(start_time_text, config.start_time)
            end_time = _parse_hhmm(end_time_text, config.end_time)
            watch_interval_s = _parse_interval(interval_s, config.interval_s)
            task_categories = _parse_categories(categories, config.task_categories)
            today = datetime.now().strftime("%Y-%m-%d")

            if tree_id.strip():
                tree = self._ensure_tree(config, today, tree_id.strip())
            else:
                tree = self._new_tree(config, today)

            config = config.__class__(
                **{
                    **config.__dict__,
                    "start_time": start_time,
                    "end_time": end_time,
                    "interval_s": watch_interval_s,
                    "task_categories": task_categories,
                }
            )
            self._config = config
            self._stop_event = threading.Event()
            self._watcher = self._watcher_cls()(
                config, stop_event=self._stop_event, tree_id=tree["id"]
            )
            self._thread = threading.Thread(
                target=self._watcher.run_forever, daemon=True
            )
            self._thread.start()
            self._running = True
            return {
                "ok": True,
                "message": "watcher started",
                "interval_s": config.interval_s,
                "categories": list(config.task_categories),
                "tree_id": tree["id"],
            }

    def stop(self) -> dict:
        thread = None
        with self._lock:
            if not self._running:
                return {"ok": True, "message": "already stopped"}
            if self._stop_event:
                self._stop_event.set()
            thread = self._thread
            self._running = False
        if thread:
            thread.join(timeout=2)
        return {"ok": True, "message": "watcher stopped"}

    def set_preferences(self, interval_s: Any = None, categories: Any = None) -> dict:
        with self._lock:
            config = self._config or load_config()
            next_interval = _parse_interval(interval_s, config.interval_s)
            next_categories = _parse_categories(categories, config.task_categories)
            config = config.__class__(
                **{
                    **config.__dict__,
                    "interval_s": next_interval,
                    "task_categories": next_categories,
                }
            )
            self._config = config
            if self._watcher is not None:
                self._watcher.config = config
                if hasattr(self._watcher, "client"):
                    self._watcher.client.categories = config.task_categories
            running = self._running
        return {
            "ok": True,
            "message": "preferences updated",
            "interval_s": next_interval,
            "categories": list(next_categories),
            "running": running,
        }

    def create_tree(self, date_text: str = "", name: str = "") -> dict:
        with self._lock:
            config = self._config or load_config()
            date_str = _validate_date_or_today(date_text)
            tree = self._new_tree(config, date_str, name=name or None)
        return {
            "ok": True,
            "date": date_str,
            "tree": {
                "id": tree["id"],
                "name": tree["name"],
                "count": 0,
                "start_time": "--:--",
                "end_time": "--:--",
                "categories": [],
            },
        }

    def delete_tree(self, date_text: str = "", tree_id: str = "") -> dict:
        tree_id = tree_id.strip()
        if not tree_id:
            raise ValueError("tree_id is required")
        date_str = _validate_date_or_today(date_text)

        with self._lock:
            config = self._config or load_config()
            if self._running and getattr(self._watcher, "tree_id", None) == tree_id:
                return {"ok": False, "message": "cannot delete active running tree"}

            report_path = Path(config.report_dir) / f"{date_str}.md"
            if report_path.exists():
                lines = report_path.read_text(encoding="utf-8").splitlines()
                entries = self._read_entries_for_date(config, date_str)
                _, groups = self._group_entries(entries)
                target_orders = {
                    row["_order"] for row in groups.get(tree_id, []) if "_order" in row
                }
                if target_orders:
                    kept_lines = [
                        line
                        for idx, line in enumerate(lines)
                        if idx not in target_orders
                    ]
                    report_path.write_text("\n".join(kept_lines), encoding="utf-8")

            self._upsert_tree_meta(config, date_str, tree_id, deleted=True)
        return {
            "ok": True,
            "message": "tree deleted",
            "date": date_str,
            "tree_id": tree_id,
        }

    def manual_record(self, tree_id: str = "") -> dict:
        with self._lock:
            config = self._config or load_config()
            if not config.api_url:
                return {"ok": False, "message": "VL_API_URL is missing"}
            today = datetime.now().strftime("%Y-%m-%d")
            if tree_id.strip():
                tree = self._ensure_tree(config, today, tree_id.strip())
                target_tree_id = tree["id"]
            elif self._watcher is not None and getattr(self._watcher, "tree_id", None):
                target_tree_id = self._watcher.tree_id
            else:
                target_tree_id = self._new_tree(config, today)["id"]

        watcher = self._watcher_cls()(config, tree_id=target_tree_id)
        summary, category, diff, used_tree_id = watcher.run_once(force_send=True)
        if not summary:
            return {"ok": False, "message": f"no summary generated, diff={diff}"}
        return {
            "ok": True,
            "summary": summary,
            "category": category,
            "diff": diff,
            "tree_id": used_tree_id,
        }

    def tree_data(self, date_text: str = "", tree_id: str = "") -> dict:
        with self._lock:
            config = self._config

        date_str = _validate_date_or_today(date_text)
        entries = self._read_entries_for_date(config, date_str)
        inferred_trees, grouped = self._group_entries(entries)
        trees = self._merge_trees(config, date_str, inferred_trees)

        valid_ids = {row["id"] for row in trees}
        selected_tree_id = tree_id if tree_id in valid_ids else ""
        if not selected_tree_id and trees:
            selected_tree_id = trees[-1]["id"]

        selected_entries = grouped.get(selected_tree_id, []) if selected_tree_id else []
        cfg_start = config.start_time.hour * 60 + config.start_time.minute
        cfg_end = config.end_time.hour * 60 + config.end_time.minute
        if selected_entries:
            data_start = min(row["minute"] for row in selected_entries) - 20
            data_end = max(row["minute"] for row in selected_entries) + 20
            start_minute = min(data_start, cfg_start)
            end_minute = max(data_end, cfg_end)
            start_time = _minutes_to_hhmm(start_minute)
            end_time = _minutes_to_hhmm(max(end_minute, start_minute + 1))
        else:
            start_time = config.start_time.isoformat(timespec="minutes")
            end_time = config.end_time.isoformat(timespec="minutes")

        payload_entries = [
            {
                "time": row["time"],
                "category": row["category"],
                "summary": row["summary"],
                "tree_id": row["tree_id"],
            }
            for row in selected_entries
        ]

        return {
            "date": date_str,
            "date_options": self._available_dates(config.report_dir),
            "trees": trees,
            "selected_tree_id": selected_tree_id,
            "start_time": start_time,
            "end_time": end_time,
            "categories": list(config.task_categories),
            "entries": payload_entries,
        }

    def _resolve_cards_dates(
        self,
        date_text: str = "",
        date_from: str = "",
        date_to: str = "",
    ) -> list[str]:
        if date_from or date_to:
            try:
                start = date.fromisoformat(date_from or date_to)
                end = date.fromisoformat(date_to or date_from)
            except ValueError as exc:
                raise ValueError("date_from/date_to must be YYYY-MM-DD") from exc
            return _date_span(start, end)
        return [_validate_date_or_today(date_text)]

    def _tree_name_map_for_date(self, config: Any, date_str: str) -> dict[str, str]:
        names: dict[str, str] = {}
        for row in self._read_tree_meta(config, date_str):
            if row.get("deleted"):
                continue
            tree_id = row.get("id")
            tree_name = row.get("name")
            if tree_id and tree_name:
                names[str(tree_id)] = str(tree_name)

        entries = self._read_entries_for_date(config, date_str)
        inferred_trees, _ = self._group_entries(entries)
        for tree in inferred_trees:
            tree_id = str(tree.get("id", "")).strip()
            tree_name = str(tree.get("name", "")).strip()
            if tree_id and tree_name and tree_id not in names:
                names[tree_id] = tree_name
        return names

    def _collect_cards_for_date(self, config: Any, date_str: str) -> list[dict]:
        report_path = Path(config.report_dir) / f"{date_str}.md"
        if not report_path.exists():
            return []

        tree_names = self._tree_name_map_for_date(config, date_str)
        cards: list[dict] = []
        date_compact = date_str.replace("-", "")
        sequence = 0

        for line_index, raw_line in enumerate(
            report_path.read_text(encoding="utf-8").splitlines()
        ):
            line = raw_line.strip()
            if not line.startswith("- "):
                continue
            match = REPORT_LINE_RE.match(line)
            if match:
                time_text = match.group("time")
                category = (match.group("category") or "").strip() or "写代码"
                summary = (match.group("summary") or "").strip()
                tree_id = (match.group("tree_id") or "").strip() or None
            else:
                content = line[2:].strip()
                parts = content.split(" ", 1)
                if len(parts) < 2:
                    continue
                time_text = parts[0].strip()
                rest = parts[1].strip()
                category = "写代码"
                summary = rest
                tree_id = None
                if rest.startswith("[") and "]" in rest:
                    end = rest.find("]")
                    category = rest[1:end].strip() or "写代码"
                    summary = rest[end + 1 :].strip()

            try:
                _hhmm_to_minutes(time_text)
            except Exception:
                continue

            sequence += 1
            summary_text, meta, meta_suffix = _split_summary_meta(summary)
            vl_raw = (meta.get("vl") or "").strip()
            event_raw = (meta.get("event") or "").strip()
            vl_category = None
            event_category = None
            if vl_raw and vl_raw != "-":
                vl_category = (
                    _resolve_category_value(vl_raw, config.task_categories) or vl_raw
                )
            if event_raw and event_raw != "-":
                event_category = (
                    _resolve_category_value(event_raw, config.task_categories)
                    or event_raw
                )
            timestamp = datetime.strptime(
                f"{date_str} {time_text}", "%Y-%m-%d %H:%M"
            ).timestamp()

            cards.append(
                {
                    "id": f"{date_compact}-{time_text.replace(':', '')}-{sequence:03d}",
                    "time": time_text,
                    "date": date_str,
                    "category": _normalize_category(category, config.task_categories),
                    "summary": summary_text,
                    "tree_id": tree_id,
                    "tree_name": tree_names.get(tree_id or "", tree_id or ""),
                    "source": _normalize_source(meta),
                    "confidence": _extract_confidence(meta),
                    "vl_category": vl_category,
                    "event_category": event_category,
                    "event_data": {
                        "click_count": 0,
                        "top_app": "",
                        "active_seconds": 0,
                    },
                    "_line_index": line_index,
                    "_meta_suffix": meta_suffix,
                    "_ts": timestamp,
                    "_seq": sequence,
                }
            )

        return cards

    @staticmethod
    def _public_card(card: dict) -> dict:
        return {key: value for key, value in card.items() if not key.startswith("_")}

    def _cards_data_impl(
        self,
        config: Any,
        *,
        date_text: str = "",
        date_from: str = "",
        date_to: str = "",
        categories: list[str] | None = None,
        tree_ids: list[str] | None = None,
        search: str = "",
        page: int = 1,
        page_size: int = 50,
        sort: str = "time_desc",
    ) -> dict:
        try:
            page_value = int(page)
            page_size_value = int(page_size)
        except (TypeError, ValueError) as exc:
            raise ValueError("page/page_size must be integers") from exc
        if page_value < 1:
            raise ValueError("page must be >= 1")
        page_size_value = max(1, min(page_size_value, 500))

        sort_value = (sort or "time_desc").strip().lower()
        if sort_value not in {"time_desc", "time_asc"}:
            raise ValueError("sort must be time_desc or time_asc")

        date_values = self._resolve_cards_dates(
            date_text=date_text, date_from=date_from, date_to=date_to
        )
        cards: list[dict] = []
        for date_str in date_values:
            cards.extend(self._collect_cards_for_date(config, date_str))

        category_filters = _parse_filters_list(categories)
        normalized_filters: set[str] = set()
        for item in category_filters:
            resolved = _resolve_category_value(item, config.task_categories)
            if resolved:
                normalized_filters.add(resolved)
        if category_filters and not normalized_filters:
            raise ValueError("no valid categories in filter")

        tree_filter = {item for item in _parse_filters_list(tree_ids) if item}
        search_text = str(search or "").strip().lower()

        filtered: list[dict] = []
        for card in cards:
            if normalized_filters and card["category"] not in normalized_filters:
                continue
            if tree_filter and (card.get("tree_id") or "") not in tree_filter:
                continue
            if search_text:
                haystack = " ".join(
                    [
                        card.get("date", ""),
                        card.get("time", ""),
                        card.get("category", ""),
                        card.get("summary", ""),
                        card.get("tree_id") or "",
                        card.get("tree_name") or "",
                    ]
                ).lower()
                if search_text not in haystack:
                    continue
            filtered.append(card)

        filtered.sort(
            key=lambda item: (item.get("_ts", 0.0), item.get("_seq", 0)),
            reverse=(sort_value == "time_desc"),
        )

        total = len(filtered)
        start_idx = (page_value - 1) * page_size_value
        end_idx = start_idx + page_size_value
        page_cards = filtered[start_idx:end_idx]
        has_more = end_idx < total

        stats_cards = sorted(
            filtered, key=lambda item: (item.get("_ts", 0.0), item.get("_seq", 0))
        )
        category_counts: dict[str, int] = {}
        for item in stats_cards:
            category = item["category"]
            category_counts[category] = category_counts.get(category, 0) + 1

        total_active_seconds = 0
        intervals: list[int] = []
        for index in range(1, len(stats_cards)):
            delta = int(
                max(0.0, stats_cards[index]["_ts"] - stats_cards[index - 1]["_ts"])
            )
            intervals.append(delta)
            total_active_seconds += min(delta, 3600)

        avg_interval_seconds = int(sum(intervals) / len(intervals)) if intervals else 0
        if stats_cards:
            range_start = stats_cards[0]["date"]
            range_end = stats_cards[-1]["date"]
        elif date_values:
            range_start = date_values[0]
            range_end = date_values[-1]
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            range_start = today
            range_end = today

        return {
            "cards": [self._public_card(item) for item in page_cards],
            "total": total,
            "page": page_value,
            "page_size": page_size_value,
            "has_more": has_more,
            "stats": {
                "total_count": total,
                "category_counts": category_counts,
                "total_active_seconds": total_active_seconds,
                "avg_interval_seconds": avg_interval_seconds,
                "date_range": {
                    "start": range_start,
                    "end": range_end,
                },
            },
        }

    def cards_data(
        self,
        date_text: str = "",
        date_from: str = "",
        date_to: str = "",
        categories: list[str] | None = None,
        tree_ids: list[str] | None = None,
        search: str = "",
        page: int = 1,
        page_size: int = 50,
        sort: str = "time_desc",
    ) -> dict:
        with self._lock:
            config = self._config or load_config()
        return self._cards_data_impl(
            config,
            date_text=date_text,
            date_from=date_from,
            date_to=date_to,
            categories=categories,
            tree_ids=tree_ids,
            search=search,
            page=page,
            page_size=page_size,
            sort=sort,
        )

    def update_card(
        self,
        card_id: str,
        summary: str | None = None,
        category: str | None = None,
    ) -> dict:
        if summary is None and category is None:
            raise ValueError("summary or category is required")

        with self._lock:
            config = self._config or load_config()
            date_str, _, _ = _parse_card_id(card_id)
            report_path = Path(config.report_dir) / f"{date_str}.md"
            if not report_path.exists():
                raise ValueError("card not found")

            lines = report_path.read_text(encoding="utf-8").splitlines()
            cards = self._collect_cards_for_date(config, date_str)
            target = next((item for item in cards if item["id"] == card_id), None)
            if target is None:
                raise ValueError("card not found")

            next_summary = target["summary"]
            if summary is not None:
                next_summary = str(summary).strip()
                if not next_summary:
                    raise ValueError("summary cannot be empty")

            next_category = target["category"]
            if category is not None:
                resolved = _resolve_category_value(
                    str(category), config.task_categories
                )
                if not resolved:
                    raise ValueError("category not allowed")
                next_category = resolved

            tree_tag = f" {{tree:{target['tree_id']}}}" if target.get("tree_id") else ""
            updated_line = (
                f"- {target['time']} [{next_category}]{tree_tag} "
                f"{next_summary}{target.get('_meta_suffix', '')}"
            )
            line_index = target["_line_index"]
            if line_index < 0 or line_index >= len(lines):
                raise ValueError("card line out of range")
            lines[line_index] = updated_line
            report_path.write_text("\n".join(lines), encoding="utf-8")

            refreshed = self._collect_cards_for_date(config, date_str)
            updated_card = next(
                (item for item in refreshed if item["id"] == card_id), None
            )
            if updated_card is None:
                raise ValueError("card update failed")

        return {
            "ok": True,
            "message": "卡片已更新",
            "card": self._public_card(updated_card),
        }

    def delete_card(self, card_id: str) -> dict:
        with self._lock:
            config = self._config or load_config()
            date_str, _, _ = _parse_card_id(card_id)
            report_path = Path(config.report_dir) / f"{date_str}.md"
            if not report_path.exists():
                raise ValueError("card not found")

            lines = report_path.read_text(encoding="utf-8").splitlines()
            cards = self._collect_cards_for_date(config, date_str)
            target = next((item for item in cards if item["id"] == card_id), None)
            if target is None:
                raise ValueError("card not found")

            line_index = target["_line_index"]
            if line_index < 0 or line_index >= len(lines):
                raise ValueError("card line out of range")
            lines.pop(line_index)
            report_path.write_text("\n".join(lines), encoding="utf-8")

            target_tree_id = (target.get("tree_id") or "").strip()
            if target_tree_id:
                meta_rows = self._read_tree_meta(config, date_str)
                tree_exists = any(row["id"] == target_tree_id for row in meta_rows)
                if tree_exists:
                    remaining_cards = self._collect_cards_for_date(config, date_str)
                    still_used = any(
                        (item.get("tree_id") or "").strip() == target_tree_id
                        for item in remaining_cards
                    )
                    if not still_used:
                        for row in meta_rows:
                            if row["id"] == target_tree_id:
                                row["deleted"] = True
                        self._write_tree_meta(config, date_str, meta_rows)

        return {
            "ok": True,
            "message": "卡片已删除",
            "card_id": card_id,
        }

    def export_cards(
        self,
        format: str = "markdown",
        filters: dict | None = None,
    ) -> tuple[str, str]:
        with self._lock:
            config = self._config or load_config()

        payload = filters or {}
        export_format = (format or "markdown").strip().lower()
        if export_format not in {"markdown", "json", "csv"}:
            raise ValueError("format must be markdown/json/csv")

        data = self._cards_data_impl(
            config,
            date_text=str(payload.get("date", "") or ""),
            date_from=str(payload.get("date_from", "") or ""),
            date_to=str(payload.get("date_to", "") or ""),
            categories=payload.get("categories"),
            tree_ids=payload.get("tree_ids"),
            search=str(payload.get("search", "") or ""),
            page=1,
            page_size=1000000,
            sort=str(payload.get("sort", "time_desc") or "time_desc"),
        )
        cards = data["cards"]

        if export_format == "markdown":
            lines: list[str] = []
            for card in cards:
                tree_tag = f" {{tree:{card['tree_id']}}}" if card.get("tree_id") else ""
                meta_parts: list[str] = []
                source = str(card.get("source") or "vl")
                if source != "vl":
                    meta_parts.append(f"source={source}")
                if card.get("vl_category") or card.get("event_category"):
                    meta_parts.append(
                        f"vl={card.get('vl_category') or '-'}; event={card.get('event_category') or '-'}"
                    )
                confidence = float(card.get("confidence") or 0.0)
                if confidence > 0:
                    meta_parts.append(f"confidence={confidence:.2f}")
                meta = f" ({'; '.join(meta_parts)})" if meta_parts else ""
                lines.append(
                    f"- {card['date']} {card['time']} [{card['category']}]"
                    f"{tree_tag} {card['summary']}{meta}"
                )
            content = "\n".join(lines)
            ext = "md"
        elif export_format == "json":
            content = json.dumps(
                {"cards": cards, "stats": data.get("stats", {})},
                ensure_ascii=False,
                indent=2,
            )
            ext = "json"
        else:
            stream = StringIO()
            fieldnames = [
                "id",
                "date",
                "time",
                "category",
                "summary",
                "tree_id",
                "tree_name",
                "source",
                "confidence",
                "vl_category",
                "event_category",
            ]
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            for card in cards:
                writer.writerow({name: card.get(name, "") for name in fieldnames})
            content = stream.getvalue()
            ext = "csv"

        date_range = data.get("stats", {}).get("date_range", {})
        start_text = str(date_range.get("start") or datetime.now().strftime("%Y-%m-%d"))
        end_text = str(date_range.get("end") or start_text)
        filename = f"watcher-report-{start_text.replace('-', '')}-{end_text.replace('-', '')}.{ext}"
        return content, filename

    def daily_summary_cached(self, date_str: str = "") -> dict | None:
        with self._lock:
            config = self._config or load_config()
        normalized_date = _validate_date_or_today(date_str)
        return load_summary_cache(normalized_date, config.report_dir)

    def daily_summary(self, date_str: str = "", force: bool = False) -> dict:
        with self._lock:
            config = self._config or load_config()

        normalized_date = _validate_date_or_today(date_str)
        if not force:
            cached_payload = load_summary_cache(normalized_date, config.report_dir)
            if cached_payload is not None:
                return cached_payload

        entries = parse_daily_report(normalized_date, config.report_dir)
        if not entries:
            raise ValueError("no_data")

        stats = aggregate_stats(entries)
        timeline_segments = build_timeline_segments(entries)
        llm_result = generate_llm_summary(entries, stats, config)

        payload = {
            "date": normalized_date,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stats": asdict(stats),
            "timeline_segments": [asdict(item) for item in timeline_segments],
            "summary": llm_result.summary,
            "highlights": llm_result.highlights,
        }
        save_summary_cache(normalized_date, config.report_dir, payload)
        return payload

    def daily_summary_stream(self, date_str: str = "", force: bool = False):
        with self._lock:
            config = self._config or load_config()

        normalized_date = _validate_date_or_today(date_str)
        if not force:
            cached_payload = load_summary_cache(normalized_date, config.report_dir)
            if cached_payload is not None:
                yield ("cached", cached_payload)
                return

        yield (
            "phase",
            {"phase": "parsing", "message": "正在解析活动记录..."},
        )
        entries = parse_daily_report(normalized_date, config.report_dir)
        if not entries:
            raise ValueError("no_data")

        yield (
            "phase",
            {"phase": "aggregating", "message": "正在聚合统计数据..."},
        )
        stats = aggregate_stats(entries)
        timeline_segments = build_timeline_segments(entries)

        yield (
            "phase",
            {"phase": "generating", "message": "正在生成 AI 总结..."},
        )
        stream_iter = stream_llm_summary(entries, stats, config)
        llm_result = None
        while True:
            try:
                token = next(stream_iter)
            except StopIteration as stop:
                llm_result = stop.value
                break
            yield ("token", {"text": token})

        if llm_result is None:
            llm_result = generate_llm_summary(entries, stats, config)

        timeline_payload = [asdict(item) for item in timeline_segments]
        payload = {
            "date": normalized_date,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "stats": asdict(stats),
            "timeline_segments": timeline_payload,
            "summary": llm_result.summary,
            "highlights": llm_result.highlights,
        }
        save_summary_cache(normalized_date, config.report_dir, payload)

        yield ("highlights", {"highlights": llm_result.highlights})
        yield ("segments", {"timeline_segments": timeline_payload})
        yield ("done", payload)

    def logs(self, lines: int = 120, date_text: str = "") -> dict:
        with self._lock:
            config = self._config
        date_str = _validate_date_or_today(date_text)
        log_path = Path(config.log_dir) / f"{date_str}.log"
        if not log_path.exists():
            return {"lines": []}
        rows = log_path.read_text(encoding="utf-8").splitlines()
        return {"lines": rows[-max(lines, 1) :]}
