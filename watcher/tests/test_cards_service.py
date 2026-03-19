import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.service import WatcherService
from watcher.config import Config


def _build_config(report_dir: str, log_dir: str) -> Config:
    from datetime import time

    return Config(
        start_time=time(9, 0),
        end_time=time(18, 0),
        interval_s=30,
        min_send_interval_s=300,
        max_idle_send_interval_s=900,
        hash_diff_threshold=8,
        resize_width=960,
        jpeg_quality=70,
        api_url="https://api.example.com",
        api_key="test-key",
        api_timeout_s=30.0,
        vl_mode="auto",
        vl_model="gpt-4o-mini",
        event_summary_model="gpt-4o-mini",
        fusion_summary_model="gpt-4o-mini",
        daily_summary_model="gpt-4o-mini",
        vl_max_tokens=256,
        daily_summary_max_tokens=1024,
        classify_api_url="",
        classify_api_key=None,
        classify_timeout_s=15.0,
        task_categories=("写代码", "研究", "娱乐"),
        enable_event_source=True,
        event_privacy_mask=False,
        event_buffer_window_s=300,
        event_trigger_min_clicks=6,
        event_switch_trigger=True,
        fusion_vl_weight=0.7,
        fusion_event_weight=0.3,
        fusion_confidence_threshold=0.5,
        event_log_dir=log_dir,
        report_dir=report_dir,
        log_dir=log_dir,
        use_llm_event_classifier=False,
        llm_event_model="gpt-4o-mini",
        llm_event_threshold=0.6,
        llm_event_always=False,
        llm_event_timeout_s=10.0,
        monitor_index=1,
    )


class CardsServiceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.report_dir = Path(self.tmp.name) / "reports"
        self.log_dir = Path(self.tmp.name) / "logs"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.config = _build_config(str(self.report_dir), str(self.log_dir))
        self._seed_files()
        with patch("app.service.load_config", return_value=self.config):
            self.service = WatcherService()

    def tearDown(self):
        self.tmp.cleanup()

    def _seed_files(self):
        report = self.report_dir / "2026-02-11.md"
        report.write_text(
            "\n".join(
                [
                    "- 09:41 [写代码] {tree:tree-a} 第一条摘要 (source=fusion; vl=写代码; event=研究; reason=close confidence (vl=0.62, event=0.55), weighted blend)",
                    "- 10:01 [研究] {tree:tree-a} 第二条研究",
                    "- 10:21 [娱乐] {tree:tree-b} 第三条娱乐",
                ]
            ),
            encoding="utf-8",
        )
        tree_meta = {
            "trees": [
                {
                    "id": "tree-a",
                    "name": "Morning Tree",
                    "created_at": "2026-02-11T09:40:00",
                    "deleted": False,
                },
                {
                    "id": "tree-b",
                    "name": "Leisure Tree",
                    "created_at": "2026-02-11T10:20:00",
                    "deleted": False,
                },
            ]
        }
        (self.report_dir / "2026-02-11.trees.json").write_text(
            json.dumps(tree_meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def test_cards_data_filters_and_pagination(self):
        data = self.service.cards_data(
            date_text="2026-02-11",
            categories=["研究", "娱乐"],
            page=1,
            page_size=1,
            sort="time_desc",
        )
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 1)
        self.assertTrue(data["has_more"])
        self.assertEqual(len(data["cards"]), 1)
        self.assertEqual(data["cards"][0]["id"], "20260211-1021-003")

    def test_cards_data_search_and_meta(self):
        data = self.service.cards_data(date_text="2026-02-11", search="第一条")
        self.assertEqual(data["total"], 1)
        card = data["cards"][0]
        self.assertEqual(card["source"], "vl+event")
        self.assertEqual(card["vl_category"], "写代码")
        self.assertEqual(card["event_category"], "研究")
        self.assertGreater(card["confidence"], 0)
        self.assertEqual(card["tree_name"], "Morning Tree")

    def test_update_card(self):
        card_id = "20260211-0941-001"
        result = self.service.update_card(
            card_id=card_id,
            summary="更新后的摘要",
            category="research",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["card"]["category"], "研究")
        self.assertEqual(result["card"]["summary"], "更新后的摘要")

        lines = (self.report_dir / "2026-02-11.md").read_text(encoding="utf-8").splitlines()
        self.assertIn("[研究]", lines[0])
        self.assertIn("更新后的摘要", lines[0])
        self.assertIn("(source=fusion;", lines[0])

    def test_delete_card_marks_tree_deleted_when_orphan(self):
        card_id = "20260211-1021-003"
        result = self.service.delete_card(card_id=card_id)
        self.assertTrue(result["ok"])

        lines = (self.report_dir / "2026-02-11.md").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        meta = json.loads(
            (self.report_dir / "2026-02-11.trees.json").read_text(encoding="utf-8")
        )
        row = next(item for item in meta["trees"] if item["id"] == "tree-b")
        self.assertTrue(row["deleted"])

    def test_export_cards_formats(self):
        content_md, filename_md = self.service.export_cards(
            format="markdown",
            filters={"date": "2026-02-11"},
        )
        self.assertTrue(filename_md.endswith(".md"))
        self.assertIn("[写代码]", content_md)

        content_json, filename_json = self.service.export_cards(
            format="json",
            filters={"date": "2026-02-11"},
        )
        self.assertTrue(filename_json.endswith(".json"))
        payload = json.loads(content_json)
        self.assertEqual(len(payload["cards"]), 3)

        content_csv, filename_csv = self.service.export_cards(
            format="csv",
            filters={"date": "2026-02-11"},
        )
        self.assertTrue(filename_csv.endswith(".csv"))
        self.assertIn("id,date,time,category,summary", content_csv)


if __name__ == "__main__":
    unittest.main()
