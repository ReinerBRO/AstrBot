from dataclasses import dataclass

from watcher.signal_fusion.event_classifier import ClassificationResult


@dataclass(frozen=True)
class FusionResult:
    category: str
    confidence: float
    source: str
    reason: str
    vl_category: str | None
    event_category: str | None


class FusionEngine:
    def __init__(
        self,
        vl_weight: float = 0.7,
        event_weight: float = 0.3,
        confidence_threshold: float = 0.5,
        fallback_category: str = "研究",
    ):
        total = max(0.001, vl_weight + event_weight)
        self.vl_weight = max(0.0, vl_weight) / total
        self.event_weight = max(0.0, event_weight) / total
        self.confidence_threshold = max(0.0, min(1.0, confidence_threshold))
        self.fallback_category = fallback_category

    def fuse(
        self,
        vl_result: ClassificationResult,
        event_result: ClassificationResult,
        last_category: str | None = None,
    ) -> FusionResult:
        vl_conf = max(0.0, min(1.0, vl_result.confidence))
        event_conf = max(0.0, min(1.0, event_result.confidence))
        diff = abs(vl_conf - event_conf)

        if vl_conf > 0.8:
            return FusionResult(
                category=vl_result.category,
                confidence=vl_conf,
                source="vl",
                reason=f"vl confidence high ({vl_conf:.2f})",
                vl_category=vl_result.category,
                event_category=event_result.category,
            )

        if event_conf > 0.8 and vl_conf < 0.5:
            return FusionResult(
                category=event_result.category,
                confidence=event_conf,
                source="event",
                reason=f"event confidence high ({event_conf:.2f}) while vl low ({vl_conf:.2f})",
                vl_category=vl_result.category,
                event_category=event_result.category,
            )

        if vl_result.category == event_result.category:
            confidence = vl_conf * self.vl_weight + event_conf * self.event_weight
            source = "fusion" if event_conf > 0 else "vl"
            return FusionResult(
                category=vl_result.category,
                confidence=confidence,
                source=source,
                reason=f"same category from both sources ({vl_result.category})",
                vl_category=vl_result.category,
                event_category=event_result.category,
            )

        if diff < 0.2:
            category, confidence = self._blend(vl_result, event_result)
            return FusionResult(
                category=category,
                confidence=confidence,
                source="fusion",
                reason=f"close confidence (vl={vl_conf:.2f}, event={event_conf:.2f}), weighted blend",
                vl_category=vl_result.category,
                event_category=event_result.category,
            )

        winner = vl_result if vl_conf >= event_conf else event_result
        winner_source = "vl" if winner is vl_result else "event"
        winner_conf = max(vl_conf, event_conf)
        if winner_conf >= self.confidence_threshold:
            return FusionResult(
                category=winner.category,
                confidence=winner_conf,
                source=winner_source,
                reason=f"conflict resolved by higher confidence ({winner_conf:.2f})",
                vl_category=vl_result.category,
                event_category=event_result.category,
            )

        conservative = last_category or self.fallback_category
        return FusionResult(
            category=conservative,
            confidence=max(vl_conf, event_conf),
            source="fusion",
            reason=(
                f"both confidences below threshold ({self.confidence_threshold:.2f}), "
                f"fallback={conservative}"
            ),
            vl_category=vl_result.category,
            event_category=event_result.category,
        )

    def _blend(
        self,
        vl_result: ClassificationResult,
        event_result: ClassificationResult,
    ) -> tuple[str, float]:
        scores: dict[str, float] = {}
        scores[vl_result.category] = scores.get(vl_result.category, 0.0) + (
            vl_result.confidence * self.vl_weight
        )
        scores[event_result.category] = scores.get(event_result.category, 0.0) + (
            event_result.confidence * self.event_weight
        )
        category = max(scores, key=scores.get)
        return category, max(0.0, min(1.0, scores[category]))
