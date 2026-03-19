import unittest
from unittest.mock import Mock, patch

from app.web import create_app


class CardsApiTest(unittest.TestCase):
    def setUp(self):
        self.service = Mock()
        self.service.cards_data.return_value = {
            "cards": [],
            "total": 0,
            "page": 1,
            "page_size": 50,
            "has_more": False,
            "stats": {
                "total_count": 0,
                "category_counts": {},
                "total_active_seconds": 0,
                "avg_interval_seconds": 0,
                "date_range": {"start": "2026-02-11", "end": "2026-02-11"},
            },
        }
        self.service.update_card.return_value = {
            "ok": True,
            "message": "卡片已更新",
            "card": {"id": "20260211-0941-001"},
        }
        self.service.delete_card.return_value = {
            "ok": True,
            "message": "卡片已删除",
            "card_id": "20260211-0941-001",
        }
        self.service.export_cards.return_value = (
            "id,date\n1,2026-02-11\n",
            "watcher-report-20260211-20260211.csv",
        )

    def _client(self):
        with patch("app.web.WatcherService", return_value=self.service):
            app = create_app()
            app.testing = True
            return app.test_client()

    def test_get_cards_success(self):
        client = self._client()
        resp = client.get(
            "/api/cards?date=2026-02-11&categories=写代码,研究&tree_ids=tree-a&page=2&page_size=10&sort=time_asc"
        )
        self.assertEqual(resp.status_code, 200)
        self.service.cards_data.assert_called_once()
        kwargs = self.service.cards_data.call_args.kwargs
        self.assertEqual(kwargs["date_text"], "2026-02-11")
        self.assertEqual(kwargs["categories"], ["写代码", "研究"])
        self.assertEqual(kwargs["tree_ids"], ["tree-a"])
        self.assertEqual(kwargs["page"], 2)
        self.assertEqual(kwargs["page_size"], 10)
        self.assertEqual(kwargs["sort"], "time_asc")

    def test_get_cards_invalid_page(self):
        client = self._client()
        resp = client.get("/api/cards?page=abc")
        self.assertEqual(resp.status_code, 400)
        self.service.cards_data.assert_not_called()

    def test_put_delete_and_export(self):
        client = self._client()

        put_resp = client.put(
            "/api/cards/20260211-0941-001",
            json={"summary": "updated", "category": "研究"},
        )
        self.assertEqual(put_resp.status_code, 200)
        self.service.update_card.assert_called_once()

        del_resp = client.delete("/api/cards/20260211-0941-001")
        self.assertEqual(del_resp.status_code, 200)
        self.service.delete_card.assert_called_once()

        export_resp = client.post(
            "/api/cards/export",
            json={"format": "csv", "filters": {"date": "2026-02-11"}},
        )
        self.assertEqual(export_resp.status_code, 200)
        self.assertIn("attachment; filename=", export_resp.headers.get("Content-Disposition", ""))
        self.service.export_cards.assert_called_once()


if __name__ == "__main__":
    unittest.main()
