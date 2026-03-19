"""Integration tests for runner with hybrid event classifier."""

import os
from datetime import datetime, time
from unittest.mock import MagicMock, Mock, patch

import pytest

from watcher.config import Config
from watcher.event_source.models import AggregatedFeatures
from watcher.runner import Watcher
from watcher.signal_fusion import ClassificationResult
from watcher.signal_fusion.llm_event_classifier import EnhancedClassificationResult


@pytest.fixture
def base_config():
    """Base configuration for testing."""
    return Config(
        start_time=time(9, 0),
        end_time=time(18, 0),
        interval_s=30,
        min_send_interval_s=300,
        max_idle_send_interval_s=900,
        hash_diff_threshold=8,
        resize_width=960,
        jpeg_quality=70,
        api_url="https://api.example.com",
        api_key="test-key",
        api_timeout_s=30.0,
        vl_mode="auto",
        vl_model="gpt-4o-mini",
        event_summary_model="gpt-4o-mini",
        fusion_summary_model="gpt-4o-mini",
        daily_summary_model="gpt-4o-mini",
        vl_max_tokens=256,
        daily_summary_max_tokens=1024,
        classify_api_url="",
        classify_api_key=None,
        classify_timeout_s=15.0,
        task_categories=("写代码", "研究", "娱乐"),
        enable_event_source=True,
        event_privacy_mask=False,
        event_buffer_window_s=300,
        event_trigger_min_clicks=6,
        event_switch_trigger=True,
        fusion_vl_weight=0.7,
        fusion_event_weight=0.3,
        fusion_confidence_threshold=0.5,
        event_log_dir="logs",
        report_dir="reports",
        log_dir="logs",
        use_llm_event_classifier=False,
        llm_event_model="gpt-4o-mini",
        llm_event_threshold=0.6,
        llm_event_always=False,
        llm_event_timeout_s=10.0,
        monitor_index=1,
    )


@pytest.fixture
def llm_enabled_config(base_config):
    """Configuration with LLM event classifier enabled."""
    return Config(
        **{
            **base_config.__dict__,
            "use_llm_event_classifier": True,
        }
    )


class TestConfigLoading:
    """Test configuration loading with LLM event classifier settings."""

    def test_default_config_disables_llm(self, base_config):
        """Default configuration should have LLM classifier disabled."""
        assert base_config.use_llm_event_classifier is False
        assert base_config.llm_event_model == "gpt-4o-mini"
        assert base_config.llm_event_threshold == 0.6
        assert base_config.llm_event_always is False
        assert base_config.llm_event_timeout_s == 10.0

    def test_llm_config_enables_llm(self, llm_enabled_config):
        """LLM-enabled configuration should have correct settings."""
        assert llm_enabled_config.use_llm_event_classifier is True


class TestRuleClassifierMode:
    """Test runner with default rule-based classifier."""

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_uses_rule_classifier_by_default(
        self, mock_client_class, mock_capture, base_config
    ):
        """Should use rule-based classifier when LLM is disabled."""
        watcher = Watcher(base_config)

        # Verify rule classifier is used
        from watcher.signal_fusion import EventClassifier

        assert isinstance(watcher.event_classifier, EventClassifier)
        assert not hasattr(watcher.event_classifier, "llm_classifier")


