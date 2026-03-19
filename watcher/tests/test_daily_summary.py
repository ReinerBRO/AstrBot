from types import SimpleNamespace
from unittest.mock import patch

from app.service import WatcherService
from app.web import create_app
from watcher.daily_summary import (
    SummaryResult,
    aggregate_stats,
    build_timeline_segments,
    generate_llm_summary,
    stream_llm_summary,
)
from watcher.report_parser import ReportEntry


def _entries() -> list[ReportEntry]:
    return [
        ReportEntry(
            time="09:00",
            category="写代码",
            tree_id="tree-a",
            summary="编写接口",
            source="vl",
            meta={},
        ),
        ReportEntry(
            time="09:10",
            category="写代码",
            tree_id="tree-a",
            summary="修复问题",
            source="vl",
            meta={},
        ),
        ReportEntry(
            time="09:40",
            category="研究",
            tree_id="tree-a",
            summary="阅读文档",
            source="vl",
            meta={},
        ),
    ]


def _config(report_dir: str = "reports") -> SimpleNamespace:
    return SimpleNamespace(
        api_url="https://api.example.com/v1",
        api_key="test-key",
        api_timeout_s=30.0,
        vl_mode="auto",
        vl_model="fallback-model",
        event_summary_model="fallback-model",
        fusion_summary_model="fallback-model",
        daily_summary_model="test-model",
        vl_max_tokens=256,
        daily_summary_max_tokens=512,
        classify_api_url="",
        classify_api_key=None,
        classify_timeout_s=15.0,
        task_categories=("写代码", "研究", "娱乐"),
        report_dir=report_dir,
    )


class _FakeStreamResponse:
    def __init__(self, lines: list[str]):
        self._lines = lines

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    @staticmethod
    def raise_for_status() -> None:
        return None

    def iter_lines(self, decode_unicode: bool = True):
        return iter(self._lines)


def _collect_stream_tokens(gen):
    chunks: list[str] = []
    while True:
        try:
            chunks.append(next(gen))
        except StopIteration as stop:
            return chunks, stop.value


def test_aggregate_stats_counts_duration_and_range():
    stats = aggregate_stats(_entries())

    assert stats.total_entries == 3
    assert stats.time_range.start == "09:00"
    assert stats.time_range.end == "09:40"
    assert stats.active_duration_min == 45

    assert stats.categories["写代码"].count == 2
    assert stats.categories["写代码"].duration_min == 40
    assert stats.categories["研究"].count == 1
    assert stats.categories["研究"].duration_min == 5


def test_build_timeline_segments_splits_on_gap_and_category_change():
    entries = [
        ReportEntry("09:00", "写代码", "tree-a", "编写接口", "vl", {}),
        ReportEntry("09:10", "写代码", "tree-a", "修复问题", "vl", {}),
        ReportEntry("09:50", "写代码", "tree-a", "代码走查", "vl", {}),
        ReportEntry("10:00", "研究", "tree-a", "阅读文档", "vl", {}),
    ]

    segments = build_timeline_segments(entries)
    assert len(segments) == 3

    assert segments[0].start == "09:00"
    assert segments[0].end == "09:10"
    assert segments[0].main_category == "写代码"

    assert segments[1].start == "09:50"
    assert segments[1].end == "09:50"
    assert segments[1].main_category == "写代码"

    assert segments[2].start == "10:00"
    assert segments[2].end == "10:00"
    assert segments[2].main_category == "研究"


def test_generate_llm_summary_parses_json_payload():
    entries = _entries()
    stats = aggregate_stats(entries)
    config = SimpleNamespace(
        daily_summary_model="test-model",
        daily_summary_max_tokens=512,
        vl_model="fallback-model",
    )

    fake_client = SimpleNamespace()
    fake_client.max_tokens = 0
    fake_client._chat_openai = lambda messages, model: (
        '{"summary":"今天主要完成开发和研究工作。",'
        '"highlights":["实现日报接口","优化统计逻辑"]}'
    )

    with patch("watcher.daily_summary.VLClient", return_value=fake_client):
        result = generate_llm_summary(entries, stats, config)

    assert "开发和研究" in result.summary
    assert "实现日报接口" in result.highlights
    assert len(result.highlights) >= 3


