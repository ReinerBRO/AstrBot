from datetime import datetime
from pathlib import Path
from threading import Event
import time as time_module

from watcher.api_client import VLClient
from watcher.capture import capture_screen, to_jpeg_bytes
from watcher.config import Config
from watcher.diff import average_hash, hamming_distance
from watcher.event_source import (
    ClickListener,
    EventBuffer,
    EventLogger,
    WindowResolver,
    check_accessibility_permission,
)
from watcher.event_source.models import AggregatedFeatures, ClickEvent
from watcher.reporter import Reporter
from watcher.scheduler import in_window, seconds_until_start
from watcher.signal_fusion import ClassificationResult, EventClassifier, FusionEngine
from watcher.trigger import TriggerDetector


class Watcher:
    def __init__(
        self,
        config: Config,
        stop_event: Event | None = None,
        tree_id: str | None = None,
    ):
        self.config = config
        self.client = VLClient(config)
        self.reporter = Reporter(config)
        self.tree_id = tree_id or datetime.now().strftime("%Y%m%d-%H%M%S")
        self.last_hash = None
        self.last_sent_at = None
        self.last_summary = None
        self.last_category = None
        self.stop_event = stop_event

        self.event_source_enabled = bool(config.enable_event_source)
        self.event_buffer = (
            EventBuffer(window_seconds=config.event_buffer_window_s)
            if self.event_source_enabled
            else None
        )
        self.event_logger = None
        self.click_listener = None

        # Initialize event classifier based on configuration
        if self.config.use_llm_event_classifier:
            from watcher.signal_fusion.llm_event_classifier import LLMEventClassifier
            from watcher.signal_fusion.hybrid_classifier import HybridEventClassifier

            llm_classifier = LLMEventClassifier(
                api_client=self.client,
                model=self.config.llm_event_model,
                categories=self.config.task_categories,
                timeout_s=self.config.llm_event_timeout_s,
            )
            self.event_classifier = HybridEventClassifier(
                rule_classifier=EventClassifier(),
                llm_classifier=llm_classifier,
                llm_threshold=self.config.llm_event_threshold,
                always_use_llm=self.config.llm_event_always,
            )
        else:
            self.event_classifier = EventClassifier()

        self.fusion_engine = FusionEngine(
            vl_weight=config.fusion_vl_weight,
            event_weight=config.fusion_event_weight,
            confidence_threshold=config.fusion_confidence_threshold,
        )
        self.trigger_detector = TriggerDetector(
            min_clicks=config.event_trigger_min_clicks,
            switch_trigger=config.event_switch_trigger,
        )

    def _should_stop(self) -> bool:
        return bool(self.stop_event and self.stop_event.is_set())

    def _sleep(self, seconds: int) -> bool:
        end = time_module.time() + max(seconds, 0)
        while time_module.time() < end:
            if self._should_stop():
                return True
            time_module.sleep(min(1, end - time_module.time()))
        return False

    def run_forever(self):
        self.reporter.log_event(datetime.now(), "watcher started")
        if self.event_source_enabled:
            if self.event_logger is None:
                self.event_logger = EventLogger(Path(self.config.event_log_dir))
            if self.click_listener is None:
                self.click_listener = ClickListener(self._on_click)
            listener_ok = self.click_listener.start()
            permission = check_accessibility_permission()
            self.reporter.log_event(
                datetime.now(),
                (
                    f"event-source enabled={self.event_source_enabled} "
                    f"listener={listener_ok} permission={permission}"
                ),
            )

        try:
            while not self._should_stop():
                now = datetime.now()
                if not in_window(now, self.config.start_time, self.config.end_time):
                    sleep_s = seconds_until_start(now, self.config.start_time)
                    self.reporter.log_event(
                        now, f"sleeping {sleep_s}s (outside window)"
                    )
                    if self._sleep(max(sleep_s, 5)):
                        break
                    continue

                try:
                    self._process_once(now, force_send=False)
                except Exception as exc:
                    self.reporter.log_event(now, f"error {exc}")

                if self._sleep(self.config.interval_s):
                    break
        finally:
            if self.click_listener is not None:
                self.click_listener.stop()
                self.click_listener = None
            if self.event_logger is not None:
                self.event_logger.close()
                self.event_logger = None

    def run_once(self, force_send: bool = False):
        now = datetime.now()
        return self._process_once(now, force_send=force_send)

    def _process_once(self, now: datetime, force_send: bool):
        image = capture_screen(self.config.monitor_index)
        current_hash = average_hash(image)
        diff = (
            64
            if self.last_hash is None
            else hamming_distance(self.last_hash, current_hash)
        )
        self.last_hash = current_hash

        event_features = self._get_event_features(now)
        event_triggered = self.trigger_detector.should_trigger(event_features)
        should_send = force_send or self._should_send(now, diff, event_triggered)
        if should_send:
            jpeg = to_jpeg_bytes(
                image,
                quality=self.config.jpeg_quality,
                resize_width=self.config.resize_width,
            )
            summary, vl_category = self.client.analyze_with_category(jpeg, now)
            default_category = self.config.task_categories[0]
            if summary:
                vl_best_category = vl_category or self.client.classify(summary)
            else:
                vl_best_category = default_category

            category = self._normalize_category(
                vl_best_category, default=default_category
            )
            source = "vl"
            reason = "vl only"
            event_category = None
            vl_result = self._to_vl_result(summary, vl_category, category)

            if summary and self.event_source_enabled and event_features.click_count > 0:
                import time as time_module_local

                event_start = time_module_local.time()
                event_result = self.event_classifier.classify(event_features)
                event_elapsed = time_module_local.time() - event_start

                # Log classifier usage
                classifier_type = (
                    "hybrid" if self.config.use_llm_event_classifier else "rule"
                )
                self.reporter.log_event(
                    now,
                    (
                        f"event-classifier type={classifier_type} "
                        f"category={event_result.category} "
                        f"confidence={event_result.confidence:.2f} "
                        f"elapsed={event_elapsed:.3f}s"
                    ),
                )

                fusion_result = self.fusion_engine.fuse(
                    vl_result, event_result, last_category=self.last_category
                )
                category = self._normalize_category(
                    fusion_result.category, default=default_category
                )
                source = fusion_result.source
                reason = fusion_result.reason
                event_category = fusion_result.event_category

            if summary and summary != self.last_summary:
                self.reporter.append_report(
                    now,
                    summary,
                    category,
                    tree_id=self.tree_id,
                    source=source,
                    reason=reason,
                    vl_category=vl_result.category,
                    event_category=event_category,
                )
                self.last_summary = summary
            self.last_category = category
            self.last_sent_at = now
            self.reporter.log_event(
                now,
                (
                    f"sent diff={diff} category={category} source={source} "
                    f"trigger={event_triggered} app={event_features.top_app} summary={summary}"
                ),
            )
            return summary, category, diff, self.tree_id

        self.reporter.log_event(
            now,
            f"skip diff={diff} trigger={event_triggered} clicks={event_features.click_count} app={event_features.top_app}",
        )
        return None, None, diff, self.tree_id

    def _should_send(
        self, now: datetime, diff: int, event_triggered: bool = False
    ) -> bool:
        if self.last_sent_at is None:
            return True
        since = (now - self.last_sent_at).total_seconds()
        if since < self.config.min_send_interval_s:
            return False
        if event_triggered:
            return True
        if diff >= self.config.hash_diff_threshold:
            return True
        return since >= self.config.max_idle_send_interval_s

    def _on_click(self, event: ClickEvent) -> None:
        if self.event_buffer is None:
            return
        try:
            window = WindowResolver.get_active_window(
                mask_title=self.config.event_privacy_mask
            )
            self.event_buffer.add_click(event, window)
            if self.event_logger is not None:
                self.event_logger.log_event(event, window)
        except Exception as exc:
            self.reporter.log_event(
                datetime.now(), f"event-source callback error: {exc}"
            )

    def _get_event_features(self, now: datetime) -> AggregatedFeatures:
        if self.event_buffer is None:
            ts = now.timestamp()
            return AggregatedFeatures(start_time=ts, end_time=ts)
        end_ts = now.timestamp()
        start_ts = end_ts - self.config.event_buffer_window_s
        self.event_buffer.clear_old_events(start_ts - self.config.event_buffer_window_s)
        return self.event_buffer.get_aggregated_features(start_ts, end_ts)

    def _to_vl_result(
        self, summary: str | None, vl_category: str | None, best_category: str
    ) -> ClassificationResult:
        if not summary:
            return ClassificationResult(
                category=best_category,
                confidence=0.35,
                reason="no summary from vl response",
            )
        if vl_category:
            return ClassificationResult(
                category=best_category,
                confidence=0.86,
                reason="vl returned category directly",
            )
        return ClassificationResult(
            category=best_category,
            confidence=0.62,
            reason="summary classified by fallback classifier",
        )

    def _normalize_category(self, value: str, default: str) -> str:
        text = (value or "").strip()
        if text in self.config.task_categories:
            return text
        if text == "其他":
            return "研究" if "研究" in self.config.task_categories else default
        alias = {
            "coding": "写代码",
            "research": "研究",
            "entertainment": "娱乐",
        }
        mapped = alias.get(text.lower()) if text else None
        if mapped and mapped in self.config.task_categories:
            return mapped
        return default

    def get_event_source_status(self) -> dict:
        return {
            "enabled": bool(self.config.enable_event_source),
            "listener_running": bool(
                self.click_listener is not None and self.click_listener.is_running()
            ),
            "permission_granted": check_accessibility_permission(),
            "recent_apps": (
                self.event_buffer.get_recent_apps(limit=5)
                if self.event_buffer is not None
                else []
            ),
        }

    def get_event_source_summary(self) -> dict:
        features = self._get_event_features(datetime.now())
        return {
            "click_count": features.click_count,
            "app_switch_count": features.app_switch_count,
            "active_seconds": round(features.active_seconds, 2),
            "top_app": features.top_app,
            "top_keywords": features.top_window_keywords[:5],
        }
