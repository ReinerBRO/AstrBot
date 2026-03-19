from datetime import datetime
from pathlib import Path

from watcher.config import Config


class Reporter:
    def __init__(self, config: Config):
        self.report_dir = Path(config.report_dir)
        self.log_dir = Path(config.log_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def append_report(
        self,
        timestamp: datetime,
        summary: str,
        category: str,
        tree_id: str | None = None,
        source: str = "vl",
        reason: str = "",
        vl_category: str | None = None,
        event_category: str | None = None,
    ):
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H:%M")
        path = self.report_dir / f"{date_str}.md"
        tree_tag = f" {{tree:{tree_id}}}" if tree_id else ""
        meta = ""
        if source != "vl":
            reason_text = reason.strip()[:120]
            reason_part = f"; reason={reason_text}" if reason_text else ""
            origin_part = ""
            if vl_category or event_category:
                origin_part = (
                    f"; vl={vl_category or '-'}; event={event_category or '-'}"
                )
            meta = f" (source={source}{origin_part}{reason_part})"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"- {time_str} [{category}]{tree_tag} {summary}{meta}\n")

    def log_event(self, timestamp: datetime, message: str):
        date_str = timestamp.strftime("%Y-%m-%d")
        time_str = timestamp.strftime("%H:%M:%S")
        path = self.log_dir / f"{date_str}.log"
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{time_str} {message}\n")