def test_generate_llm_summary_falls_back_when_llm_fails():
    entries = _entries()
    stats = aggregate_stats(entries)
    config = SimpleNamespace(
        daily_summary_model="test-model",
        daily_summary_max_tokens=512,
        vl_model="fallback-model",
    )

    with patch("watcher.daily_summary.VLClient", side_effect=RuntimeError("boom")):
        result = generate_llm_summary(entries, stats, config)

    assert "今天共记录" in result.summary
    assert len(result.highlights) >= 1


def test_stream_llm_summary_reads_sse_tokens():
    entries = _entries()
    stats = aggregate_stats(entries)
    config = _config()
    lines = [
        'data: {"choices":[{"delta":{"content":"今天"}}]}',
        'data: {"choices":[{"delta":{"content":"主要完成接口开发。"}}]}',
        "data: [DONE]",
    ]

    with patch(
        "watcher.daily_summary.requests.post",
        return_value=_FakeStreamResponse(lines),
    ):
        chunks, result = _collect_stream_tokens(stream_llm_summary(entries, stats, config))

    assert "".join(chunks) == "今天主要完成接口开发。"
    assert isinstance(result, SummaryResult)
    assert result.summary == "今天主要完成接口开发。"
    assert len(result.highlights) >= 3


def test_stream_llm_summary_falls_back_to_non_stream():
    entries = _entries()
    stats = aggregate_stats(entries)
    config = _config()
    fake_client = SimpleNamespace(
        max_tokens=0,
        _chat_openai=lambda messages, model: "今天主要推进日报总结功能。",
    )

    with patch("watcher.daily_summary.requests.post", side_effect=RuntimeError("boom")):
        with patch("watcher.daily_summary.VLClient", return_value=fake_client):
            chunks, result = _collect_stream_tokens(
                stream_llm_summary(entries, stats, config)
            )

    assert chunks == ["今天主要推进日报总结功能。"]
    assert isinstance(result, SummaryResult)
    assert result.summary == "今天主要推进日报总结功能。"
    assert len(result.highlights) >= 3


def test_daily_summary_stream_emits_cached_event():
    config = _config()
    cached_payload = {
        "date": "2026-02-13",
        "generated_at": "2026-02-13T09:30:00",
        "stats": {},
        "timeline_segments": [],
        "summary": "cached summary",
        "highlights": ["cached highlight"],
    }
    with patch("app.service.load_config", return_value=config):
        service = WatcherService()

    with patch("app.service.load_summary_cache", return_value=cached_payload):
        events = list(service.daily_summary_stream("2026-02-13", force=False))

    assert events == [("cached", cached_payload)]


def test_daily_summary_stream_emits_phase_token_done_and_persists_cache():
    config = _config()

    def _fake_stream(entries, stats, cfg):
        yield "今"
        yield "天"
        return SummaryResult(
            summary="今天完成了流式日报接口。",
            highlights=["新增 SSE 端点", "补充流式单测", "接入缓存策略"],
        )

    with patch("app.service.load_config", return_value=config):
        service = WatcherService()

    with patch("app.service.parse_daily_report", return_value=_entries()):
        with patch("app.service.stream_llm_summary", side_effect=_fake_stream):
            with patch("app.service.save_summary_cache") as save_mock:
                events = list(service.daily_summary_stream("2026-02-13", force=True))

    event_names = [name for name, _ in events]
    assert event_names[:3] == ["phase", "phase", "phase"]
    assert event_names.count("token") == 2
    assert event_names[-3:] == ["highlights", "segments", "done"]
    assert events[-1][1]["summary"] == "今天完成了流式日报接口。"
    assert len(events[-1][1]["timeline_segments"]) >= 1
    save_mock.assert_called_once()


def test_daily_summary_stream_route_returns_sse_format():
    service = SimpleNamespace()

    def _stream(date_text: str, force: bool = False):
        assert date_text == "2026-02-13"
        assert force is True
        yield ("phase", {"phase": "parsing", "message": "正在解析活动记录..."})
        yield (
            "done",
            {
                "date": "2026-02-13",
                "generated_at": "2026-02-13T10:00:00",
                "stats": {},
                "timeline_segments": [],
                "summary": "done",
                "highlights": [],
            },
        )

    service.daily_summary_stream = _stream

    with patch("app.web.WatcherService", return_value=service):
        app = create_app()
        app.testing = True
        client = app.test_client()
        resp = client.get("/api/daily-summary/stream?date=2026-02-13&force=true")

    body = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.content_type
    assert "event: phase" in body
    assert "event: done" in body
