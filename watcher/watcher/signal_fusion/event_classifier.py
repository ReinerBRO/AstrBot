from dataclasses import dataclass

from watcher.event_source.models import AggregatedFeatures

DEFAULT_KEYWORD_RULES: dict[str, list[str]] = {
    "写代码": [
        "vscode",
        "pycharm",
        "intellij",
        "terminal",
        "iterm",
        "git",
        "github",
        "repo",
        "python",
        "java",
        "typescript",
        "debug",
    ],
    "研究": [
        "arxiv",
        "paper",
        "pdf",
        "scholar",
        "documentation",
        "wiki",
        "notion",
        "readme",
        "docs",
        "research",
        "study",
        "学习",
        "文档",
    ],
    "娱乐": [
        "youtube",
        "bilibili",
        "netflix",
        "spotify",
        "game",
        "游戏",
        "douyin",
        "tiktok",
        "movie",
        "music",
    ],
    "聊天": [
        "wechat",
        "weixin",
        "qq",
        "telegram",
        "discord",
        "slack",
        "zoom",
        "meeting",
        "chat",
        "message",
        "teams",
        "飞书",
        "企业微信",
        "钉钉",
    ],
}


@dataclass(frozen=True)
class ClassificationResult:
    category: str
    confidence: float
    reason: str


class EventClassifier:
    def __init__(self, rules: dict[str, list[str]] | None = None):
        self.rules = rules or DEFAULT_KEYWORD_RULES

    def classify(self, features: AggregatedFeatures) -> ClassificationResult:
        if features.click_count <= 0:
            return ClassificationResult(
                category="其他",
                confidence=0.0,
                reason="no click events in time window",
            )

        lower_top_app = (features.top_app or "").lower()
        lower_keywords = [item.lower() for item in features.top_window_keywords]
        candidate_texts = [lower_top_app, *lower_keywords]

        scores: dict[str, float] = {label: 0.0 for label in self.rules}
        matched: dict[str, list[str]] = {label: [] for label in self.rules}

        for label, keywords in self.rules.items():
            for keyword in keywords:
                token = keyword.lower().strip()
                if not token:
                    continue
                gain = 0.0
                if token and token in lower_top_app:
                    gain += 2.4
                if any(token in text for text in lower_keywords):
                    gain += 1.3
                if any(token in name.lower() for name in features.app_distribution):
                    gain += 0.8
                if gain > 0:
                    scores[label] += gain
                    matched[label].append(token)

        best_label = max(scores, key=scores.get)
        best_score = scores[best_label]
        total_score = sum(scores.values())

        if best_score <= 0:
            fallback = "研究" if features.click_count >= 3 else "其他"
            confidence = min(0.45, 0.16 + features.click_count * 0.04)
            return ClassificationResult(
                category=fallback,
                confidence=confidence,
                reason=f"weak event signal, fallback={fallback}",
            )

        ratio = best_score / max(total_score, best_score)
        base = min(0.75, 0.22 + features.click_count * 0.05)
        confidence = max(0.05, min(0.95, base * 0.62 + ratio * 0.38))

        final_label = best_label
        if best_label == "聊天":
            # 聊天类默认更接近“研究”（保守策略），避免误判成娱乐。
            final_label = "研究"
            confidence = min(confidence, 0.7)

        reason_tokens = matched.get(best_label, [])[:3]
        reason = (
            f"event rule matched app={features.top_app}, "
            f"tokens={','.join(reason_tokens) if reason_tokens else 'none'}"
        )
        return ClassificationResult(
            category=final_label,
            confidence=confidence,
            reason=reason,
        )
