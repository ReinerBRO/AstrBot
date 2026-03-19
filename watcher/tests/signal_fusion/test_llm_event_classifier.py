"""Tests for LLM event classifier."""

import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from watcher.event_source.models import AggregatedFeatures
from watcher.signal_fusion.llm_event_classifier import (
    EnhancedClassificationResult,
    LLMEventClassifier,
)


class MockAPIClient:
    """Mock API client for testing."""

    def __init__(self, response: str = ""):
        self.url = "http://localhost:8000/v1"
        self.api_key = "test-key"
        self.timeout = 30.0
        self.max_tokens = 256
        self.response = response

    def _chat_openai(self, messages: list[dict], model: str) -> str:
        return self.response


class LLMEventClassifierTest(unittest.TestCase):
    def test_classify_no_activity(self):
        """Test classification with no activity."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=0,
            app_switch_count=0,
            active_seconds=0.0,
            top_app="Unknown",
            top_window_keywords=[],
            app_distribution={},
        )

        result = classifier.classify(features)
        self.assertEqual(result.category, "其他")
        self.assertEqual(result.confidence, 0.0)
        self.assertIn("No activity", result.reasoning)

    def test_classify_coding_activity(self):
        """Test classification of coding activity."""
        response_json = {
            "category": "写代码",
            "confidence": 0.9,
            "reasoning": "在VSCode中编辑Python代码",
            "activity_pattern": "debugging",
            "focus_level": "high",
        }
        api_client = MockAPIClient(response=json.dumps(response_json))
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=15,
            app_switch_count=2,
            active_seconds=280.0,
            top_app="VSCode",
            top_window_keywords=["python", "main.py", "debug"],
            app_distribution={"VSCode": 10, "Terminal": 5},
        )

        result = classifier.classify(features)
        self.assertEqual(result.category, "写代码")
        self.assertGreater(result.confidence, 0.8)
        self.assertEqual(result.activity_pattern, "debugging")
        self.assertEqual(result.focus_level, "high")

    def test_classify_research_activity(self):
        """Test classification of research activity."""
        response_json = {
            "category": "研究",
            "confidence": 0.85,
            "reasoning": "在Chrome中阅读arxiv论文",
            "activity_pattern": "researching",
            "focus_level": "high",
        }
        api_client = MockAPIClient(response=json.dumps(response_json))
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=8,
            app_switch_count=1,
            active_seconds=250.0,
            top_app="Chrome",
            top_window_keywords=["arxiv", "paper", "pdf"],
            app_distribution={"Chrome": 8},
        )

        result = classifier.classify(features)
        self.assertEqual(result.category, "研究")
        self.assertGreater(result.confidence, 0.7)

    def test_parse_response_with_markdown(self):
        """Test parsing JSON from markdown code block."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        response = """```json
{
  "category": "写代码",
  "confidence": 0.9,
  "reasoning": "编程活动",
  "activity_pattern": "coding",
  "focus_level": "high"
}
```"""

        result = classifier._parse_response(response)
        self.assertEqual(result.category, "写代码")
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.activity_pattern, "coding")

    def test_parse_response_plain_json(self):
        """Test parsing plain JSON response."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        response = '{"category": "研究", "confidence": 0.8, "reasoning": "研究活动"}'

        result = classifier._parse_response(response)
        self.assertEqual(result.category, "研究")
        self.assertEqual(result.confidence, 0.8)

    def test_parse_response_invalid_json(self):
        """Test parsing invalid JSON falls back gracefully."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        response = "This is not JSON but mentions 写代码"

        result = classifier._parse_response(response)
        self.assertEqual(result.category, "写代码")
        self.assertLess(result.confidence, 0.5)

    def test_normalize_category(self):
        """Test category normalization."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        self.assertEqual(classifier._normalize_category("写代码"), "写代码")
        self.assertEqual(classifier._normalize_category("coding"), "写代码")
        self.assertEqual(classifier._normalize_category("programming"), "写代码")
        self.assertEqual(classifier._normalize_category("research"), "研究")
        self.assertEqual(classifier._normalize_category("study"), "研究")
        self.assertEqual(classifier._normalize_category("entertainment"), "娱乐")

    def test_extract_json_from_response(self):
        """Test JSON extraction from various formats."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        plain = '{"category": "写代码"}'
        self.assertIsNotNone(classifier._extract_json_from_response(plain))

        markdown = '```json\n{"category": "研究"}\n```'
        self.assertIsNotNone(classifier._extract_json_from_response(markdown))

        mixed = 'Here is the result: {"category": "娱乐"}'
        self.assertIsNotNone(classifier._extract_json_from_response(mixed))

        invalid = "No JSON here"
        self.assertIsNone(classifier._extract_json_from_response(invalid))

    def test_fallback_classify_coding(self):
        """Test fallback classification for coding."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=10,
            app_switch_count=2,
            active_seconds=250.0,
            top_app="VSCode",
            top_window_keywords=["python", "main.py"],
            app_distribution={"VSCode": 10},
        )

        category = classifier._fallback_classify(features)
        self.assertEqual(category, "写代码")

    def test_fallback_classify_research(self):
        """Test fallback classification for research."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=5,
            app_switch_count=1,
            active_seconds=200.0,
            top_app="Chrome",
            top_window_keywords=["arxiv", "pdf"],
            app_distribution={"Chrome": 5},
        )

        category = classifier._fallback_classify(features)
        self.assertEqual(category, "研究")

    def test_fallback_classify_entertainment(self):
        """Test fallback classification for entertainment."""
        api_client = MockAPIClient()
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=8,
            app_switch_count=3,
            active_seconds=180.0,
            top_app="Chrome",
            top_window_keywords=["bilibili", "video"],
            app_distribution={"Chrome": 8},
        )

        category = classifier._fallback_classify(features)
        self.assertEqual(category, "娱乐")

    @patch("watcher.signal_fusion.llm_event_classifier.requests.post")
    def test_call_llm_with_retry(self, mock_post):
        """Test LLM call with retry mechanism."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"category": "写代码"}'}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        api_client = SimpleNamespace(
            url="http://localhost:8000/v1",
            api_key="test-key",
            timeout=30.0,
            max_tokens=256,
        )
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        result = classifier._call_llm("test prompt")
        self.assertIn("category", result)

    @patch("watcher.signal_fusion.llm_event_classifier.requests.post")
    def test_call_llm_timeout_retry(self, mock_post):
        """Test LLM call retries on timeout."""
        import requests

        mock_post.side_effect = [
            requests.exceptions.Timeout(),
            requests.exceptions.Timeout(),
            MagicMock(
                json=lambda: {
                    "choices": [{"message": {"content": '{"category": "写代码"}'}}]
                },
                raise_for_status=lambda: None,
            ),
        ]

        api_client = SimpleNamespace(
            url="http://localhost:8000/v1",
            api_key="test-key",
            timeout=30.0,
            max_tokens=256,
        )
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        result = classifier._call_llm("test prompt")
        self.assertIn("category", result)
        self.assertEqual(mock_post.call_count, 3)

    def test_classify_with_llm_failure(self):
        """Test classification falls back when LLM fails."""
        api_client = MockAPIClient(response="")
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        with patch.object(classifier, "_call_llm", side_effect=Exception("API Error")):
            features = AggregatedFeatures(
                start_time=100.0,
                end_time=400.0,
                click_count=10,
                app_switch_count=2,
                active_seconds=250.0,
                top_app="VSCode",
                top_window_keywords=["python"],
                app_distribution={"VSCode": 10},
            )

            result = classifier.classify(features)
            self.assertEqual(result.category, "写代码")
            self.assertLess(result.confidence, 0.5)
            self.assertIn("failed", result.reasoning.lower())

    def test_confidence_bounds(self):
        """Test confidence is bounded between 0 and 1."""
        response_json = {
            "category": "写代码",
            "confidence": 1.5,
            "reasoning": "测试",
        }
        api_client = MockAPIClient(response=json.dumps(response_json))
        classifier = LLMEventClassifier(api_client, categories=["写代码", "研究", "娱乐"])

        features = AggregatedFeatures(
            start_time=100.0,
            end_time=400.0,
            click_count=10,
            app_switch_count=2,
            active_seconds=250.0,
            top_app="VSCode",
            top_window_keywords=["python"],
            app_distribution={"VSCode": 10},
        )

        result = classifier.classify(features)
        self.assertLessEqual(result.confidence, 1.0)
        self.assertGreaterEqual(result.confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
