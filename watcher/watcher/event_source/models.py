from dataclasses import dataclass, field


@dataclass(frozen=True)
class ClickEvent:
    ts: float
    x: int
    y: int
    button: str


@dataclass(frozen=True)
class WindowInfo:
    app_name: str
    window_title: str
    bundle_id: str | None
    timestamp: float


@dataclass
class AggregatedFeatures:
    start_time: float
    end_time: float
    click_count: int = 0
    app_switch_count: int = 0
    active_seconds: float = 0.0
    top_app: str = "Unknown"
    top_window_keywords: list[str] = field(default_factory=list)
    app_distribution: dict[str, int] = field(default_factory=dict)
