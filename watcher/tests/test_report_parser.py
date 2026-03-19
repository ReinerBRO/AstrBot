from pathlib import Path

from watcher.report_parser import parse_daily_report


def test_parse_daily_report_basic_and_meta(tmp_path: Path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / "2026-02-11.md"
    report.write_text(
        "\n".join(
            [
                "- 09:10 [写代码] {tree:tree-a} 编写接口文档",
                "- 09:40 [研究] {tree:tree-a} 阅读论文 (source=fusion; vl=写代码; event=研究; reason=test)",
                "- 09:05 [娱乐] 浏览网页",
                "bad-line",
            ]
        ),
        encoding="utf-8",
    )

    entries = parse_daily_report("2026-02-11", str(report_dir))
    assert len(entries) == 3

    assert entries[0].time == "09:05"
    assert entries[0].category == "娱乐"
    assert entries[0].tree_id is None

    assert entries[1].time == "09:10"
    assert entries[1].category == "写代码"
    assert entries[1].tree_id == "tree-a"

    assert entries[2].time == "09:40"
    assert entries[2].source == "vl+event"
    assert entries[2].meta["source"] == "fusion"
    assert entries[2].meta["vl"] == "写代码"


def test_parse_daily_report_missing_file_returns_empty(tmp_path: Path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    entries = parse_daily_report("2026-02-12", str(report_dir))
    assert entries == []


def test_parse_daily_report_invalid_date_raises(tmp_path: Path):
    report_dir = tmp_path / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)

    try:
        parse_daily_report("2026/02/11", str(report_dir))
        assert False, "expected ValueError"
    except ValueError:
        pass
