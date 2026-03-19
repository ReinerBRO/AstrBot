"""LLM-based event classifier for enhanced activity understanding."""

import json
import re
from dataclasses import dataclass

import requests

from watcher.event_source.models import AggregatedFeatures


@dataclass(frozen=True)
class EnhancedClassificationResult:
    """Enhanced classification with reasoning and patterns."""

    category: str
    confidence: float
    reasoning: str
    activity_pattern: str | None = None  # e.g., "debugging", "researching", "writing"
    focus_level: str | None = None  # e.g., "high", "medium", "low"
    used_fallback: bool = False


class LLMEventClassifier:
    """
    LLM-based event classifier that understands temporal patterns and context.

    This classifier provides deeper understanding than rule-based matching by:
    - Analyzing temporal sequences of app usage
    - Understanding relationships between apps (e.g., IDE + browser + terminal = coding)
    - Identifying activity patterns (debugging, researching, multitasking)
    - Providing explainable reasoning
    """

    def __init__(
        self,
        api_client,  # VLClient or similar
        model: str = "gpt-4o-mini",
        categories: list[str] | None = None,
        timeout_s: float | None = None,
    ):
        self.api_client = api_client
        self.model = model
        self.categories = categories or ["写代码", "研究", "娱乐", "聊天", "其他"]
        self.timeout_s = (
            float(timeout_s) if timeout_s is not None and float(timeout_s) > 0 else None
        )

    def classify(self, features: AggregatedFeatures) -> EnhancedClassificationResult:
        """
        Classify activity based on aggregated event features.

        Args:
            features: Aggregated event features from EventBuffer

        Returns:
            Enhanced classification with reasoning and patterns
        """
        if features.click_count <= 0:
            return EnhancedClassificationResult(
                category="其他",
                confidence=0.0,
                reasoning="No activity detected in time window",
                used_fallback=False,
            )

        prompt = self._build_prompt(features)

        try:
            response = self._call_llm(prompt)
            result = self._parse_response(response)
            return result
        except Exception as e:
            return EnhancedClassificationResult(
                category=self._fallback_classify(features),
                confidence=0.3,
                reasoning=f"LLM call failed: {str(e)}, using fallback",
                used_fallback=True,
            )

    def _build_prompt(self, features: AggregatedFeatures) -> str:
        """Build LLM prompt from event features with few-shot examples."""
        categories_str = "、".join(self.categories)

        prompt = f"""分析以下用户活动数据，判断用户正在做什么。

时间窗口: {features.end_time - features.start_time:.0f} 秒
点击次数: {features.click_count}
应用切换次数: {features.app_switch_count}
活跃时长: {features.active_seconds:.1f} 秒

最常用应用: {features.top_app}
窗口关键词: {", ".join(features.top_window_keywords[:5])}
应用分布: {json.dumps(features.app_distribution, ensure_ascii=False)}

请分析用户的活动类型，从以下分类中选择一个：
{categories_str}

## 示例

示例 1:
输入: 最常用应用=VSCode, 窗口关键词=[python, main.py, debug], 点击=15, 切换=2
输出: {{"category": "写代码", "confidence": 0.9, "reasoning": "在VSCode中编辑Python代码，窗口标题包含debug关键词", "activity_pattern": "debugging", "focus_level": "high"}}

示例 2:
输入: 最常用应用=Chrome, 窗口关键词=[arxiv, paper, pdf], 点击=8, 切换=1
输出: {{"category": "研究", "confidence": 0.85, "reasoning": "在Chrome中阅读arxiv论文", "activity_pattern": "researching", "focus_level": "high"}}

示例 3:
输入: 最常用应用=Chrome, 窗口关键词=[bilibili, video], 点击=5, 切换=3
输出: {{"category": "娱乐", "confidence": 0.9, "reasoning": "在bilibili观看视频", "activity_pattern": "watching", "focus_level": "medium"}}

示例 4:
输入: 最常用应用=WeChat, 窗口关键词=[chat, message], 点击=20, 切换=5
输出: {{"category": "娱乐", "confidence": 0.75, "reasoning": "在微信聊天，频繁切换窗口", "activity_pattern": "chatting", "focus_level": "low"}}

示例 5:
输入: 最常用应用=Terminal, 窗口关键词=[git, commit, push], 点击=10, 切换=2
输出: {{"category": "写代码", "confidence": 0.85, "reasoning": "在终端执行git操作", "activity_pattern": "version_control", "focus_level": "medium"}}

## 输出格式

请严格以 JSON 格式返回，不要输出其他文字：
{{
  "category": "分类名称",
  "confidence": 0.0-1.0,
  "reasoning": "推理过程（1-2句话）",
  "activity_pattern": "活动模式（如 debugging, researching, writing）",
  "focus_level": "专注程度（high/medium/low）"
}}

## 注意事项

- 如果应用切换频繁（>3次/分钟），focus_level 应该是 low
- 如果窗口关键词包含技术术语（python, java, api, debug等），可能是"写代码"或"研究"
- Chrome/Safari 不一定是娱乐，要看窗口标题关键词
- 如果窗口关键词包含聊天工具（wechat, qq, telegram），但同时有工作关键词（需求、任务、项目），可能是"写代码"
- 边界情况：如果无法确定，选择最可能的分类，并降低confidence
"""
        return prompt

    def _parse_response(self, response: str) -> EnhancedClassificationResult:
        """Parse LLM response into structured result with robust fallback."""
        parsed = self._extract_json_from_response(response)

        if parsed:
            try:
                category = str(parsed.get("category", "其他"))
                confidence = float(parsed.get("confidence", 0.5))
                reasoning = str(parsed.get("reasoning", ""))
                activity_pattern = parsed.get("activity_pattern")
                focus_level = parsed.get("focus_level")

                if category not in self.categories:
                    category = self._normalize_category(category)

                confidence = max(0.0, min(1.0, confidence))

                return EnhancedClassificationResult(
                    category=category,
                    confidence=confidence,
                    reasoning=reasoning,
                    activity_pattern=activity_pattern,
                    focus_level=focus_level,
                    used_fallback=False,
                )
            except (ValueError, TypeError) as e:
                pass

        category = self._extract_category_from_text(response)
        return EnhancedClassificationResult(
            category=category,
            confidence=0.4,
            reasoning=f"Failed to parse structured response, extracted category from text",
            used_fallback=False,
        )

    def _call_llm(self, prompt: str) -> str:
        """Call LLM API with retry mechanism."""
        timeout = self.timeout_s
        if timeout is None:
            timeout = float(getattr(self.api_client, "timeout", 30.0))
        timeout = max(0.1, timeout)

        max_retries = 3
        if hasattr(self.api_client, "_chat_openai"):
            messages = [
                {
                    "role": "system",
                    "content": "你是工作日志助手。请严格输出 JSON 对象，不要输出其他文字。",
                },
                {"role": "user", "content": prompt},
            ]
            last_exc: Exception | None = None
            for attempt in range(max_retries):
                original_timeout = getattr(self.api_client, "timeout", None)
                has_timeout_attr = hasattr(self.api_client, "timeout")
                if has_timeout_attr:
                    try:
                        self.api_client.timeout = timeout
                    except Exception:
                        has_timeout_attr = False
                try:
                    return self.api_client._chat_openai(messages, self.model)
                except Exception as exc:
                    last_exc = exc
                    if attempt == max_retries - 1:
                        raise
                finally:
                    if has_timeout_attr:
                        try:
                            self.api_client.timeout = original_timeout
                        except Exception:
                            pass
            if last_exc is not None:
                raise last_exc

        url = self.api_client.url
        if url.rstrip("/").endswith("/v1"):
            url = url.rstrip("/") + "/chat/completions"

        payload = {
            "model": self.model,
            "max_tokens": self.api_client.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": "你是工作日志助手。请严格输出 JSON 对象，不要输出其他文字。",
                },
                {"role": "user", "content": prompt},
            ],
        }

        headers = {"Content-Type": "application/json"}
        if self.api_client.api_key:
            headers["Authorization"] = f"Bearer {self.api_client.api_key}"

        for attempt in range(max_retries):
            try:
                resp = requests.post(
                    url,
                    data=json.dumps(payload),
                    headers=headers,
                    timeout=timeout,
                )
                resp.raise_for_status()

                try:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
                except Exception:
                    return resp.text.strip()

            except requests.exceptions.Timeout:
                if attempt == max_retries - 1:
                    raise
                continue
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise
                continue

        raise RuntimeError("Failed to call LLM after retries")

    def _extract_json_from_response(self, text: str) -> dict | None:
        """Extract JSON from LLM response, handling markdown code blocks."""
        raw = (text or "").strip()
        if not raw:
            return None

        candidates: list[str] = [raw]

        fenced = re.search(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw, flags=re.IGNORECASE
        )
        if fenced:
            candidates.insert(0, fenced.group(1))

        inline = re.search(r"(\{[\s\S]*\})", raw)
        if inline:
            candidates.append(inline.group(1))

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
                if isinstance(payload, dict):
                    return payload
            except Exception:
                continue

        return None

    def _normalize_category(self, label: str) -> str:
        """Normalize category label to match configured categories."""
        raw = label.lower().strip()

        for category in self.categories:
            if raw == category.lower():
                return category

        alias = {
            "code": "写代码",
            "coding": "写代码",
            "programming": "写代码",
            "develop": "写代码",
            "开发": "写代码",
            "research": "研究",
            "study": "研究",
            "learn": "研究",
            "学习": "研究",
            "entertainment": "娱乐",
            "fun": "娱乐",
            "play": "娱乐",
            "chat": "聊天",
            "chatting": "聊天",
            "聊天": "聊天",
            "沟通": "聊天",
        }

        mapped = alias.get(raw)
        if mapped and mapped in self.categories:
            return mapped

        for category in self.categories:
            if raw in category.lower() or category.lower() in raw:
                return category

        return self.categories[0] if self.categories else "其他"

    def _extract_category_from_text(self, text: str) -> str:
        """Extract category from unstructured text response."""
        text_lower = text.lower()

        for category in self.categories:
            if category.lower() in text_lower:
                return category

        return self.categories[0] if self.categories else "其他"

    def _fallback_classify(self, features: AggregatedFeatures) -> str:
        """Fallback classification using simple keyword matching."""
        text = f"{features.top_app} {' '.join(features.top_window_keywords)}".lower()

        code_signals = [
            "vscode",
            "pycharm",
            "intellij",
            "terminal",
            "git",
            "python",
            "java",
            "javascript",
        ]
        research_signals = ["chrome", "safari", "firefox", "pdf", "arxiv", "paper"]
        entertainment_signals = ["bilibili", "youtube", "video", "game", "music"]

        code_score = sum(1 for signal in code_signals if signal in text)
        research_score = sum(1 for signal in research_signals if signal in text)
        entertainment_score = sum(
            1 for signal in entertainment_signals if signal in text
        )

        if code_score > research_score and code_score > entertainment_score:
            return "写代码" if "写代码" in self.categories else self.categories[0]
        elif research_score > entertainment_score:
            return "研究" if "研究" in self.categories else self.categories[0]
        elif entertainment_score > 0:
            return "娱乐" if "娱乐" in self.categories else self.categories[0]

        return self.categories[0] if self.categories else "其他"
