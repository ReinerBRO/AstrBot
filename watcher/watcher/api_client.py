import base64
import json
import re
from datetime import datetime

import requests

from watcher.config import Config


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_json_payload(text: str) -> dict | None:
    raw = (text or "").strip()
    if not raw:
        return None
    candidates: list[str] = [raw]
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", raw, flags=re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1))
    inline = re.search(r"(\{[\s\S]*\})", raw)
    if inline:
        candidates.append(inline.group(1))
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except Exception:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _normalize_category(label: str, categories: tuple[str, ...]) -> str | None:
    if not categories:
        return None
    raw = _normalize_spaces((label or "").lower())
    if not raw:
        return None
    for category in categories:
        if raw == category.lower():
            return category

    alias = {
        "code": "写代码",
        "coding": "写代码",
        "programming": "写代码",
        "develop": "写代码",
        "开发": "写代码",
        "写代码": "写代码",
        "research": "研究",
        "study": "研究",
        "learn": "研究",
        "学习": "研究",
        "researching": "研究",
        "研究": "研究",
        "entertainment": "娱乐",
        "fun": "娱乐",
        "play": "娱乐",
        "game": "娱乐",
        "video": "娱乐",
        "chat": "娱乐",
        "chatting": "娱乐",
        "social": "娱乐",
        "message": "娱乐",
        "messages": "娱乐",
        "wechat": "娱乐",
        "weixin": "娱乐",
        "qq": "娱乐",
        "telegram": "娱乐",
        "discord": "娱乐",
        "微信": "娱乐",
        "对话": "娱乐",
        "沟通": "娱乐",
        "闲聊": "娱乐",
        "聊天": "娱乐",
        "娱乐": "娱乐",
    }
    mapped = alias.get(raw)
    if mapped and mapped in categories:
        return mapped

    for category in categories:
        if raw in category.lower() or category.lower() in raw:
            return category
    return None


def _keyword_classify(summary: str, categories: tuple[str, ...]) -> str:
    text = (summary or "").lower()
    if not categories:
        return "写代码"

    scores = {category: 0 for category in categories}

    code_signals = [
        "code",
        "coding",
        "programming",
        "python",
        "java",
        "javascript",
        "typescript",
        "golang",
        "rust",
        "api",
        "debug",
        "bug",
        "git",
        "pull request",
        "commit",
        "repo",
        "terminal",
        "shell",
        "开发",
        "代码",
        "编程",
        "调试",
        "接口",
        "函数",
        "部署",
    ]
    research_signals = [
        "research",
        "study",
        "paper",
        "read",
        "docs",
        "document",
        "analysis",
        "report",
        "summary",
        "文档",
        "学习",
        "研究",
        "论文",
        "资料",
        "分析",
        "总结",
        "报告",
    ]
    entertainment_signals = [
        "video",
        "music",
        "game",
        "movie",
        "bilibili",
        "youtube",
        "tiktok",
        "douyin",
        "娱乐",
        "追剧",
        "游戏",
        "电影",
        "刷视频",
        "一起玩",
        "玩一玩",
    ]
    communication_signals = [
        "chat",
        "wechat",
        "weixin",
        "qq",
        "telegram",
        "discord",
        "slack",
        "meeting",
        "call",
        "zoom",
        "teams",
        "message",
        "聊天",
        "微信",
        "讨论",
        "沟通",
        "会议",
    ]
    work_discussion_signals = [
        "需求",
        "任务",
        "排期",
        "方案",
        "项目",
        "上线",
        "迭代",
        "问题",
        "修复",
    ]
    fun_discussion_signals = [
        "一起玩",
        "聚餐",
        "吃饭",
        "周末",
        "约",
        "旅游",
        "看电影",
    ]

    def add_score(target: str, value: int):
        if target in scores:
            scores[target] += value

    for token in code_signals:
        if token in text:
            add_score("写代码", 3)
    for token in research_signals:
        if token in text:
            add_score("研究", 3)
    for token in entertainment_signals:
        if token in text:
            add_score("娱乐", 3)

    has_communication = any(token in text for token in communication_signals)
    if has_communication:
        add_score(
            "写代码",
            1 if any(token in text for token in work_discussion_signals) else 0,
        )
        add_score("研究", 1 if ("讨论" in text and "方案" in text) else 0)
        add_score(
            "娱乐", 2 if any(token in text for token in fun_discussion_signals) else 0
        )

    best_category = max(scores, key=scores.get)
    best_score = scores[best_category]
    if best_score <= 0:
        if has_communication and "研究" in scores:
            return "研究"
        return categories[0]
    return best_category


def _post_classify(
    url: str,
    key: str | None,
    timeout: float,
    summary: str,
    categories: tuple[str, ...],
) -> str:
    payload = {"text": summary, "labels": list(categories)}
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    resp = requests.post(
        url, data=json.dumps(payload), headers=headers, timeout=timeout
    )
    resp.raise_for_status()
    try:
        data = resp.json()
        label = data.get("label") or data.get("category") or data.get("result")
        mapped = _normalize_category(str(label or ""), categories)
        if mapped:
            return mapped
        mapped = _normalize_category(json.dumps(data, ensure_ascii=False), categories)
        if mapped:
            return mapped
        return _keyword_classify(summary, categories)
    except ValueError:
        return _keyword_classify(summary, categories)


