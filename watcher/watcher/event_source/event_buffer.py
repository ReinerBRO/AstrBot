import re
import threading
import time
from collections import Counter, deque

from watcher.event_source.models import AggregatedFeatures, ClickEvent, WindowInfo

WINDOW_STOP_WORDS = {
    "",
    "new",
    "tab",
    "untitled",
    "window",
    "google",
    "chrome",
    "safari",
    "edge",
    "electron",
    "visual",
    "studio",
    "code",
    "vscode",
    "settings",
    "system",
}


class EventBuffer:
    def __init__(self, window_seconds: int = 300):
        self.window_seconds = max(int(window_seconds), 30)
        self._events: deque[tuple[ClickEvent, WindowInfo]] = deque()
        self._lock = threading.Lock()

    def add_click(self, event: ClickEvent, window: WindowInfo) -> None:
        with self._lock:
            self._events.append((event, window))
            self._drop_older_than(event.ts - self.window_seconds)

    def get_aggregated_features(
        self, start_time: float, end_time: float
    ) -> AggregatedFeatures:
        if end_time < start_time:
            start_time, end_time = end_time, start_time

        with self._lock:
            rows = [
                (event, window)
                for event, window in self._events
                if start_time <= event.ts <= end_time
            ]

        if not rows:
            return AggregatedFeatures(start_time=start_time, end_time=end_time)

        rows.sort(key=lambda item: item[0].ts)
        clicks = len(rows)
        app_counter: Counter[str] = Counter()
        keyword_counter: Counter[str] = Counter()
        app_switch_count = 0
        last_app = None

        active_seconds = 0.0
        for idx in range(1, len(rows)):
            prev_ts = rows[idx - 1][0].ts
            ts = rows[idx][0].ts
            active_seconds += min(30.0, max(0.0, ts - prev_ts))

        for _event, window in rows:
            app_name = (window.app_name or "Unknown").strip() or "Unknown"
            app_counter[app_name] += 1
            if last_app is not None and app_name != last_app:
                app_switch_count += 1
            last_app = app_name

            for token in self._extract_keywords(window.window_title):
                keyword_counter[token] += 1

        top_app = app_counter.most_common(1)[0][0] if app_counter else "Unknown"
        top_keywords = [token for token, _ in keyword_counter.most_common(8)]
        return AggregatedFeatures(
            start_time=start_time,
            end_time=end_time,
            click_count=clicks,
            app_switch_count=app_switch_count,
            active_seconds=active_seconds,
            top_app=top_app,
            top_window_keywords=top_keywords,
            app_distribution=dict(app_counter),
        )

    def get_recent_apps(self, limit: int = 5) -> list[str]:
        cap = max(1, min(int(limit), 20))
        now = time.time()
        with self._lock:
            rows = [
                window.app_name
                for event, window in self._events
                if event.ts >= now - self.window_seconds
            ]
        if not rows:
            return []
        counter: Counter[str] = Counter(app.strip() or "Unknown" for app in rows)
        return [name for name, _ in counter.most_common(cap)]

    def clear_old_events(self, before_time: float) -> None:
        with self._lock:
            self._drop_older_than(before_time)

    def _drop_older_than(self, before_time: float) -> None:
        while self._events and self._events[0][0].ts < before_time:
            self._events.popleft()

    @staticmethod
    def _extract_keywords(window_title: str) -> list[str]:
        text = (window_title or "").strip().lower()
        if not text:
            return []
        tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]{2,}", text)
        output: list[str] = []
        for token in tokens:
            if token in WINDOW_STOP_WORDS:
                continue
            if token.isdigit():
                continue
            output.append(token)
        return output
