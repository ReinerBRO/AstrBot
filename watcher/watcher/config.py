import os
from dataclasses import dataclass
from datetime import time

from dotenv import find_dotenv, load_dotenv


def _load_env():
    env_path = find_dotenv(usecwd=True)
    if env_path:
        load_dotenv(env_path)


def _parse_time(value: str, default: str) -> time:
    text = value or default
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError("时间格式应为 HH:MM")
    hour = int(parts[0])
    minute = int(parts[1])
    return time(hour=hour, minute=minute)


def _parse_categories(value: str | None) -> tuple[str, ...]:
    raw = value or "写代码,研究,娱乐"
    items = [item.strip() for item in raw.split(",") if item.strip()]
    if not items:
        items = ["写代码", "研究", "娱乐"]
    unique: list[str] = []
    for item in items:
        if item not in unique:
            unique.append(item)
    return tuple(unique[:8])


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if not normalized:
        return default
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class Config:
    start_time: time
    end_time: time
    interval_s: int
    min_send_interval_s: int
    max_idle_send_interval_s: int
    hash_diff_threshold: int
    resize_width: int
    jpeg_quality: int
    api_url: str
    api_key: str | None
    api_timeout_s: float
    vl_mode: str
    vl_model: str
    event_summary_model: str
    fusion_summary_model: str
    daily_summary_model: str
    vl_max_tokens: int
    daily_summary_max_tokens: int
    classify_api_url: str
    classify_api_key: str | None
    classify_timeout_s: float
    task_categories: tuple[str, ...]
    enable_event_source: bool
    event_privacy_mask: bool
    event_buffer_window_s: int
    event_trigger_min_clicks: int
    event_switch_trigger: bool
    fusion_vl_weight: float
    fusion_event_weight: float
    fusion_confidence_threshold: float
    event_log_dir: str
    report_dir: str
    log_dir: str
    use_llm_event_classifier: bool
    llm_event_model: str
    llm_event_threshold: float
    llm_event_always: bool
    llm_event_timeout_s: float
    monitor_index: int


def load_config() -> Config:
    _load_env()
    if not os.getenv("VL_API_URL") and os.getenv("LLM_BASE_URL"):
        os.environ["VL_API_URL"] = os.getenv("LLM_BASE_URL")
    if not os.getenv("VL_API_KEY") and os.getenv("LLM_API_KEY"):
        os.environ["VL_API_KEY"] = os.getenv("LLM_API_KEY")
    return Config(
        start_time=_parse_time(os.getenv("WATCH_START", "09:00"), "09:00"),
        end_time=_parse_time(os.getenv("WATCH_END", "18:00"), "18:00"),
        interval_s=int(os.getenv("WATCH_INTERVAL_S", "30")),
        min_send_interval_s=int(os.getenv("MIN_SEND_INTERVAL_S", "300")),
        max_idle_send_interval_s=int(os.getenv("MAX_IDLE_SEND_INTERVAL_S", "900")),
        hash_diff_threshold=int(os.getenv("HASH_DIFF_THRESHOLD", "8")),
        resize_width=int(os.getenv("RESIZE_WIDTH", "960")),
        jpeg_quality=int(os.getenv("JPEG_QUALITY", "70")),
        api_url=os.getenv("VL_API_URL", "").strip(),
        api_key=os.getenv("VL_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("OPENAI_API_KEY"),
        api_timeout_s=float(os.getenv("VL_API_TIMEOUT_S", "30")),
        vl_mode=os.getenv("VL_API_MODE", "").strip() or "auto",
        vl_model=os.getenv("VL_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini",
        event_summary_model=os.getenv("EVENT_SUMMARY_MODEL")
        or os.getenv("LLM_TEXT_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini",
        fusion_summary_model=os.getenv("FUSION_SUMMARY_MODEL")
        or os.getenv("EVENT_SUMMARY_MODEL")
        or os.getenv("LLM_TEXT_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini",
        daily_summary_model=os.getenv("DAILY_SUMMARY_MODEL")
        or os.getenv("LLM_TEXT_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini",
        vl_max_tokens=int(os.getenv("VL_MAX_TOKENS", "256")),
        daily_summary_max_tokens=max(
            128, int(os.getenv("DAILY_SUMMARY_MAX_TOKENS", "1024"))
        ),
        classify_api_url=os.getenv("CLASSIFY_API_URL", "").strip(),
        classify_api_key=os.getenv("CLASSIFY_API_KEY")
        or os.getenv("VL_API_KEY")
        or os.getenv("OPENAI_API_KEY"),
        classify_timeout_s=float(os.getenv("CLASSIFY_API_TIMEOUT_S", "15")),
        task_categories=_parse_categories(os.getenv("TASK_CATEGORIES")),
        enable_event_source=_parse_bool(os.getenv("ENABLE_EVENT_SOURCE"), True),
        event_privacy_mask=_parse_bool(os.getenv("EVENT_PRIVACY_MASK"), False),
        event_buffer_window_s=max(30, int(os.getenv("EVENT_BUFFER_WINDOW_S", "300"))),
        event_trigger_min_clicks=max(
            1, int(os.getenv("EVENT_TRIGGER_MIN_CLICKS", "6"))
        ),
        event_switch_trigger=_parse_bool(os.getenv("EVENT_SWITCH_TRIGGER"), True),
        fusion_vl_weight=max(0.0, float(os.getenv("FUSION_VL_WEIGHT", "0.7"))),
        fusion_event_weight=max(0.0, float(os.getenv("FUSION_EVENT_WEIGHT", "0.3"))),
        fusion_confidence_threshold=min(
            1.0, max(0.0, float(os.getenv("FUSION_CONFIDENCE_THRESHOLD", "0.5")))
        ),
        event_log_dir=os.getenv("EVENT_LOG_DIR", os.getenv("LOG_DIR", "logs")),
        report_dir=os.getenv("REPORT_DIR", "reports"),
        log_dir=os.getenv("LOG_DIR", "logs"),
        use_llm_event_classifier=_parse_bool(
            os.getenv("USE_LLM_EVENT_CLASSIFIER"), False
        ),
        llm_event_model=os.getenv("LLM_EVENT_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini",
        llm_event_threshold=min(
            1.0, max(0.0, float(os.getenv("LLM_EVENT_THRESHOLD", "0.6")))
        ),
        llm_event_always=_parse_bool(os.getenv("LLM_EVENT_ALWAYS"), False),
        llm_event_timeout_s=float(os.getenv("LLM_EVENT_TIMEOUT_S", "10.0")),
        monitor_index=max(1, int(os.getenv("MONITOR_INDEX", "1"))),
    )
