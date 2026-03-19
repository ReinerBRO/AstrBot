import json
import threading
from datetime import datetime
from pathlib import Path
from queue import Empty, Queue

from watcher.event_source.models import ClickEvent, WindowInfo


class EventLogger:
    def __init__(self, log_dir: Path):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._queue: Queue[dict | None] = Queue(maxsize=4096)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._closed = threading.Event()
        self._thread.start()

    def log_event(self, event: ClickEvent, window: WindowInfo) -> None:
        if self._closed.is_set():
            return
        payload = {
            "ts": event.ts,
            "kind": "click",
            "x": event.x,
            "y": event.y,
            "button": event.button,
            "app_name": window.app_name,
            "window_title": window.window_title,
            "bundle_id": window.bundle_id,
        }
        try:
            self._queue.put_nowait(payload)
        except Exception:
            # Drop when queue is full to avoid blocking watcher loop.
            return

    def flush(self) -> None:
        self._queue.join()

    def close(self) -> None:
        if self._closed.is_set():
            return
        # Drain queued events first, then send sentinel to stop worker.
        self.flush()
        self._closed.set()
        try:
            self._queue.put(None, timeout=1.0)
        except Exception:
            return
        self._thread.join(timeout=1.5)

    def _run(self) -> None:
        while True:
            try:
                payload = self._queue.get(timeout=0.5)
            except Empty:
                if self._closed.is_set():
                    break
                continue
            if payload is None:
                self._queue.task_done()
                break
            try:
                ts_raw = payload.get("ts")
                try:
                    ts = float(ts_raw)
                except Exception:
                    ts = datetime.now().timestamp()
                date_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                path = self.log_dir / f"click-events-{date_str}.jsonl"
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
            finally:
                self._queue.task_done()
