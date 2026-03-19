import json
import subprocess
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from watcher.event_source.click_listener import ClickListener
from watcher.event_source.event_buffer import EventBuffer
from watcher.event_source.event_logger import EventLogger
from watcher.event_source.models import ClickEvent, WindowInfo
from watcher.event_source.window_resolver import WindowResolver


class _FakeListener:
    def __init__(self, on_click):
        self.on_click = on_click
        self.running = False

    def start(self):
        self.running = True

    def stop(self):
        self.running = False

    def join(self, timeout=None):
        return None


class ClickListenerTest(unittest.TestCase):
    def test_start_stop_and_callback(self):
        captured: list[ClickEvent] = []
        fake_mouse = SimpleNamespace(Listener=_FakeListener)

        with patch(
            "watcher.event_source.click_listener.pynput_mouse",
            fake_mouse,
        ), patch(
            "watcher.event_source.click_listener.check_accessibility_permission",
            return_value=True,
        ):
            listener = ClickListener(callback=captured.append)
            self.assertTrue(listener.start())
            self.assertTrue(listener.is_running())

            assert listener._listener is not None
            listener._listener.on_click(100, 200, SimpleNamespace(name="left"), True)
            listener._listener.on_click(100, 200, SimpleNamespace(name="left"), False)

            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0].x, 100)
            self.assertEqual(captured[0].y, 200)
            self.assertEqual(captured[0].button, "left")

            listener.stop()
            self.assertFalse(listener.is_running())

    def test_start_failure_graceful(self):
        with patch(
            "watcher.event_source.click_listener.pynput_mouse",
            None,
        ):
            listener = ClickListener(callback=lambda _: None)
            self.assertFalse(listener.start())
            self.assertFalse(listener.is_running())


class WindowResolverTest(unittest.TestCase):
    def test_macos_success(self):
        output = "Visual Studio Code\tmain.py\n"
        completed = subprocess.CompletedProcess(["osascript"], 0, stdout=output, stderr="")
        bundle = subprocess.CompletedProcess(
            ["osascript"], 0, stdout="com.microsoft.VSCode\n", stderr=""
        )
        with patch("watcher.event_source.window_resolver.platform.system", return_value="Darwin"), patch(
            "watcher.event_source.window_resolver.subprocess.run",
            side_effect=[completed, bundle],
        ):
            info = WindowResolver.get_active_window()
            self.assertEqual(info.app_name, "Visual Studio Code")
            self.assertEqual(info.window_title, "main.py")
            self.assertEqual(info.bundle_id, "com.microsoft.VSCode")

    def test_macos_failure_returns_unknown(self):
        with patch("watcher.event_source.window_resolver.platform.system", return_value="Darwin"), patch(
            "watcher.event_source.window_resolver.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "osascript"),
        ):
            info = WindowResolver.get_active_window()
            self.assertEqual(info.app_name, "Unknown")
            self.assertEqual(info.window_title, "")
            self.assertIsNone(info.bundle_id)


class EventBufferTest(unittest.TestCase):
    def test_aggregate_features(self):
        buffer = EventBuffer(window_seconds=300)
        buffer.add_click(
            ClickEvent(ts=100.0, x=1, y=1, button="left"),
            WindowInfo(
                app_name="VSCode",
                window_title="main.py - Project",
                bundle_id="com.microsoft.VSCode",
                timestamp=100.0,
            ),
        )
        buffer.add_click(
            ClickEvent(ts=120.0, x=2, y=2, button="left"),
            WindowInfo(
                app_name="Chrome",
                window_title="New Tab - YouTube",
                bundle_id="com.google.Chrome",
                timestamp=120.0,
            ),
        )
        buffer.add_click(
            ClickEvent(ts=170.0, x=3, y=3, button="right"),
            WindowInfo(
                app_name="Chrome",
                window_title="paper.pdf - arxiv",
                bundle_id="com.google.Chrome",
                timestamp=170.0,
            ),
        )

        features = buffer.get_aggregated_features(90.0, 180.0)
        self.assertEqual(features.click_count, 3)
        self.assertEqual(features.app_switch_count, 1)
        self.assertAlmostEqual(features.active_seconds, 50.0, places=3)
        self.assertEqual(features.top_app, "Chrome")
        self.assertEqual(features.app_distribution["VSCode"], 1)
        self.assertEqual(features.app_distribution["Chrome"], 2)
        self.assertIn("youtube", features.top_window_keywords)
        self.assertNotIn("new", features.top_window_keywords)
        self.assertNotIn("tab", features.top_window_keywords)

    def test_window_eviction_and_clear(self):
        buffer = EventBuffer(window_seconds=60)
        buffer.add_click(
            ClickEvent(ts=10.0, x=1, y=1, button="left"),
            WindowInfo("AppA", "Window A", None, 10.0),
        )
        buffer.add_click(
            ClickEvent(ts=80.0, x=1, y=1, button="left"),
            WindowInfo("AppB", "Window B", None, 80.0),
        )
        buffer.add_click(
            ClickEvent(ts=100.0, x=1, y=1, button="left"),
            WindowInfo("AppC", "Window C", None, 100.0),
        )

        all_features = buffer.get_aggregated_features(0.0, 120.0)
        self.assertEqual(all_features.click_count, 2)

        buffer.clear_old_events(90.0)
        clear_features = buffer.get_aggregated_features(0.0, 120.0)
        self.assertEqual(clear_features.click_count, 1)
        self.assertEqual(clear_features.top_app, "AppC")


class EventLoggerTest(unittest.TestCase):
    def test_log_and_rotate_by_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            logger = EventLogger(Path(tmp))

            ts_day1 = datetime(2026, 2, 10, 23, 59, 0).timestamp()
            ts_day2 = datetime(2026, 2, 11, 0, 1, 0).timestamp()

            logger.log_event(
                ClickEvent(ts=ts_day1, x=10, y=20, button="left"),
                WindowInfo("VSCode", "main.py", "com.microsoft.VSCode", ts_day1),
            )
            logger.log_event(
                ClickEvent(ts=ts_day2, x=30, y=40, button="right"),
                WindowInfo("Chrome", "docs", "com.google.Chrome", ts_day2),
            )
            logger.flush()
            logger.close()

            day1_path = Path(tmp) / "click-events-2026-02-10.jsonl"
            day2_path = Path(tmp) / "click-events-2026-02-11.jsonl"
            self.assertTrue(day1_path.exists())
            self.assertTrue(day2_path.exists())

            day1_lines = day1_path.read_text(encoding="utf-8").strip().splitlines()
            day2_lines = day2_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(day1_lines), 1)
            self.assertEqual(len(day2_lines), 1)

            row1 = json.loads(day1_lines[0])
            row2 = json.loads(day2_lines[0])
            self.assertIsInstance(row1["ts"], float)
            self.assertEqual(row1["button"], "left")
            self.assertEqual(row1["app_name"], "VSCode")
            self.assertEqual(row2["button"], "right")
            self.assertEqual(row2["app_name"], "Chrome")


if __name__ == "__main__":
    unittest.main()
