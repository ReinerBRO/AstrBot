"""Hybrid event classifier combining rule-based and LLM approaches."""

from watcher.event_source.models import AggregatedFeatures
from watcher.signal_fusion.event_classifier import (
    ClassificationResult,
    EventClassifier,
)
from watcher.signal_fusion.llm_event_classifier import (
    EnhancedClassificationResult,
    LLMEventClassifier,
)


class HybridEventClassifier:
    """
    Hybrid classifier that uses rules for fast path and LLM for complex cases.

    Strategy:
    1. Try rule-based classification first (fast, free)
    2. If confidence < threshold, use LLM for deeper analysis
    3. Return enhanced result with reasoning

    This provides the best of both worlds:
    - Fast and cheap for obvious cases
    - Deep understanding for ambiguous cases
    """

    def __init__(
        self,
        rule_classifier: EventClassifier,
        llm_classifier: LLMEventClassifier,
        llm_threshold: float = 0.6,
        always_use_llm: bool = False,
    ):
        """
        Initialize hybrid classifier.

        Args:
            rule_classifier: Rule-based classifier for fast path
            llm_classifier: LLM classifier for deep analysis
            llm_threshold: Use LLM if rule confidence < this threshold
            always_use_llm: If True, always use LLM (ignore threshold)
        """
        self.rule_classifier = rule_classifier
        self.llm_classifier = llm_classifier
        self.llm_threshold = llm_threshold
        self.always_use_llm = always_use_llm

    def classify(self, features: AggregatedFeatures) -> ClassificationResult:
        """
        Classify activity using hybrid approach.

        Returns:
            ClassificationResult compatible with existing fusion engine
        """
        rule_result: ClassificationResult | None = None
        # Fast path: try rule-based first
        if not self.always_use_llm:
            rule_result = self.rule_classifier.classify(features)

            # If rule-based is confident, use it
            if rule_result.confidence >= self.llm_threshold:
                return rule_result

        # Slow path: use LLM for deeper analysis
        try:
            llm_result = self.llm_classifier.classify(features)
        except Exception as exc:
            if rule_result is not None:
                return ClassificationResult(
                    category=rule_result.category,
                    confidence=rule_result.confidence,
                    reason=f"rule fallback after llm exception: {rule_result.reason}",
                )
            raise

        if rule_result is not None and llm_result.used_fallback:
            return ClassificationResult(
                category=rule_result.category,
                confidence=rule_result.confidence,
                reason=f"rule fallback after llm failure: {rule_result.reason}",
            )

        # Convert enhanced result to standard ClassificationResult
        return ClassificationResult(
            category=llm_result.category,
            confidence=llm_result.confidence,
            reason=llm_result.reasoning,
        )

    def classify_enhanced(
        self, features: AggregatedFeatures
    ) -> EnhancedClassificationResult:
        """
        Classify with enhanced result including activity patterns.

        Use this when you want the full reasoning and pattern analysis.
        """
        if not self.always_use_llm:
            rule_result = self.rule_classifier.classify(features)
            if rule_result.confidence >= self.llm_threshold:
                # Convert rule result to enhanced format
                return EnhancedClassificationResult(
                    category=rule_result.category,
                    confidence=rule_result.confidence,
                    reasoning=f"Rule-based: {rule_result.reason}",
                    activity_pattern="rule_matched",
                    focus_level=self._infer_focus_level(features),
                )

        return self.llm_classifier.classify(features)

    def _infer_focus_level(self, features: AggregatedFeatures) -> str:
        """Infer focus level from event features."""
        if features.active_seconds <= 0:
            return "none"

        # Calculate switches per minute
        switches_per_min = (
            features.app_switch_count / (features.active_seconds / 60)
            if features.active_seconds > 0
            else 0
        )

        if switches_per_min > 3:
            return "low"  # Frequent switching = distracted
        elif switches_per_min > 1:
            return "medium"
        else:
            return "high"  # Focused on one app