class TestHybridClassifierMode:
    """Test runner with hybrid LLM event classifier."""

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_uses_hybrid_classifier_when_enabled(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """Should use hybrid classifier when LLM is enabled."""
        watcher = Watcher(llm_enabled_config)

        # Verify hybrid classifier is used
        from watcher.signal_fusion.hybrid_classifier import HybridEventClassifier

        assert isinstance(watcher.event_classifier, HybridEventClassifier)
        assert hasattr(watcher.event_classifier, "llm_classifier")
        assert hasattr(watcher.event_classifier, "rule_classifier")

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_hybrid_classifier_configuration(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """Hybrid classifier should be configured correctly."""
        watcher = Watcher(llm_enabled_config)

        assert watcher.event_classifier.llm_threshold == 0.6
        assert watcher.event_classifier.always_use_llm is False
        assert watcher.event_classifier.llm_classifier.timeout_s == 10.0


class TestClassificationBehavior:
    """Test classification behavior in different scenarios."""

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_high_confidence_rule_skips_llm(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """High confidence rule result should not call LLM."""
        # Mock VL client
        mock_client = Mock()
        mock_client.analyze_with_category.return_value = ("coding task", "写代码")
        mock_client_class.return_value = mock_client

        # Mock screen capture
        mock_image = MagicMock()
        mock_capture.return_value = mock_image

        watcher = Watcher(llm_enabled_config)

        # Mock rule classifier to return high confidence
        with patch.object(
            watcher.event_classifier.rule_classifier,
            "classify",
            return_value=ClassificationResult(
                category="写代码", confidence=0.85, reason="high confidence rule"
            ),
        ):
            # Mock LLM classifier to track if it's called
            llm_classify_called = False

            original_llm_classify = watcher.event_classifier.llm_classifier.classify

            def track_llm_call(*args, **kwargs):
                nonlocal llm_classify_called
                llm_classify_called = True
                return original_llm_classify(*args, **kwargs)

            with patch.object(
                watcher.event_classifier.llm_classifier,
                "classify",
                side_effect=track_llm_call,
            ):
                # Create features with activity
                features = AggregatedFeatures(
                    start_time=datetime.now().timestamp() - 300,
                    end_time=datetime.now().timestamp(),
                    click_count=10,
                    app_switch_count=2,
                    active_seconds=250.0,
                    top_app="VSCode",
                    top_window_keywords=["python", "code"],
                )

                # Classify
                result = watcher.event_classifier.classify(features)

                # LLM should not be called
                assert not llm_classify_called
                assert result.category == "写代码"
                assert result.confidence == 0.85

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_low_confidence_rule_calls_llm(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """Low confidence rule result should call LLM."""
        # Mock VL client
        mock_client = Mock()
        mock_client.analyze_with_category.return_value = ("browsing", "研究")
        # Mock the _chat_openai method that LLMEventClassifier uses
        mock_client._chat_openai.return_value = '{"category": "研究", "confidence": 0.75, "reasoning": "research activity", "activity_pattern": "researching", "focus_level": "high"}'
        mock_client_class.return_value = mock_client

        # Mock screen capture
        mock_image = MagicMock()
        mock_capture.return_value = mock_image

        watcher = Watcher(llm_enabled_config)

        # Mock rule classifier to return low confidence
        with patch.object(
            watcher.event_classifier.rule_classifier,
            "classify",
            return_value=ClassificationResult(
                category="研究", confidence=0.45, reason="low confidence rule"
            ),
        ):
            # Create features with activity
            features = AggregatedFeatures(
                start_time=datetime.now().timestamp() - 300,
                end_time=datetime.now().timestamp(),
                click_count=8,
                app_switch_count=3,
                active_seconds=200.0,
                top_app="Chrome",
                top_window_keywords=["documentation", "tutorial"],
            )

            # Classify
            result = watcher.event_classifier.classify(features)

            # LLM should be called and return result
            assert result.category == "研究"
            assert result.confidence == 0.75


class TestLLMFallback:
    """Test LLM failure fallback behavior."""

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_llm_failure_returns_rule_result(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """LLM failure should fallback to rule result."""
        # Mock VL client
        mock_client = Mock()
        mock_client._chat_openai.return_value = '{"category": "研究", "confidence": 0.7, "reasoning": "unused"}'
        mock_client_class.return_value = mock_client

        # Mock screen capture
        mock_image = MagicMock()
        mock_capture.return_value = mock_image

        watcher = Watcher(llm_enabled_config)

        # Mock rule classifier
        rule_result = ClassificationResult(
            category="写代码", confidence=0.55, reason="rule fallback"
        )
        with patch.object(
            watcher.event_classifier.rule_classifier,
            "classify",
            return_value=rule_result,
        ), patch.object(
            watcher.event_classifier.llm_classifier,
            "classify",
            return_value=EnhancedClassificationResult(
                category="研究",
                confidence=0.3,
                reasoning="LLM call failed: API error, using fallback",
                used_fallback=True,
            ),
        ):
            # Create features
            features = AggregatedFeatures(
                start_time=datetime.now().timestamp() - 300,
                end_time=datetime.now().timestamp(),
                click_count=5,
                app_switch_count=1,
                active_seconds=280.0,
                top_app="Terminal",
                top_window_keywords=["bash"],
            )

            # Classify - should fallback to rule result
            result = watcher.event_classifier.classify(features)

            # Should return rule result with fallback reason
            assert result.category == "写代码"
            assert "rule fallback" in result.reason.lower()


class TestFusionEngineIntegration:
    """Test integration with fusion engine."""

    @patch("watcher.runner.capture_screen")
    @patch("watcher.runner.VLClient")
    def test_fusion_with_hybrid_classifier(
        self, mock_client_class, mock_capture, llm_enabled_config
    ):
        """Fusion engine should work with hybrid classifier results."""
        # Mock VL client
        mock_client = Mock()
        mock_client.analyze_with_category.return_value = ("coding work", "写代码")
        mock_client_class.return_value = mock_client

        # Mock screen capture
        mock_image = MagicMock()
        mock_capture.return_value = mock_image

        watcher = Watcher(llm_enabled_config)

        # Mock event classifier
        event_result = ClassificationResult(
            category="写代码", confidence=0.80, reason="hybrid classification"
        )
        with patch.object(
            watcher.event_classifier, "classify", return_value=event_result
        ):
            # Create VL result
            vl_result = ClassificationResult(
                category="写代码", confidence=0.75, reason="vl analysis"
            )

            # Fuse results
            fusion_result = watcher.fusion_engine.fuse(
                vl_result, event_result, last_category=None
            )

            # Should produce valid fusion result
            assert fusion_result.category in llm_enabled_config.task_categories
            assert 0.0 <= fusion_result.confidence <= 1.0
            assert fusion_result.source in ["vl", "event", "fusion"]
