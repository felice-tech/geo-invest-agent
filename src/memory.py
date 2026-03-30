"""
Memory Store — persists daily reports to disk and provides a 7-day
trend summary that can be injected into future LLM prompts.

This is the foundation for the "Memory Layer" future enhancement:
  - Store trends from the past 7 days
  - Detect escalation patterns
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

# Reports are stored under <project_root>/data/reports/
_REPORTS_DIR = Path(__file__).parent.parent / "data" / "reports"


class MemoryStore:
    def __init__(self, reports_dir: Path = _REPORTS_DIR):
        self.dir = reports_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    # ── Write ──────────────────────────────────────────────────────────────────

    def save_report(self, report: str, articles_meta: list[dict] | None = None) -> Path:
        """Persist today's report as JSON.  Returns the file path."""
        today = datetime.now().strftime("%Y-%m-%d")
        path = self.dir / f"{today}.json"

        payload = {
            "date": today,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "report": report,
            "articles": articles_meta or [],
        }
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Report saved → {path}")
        return path

    # ── Read ───────────────────────────────────────────────────────────────────

    def load_recent(self, days: int = 7) -> list[dict]:
        """Return list of report payloads from the last `days` days, oldest first."""
        cutoff = datetime.now() - timedelta(days=days)
        records: list[dict] = []

        for fp in sorted(self.dir.glob("*.json")):
            try:
                date = datetime.strptime(fp.stem, "%Y-%m-%d")
            except ValueError:
                continue
            if date >= cutoff:
                try:
                    records.append(json.loads(fp.read_text(encoding="utf-8")))
                except Exception as exc:
                    logger.warning(f"Could not read {fp}: {exc}")

        return records

    def trend_summary(self, days: int = 7) -> str:
        """
        Build a compact text summary of recent reports for injection into
        the next LLM call as additional context (escalation detection).
        """
        records = self.load_recent(days)
        if not records:
            return ""

        lines = [f"--- TREND CONTEXT (last {days} days) ---"]
        for rec in records:
            lines.append(f"\n[{rec['date']}]")
            # Include only the first 400 chars of each past report as context
            snippet = rec.get("report", "")[:400].replace("\n", " ")
            lines.append(snippet + " …")
        lines.append("--- END TREND CONTEXT ---\n")
        return "\n".join(lines)