def classify_text(config: Config, summary: str) -> str:
    categories = config.task_categories
    if config.classify_api_url:
        try:
            return _post_classify(
                config.classify_api_url,
                config.classify_api_key,
                config.classify_timeout_s,
                summary,
                categories,
            )
        except Exception:
            return _keyword_classify(summary, categories)
    return _keyword_classify(summary, categories)


class VLClient:
    def __init__(self, config: Config):
        if not config.api_url:
            raise ValueError("VL_API_URL 未设置")
        self.url = config.api_url
        self.api_key = config.api_key
        self.timeout = config.api_timeout_s
        self.mode = config.vl_mode
        self.model = config.vl_model
        self.event_summary_model = config.event_summary_model
        self.fusion_summary_model = config.fusion_summary_model
        self.max_tokens = config.vl_max_tokens
        self.classify_url = config.classify_api_url
        self.classify_key = config.classify_api_key
        self.classify_timeout = config.classify_timeout_s
        self.categories = config.task_categories

    def analyze(self, image_bytes: bytes, timestamp: datetime) -> str:
        summary, _ = self.analyze_with_category(image_bytes, timestamp)
        return summary

    def analyze_with_category(
        self, image_bytes: bytes, timestamp: datetime
    ) -> tuple[str, str | None]:
        mode = self._resolve_mode()
        if mode == "openai":
            return self._analyze_openai_with_category(image_bytes, timestamp)
        return self._analyze_simple_with_category(image_bytes, timestamp)

    def _resolve_mode(self) -> str:
        if self.mode and self.mode != "auto":
            return self.mode
        if self.url.rstrip("/").endswith("/v1"):
            return "openai"
        return "simple"

    def _analyze_simple_with_category(
        self, image_bytes: bytes, timestamp: datetime
    ) -> tuple[str, str | None]:
        payload = {
            "timestamp": timestamp.isoformat(),
            "image_base64": base64.b64encode(image_bytes).decode("utf-8"),
            "image_format": "jpeg",
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(
            self.url, data=json.dumps(payload), headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        try:
            data = resp.json()
            summary = _normalize_spaces(
                str(data.get("summary") or data.get("text") or resp.text.strip())
            )
            category = _normalize_category(
                str(data.get("category") or data.get("label") or ""),
                self.categories,
            )
            return summary, category
        except ValueError:
            return _normalize_spaces(resp.text.strip()), None

    def _analyze_openai_with_category(
        self, image_bytes: bytes, timestamp: datetime
    ) -> tuple[str, str | None]:
        url = self.url
        if url.rstrip("/").endswith("/v1"):
            url = url.rstrip("/") + "/chat/completions"
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        category_text = (
            "、".join(self.categories) if self.categories else "写代码、研究、娱乐"
        )
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是工作日志助手。请严格输出 JSON 对象，不要输出其他文字。"
                        f"字段：summary, category。category 只能是 [{category_text}] 之一。"
                        "summary 用一句话描述当前活动。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"时间：{timestamp.isoformat()}"},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                    ],
                },
            ],
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(
            url, data=json.dumps(payload), headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        try:
            data = resp.json()
            content = str(data["choices"][0]["message"]["content"]).strip()
        except Exception:
            content = resp.text.strip()
        parsed = _extract_json_payload(content)
        if isinstance(parsed, dict):
            summary = _normalize_spaces(
                str(parsed.get("summary") or parsed.get("text") or "")
            )
            category = _normalize_category(
                str(parsed.get("category") or parsed.get("label") or ""),
                self.categories,
            )
            if summary:
                return summary, category
        return _normalize_spaces(content), None

    def _chat_openai(self, messages: list[dict], model: str) -> str:
        url = self.url
        if url.rstrip("/").endswith("/v1"):
            url = url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": messages,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        resp = requests.post(
            url, data=json.dumps(payload), headers=headers, timeout=self.timeout
        )
        resp.raise_for_status()
        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return resp.text.strip()

    def summarize_event_text(self, event_text: str, timestamp: datetime) -> str:
        mode = self._resolve_mode()
        if mode != "openai":
            return _normalize_spaces(event_text)
        messages = [
            {
                "role": "system",
                "content": "你是工作日志助手。请基于事件信息用一句话总结用户正在做什么。",
            },
            {
                "role": "user",
                "content": f"时间：{timestamp.isoformat()}\n事件信息：{event_text}",
            },
        ]
        return self._chat_openai(messages, self.event_summary_model)

    def summarize_fusion_text(
        self,
        screenshot_summary: str,
        event_summary: str,
        timestamp: datetime,
    ) -> str:
        mode = self._resolve_mode()
        if mode != "openai":
            return _normalize_spaces(f"{screenshot_summary} {event_summary}")
        messages = [
            {
                "role": "system",
                "content": "你是工作日志助手。请融合视觉总结与事件总结，输出一句话最终工作记录。",
            },
            {
                "role": "user",
                "content": (
                    f"时间：{timestamp.isoformat()}\n"
                    f"视觉总结：{screenshot_summary}\n"
                    f"事件总结：{event_summary}"
                ),
            },
        ]
        return self._chat_openai(messages, self.fusion_summary_model)

    def classify(self, summary: str) -> str:
        if self.classify_url:
            try:
                return _post_classify(
                    self.classify_url,
                    self.classify_key,
                    self.classify_timeout,
                    summary,
                    self.categories,
                )
            except Exception:
                return _keyword_classify(summary, self.categories)
        return _keyword_classify(summary, self.categories)
