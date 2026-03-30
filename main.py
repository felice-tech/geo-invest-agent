"""
Geo-Invest Agent — entry point.

Usage
-----
  python main.py --run-now          # run pipeline immediately, deliver report
  python main.py --run-now --dry-run # run pipeline, print report, do NOT deliver
  python main.py --schedule         # block and run on schedule (daily at 07:00)
  python main.py --run-now --date 2026-03-30  # (future) run for a specific date
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime

from loguru import logger

import config
from src.rss_fetcher import RSSFetcher
from src.filter_engine import FilterEngine
from src.scoring_engine import ScoringEngine
from src.llm_processor import LLMProcessor
from src.delivery import Delivery
from src.scheduler import start_scheduler
from src.memory import MemoryStore


# ── Logging setup ─────────────────────────────────────────────────────────────

logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    level="INFO",
)
logger.add(
    "data/agent.log",
    rotation="7 days",
    retention="30 days",
    level="DEBUG",
    encoding="utf-8",
)


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_pipeline(dry_run: bool = False) -> str:
    """
    Full pipeline:
      1. Fetch RSS articles
      2. Filter by relevance keywords
      3. Score and rank articles
      4. Analyse with LLM
      5. Save report to memory
      6. Deliver (unless dry_run)

    Returns the generated report text.
    """
    run_ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    logger.info(f"═══ Pipeline started [{run_ts}] ═══")

    # 1 — Fetch
    fetcher = RSSFetcher()
    raw_articles = fetcher.fetch_all()

    if not raw_articles:
        logger.warning("No articles fetched — check RSS sources and network")

    # 2 — Filter
    filtered = FilterEngine().filter(raw_articles)

    # 3 — Score & rank
    top_articles = ScoringEngine().score_and_rank(filtered)

    # 4 — LLM analysis
    processor = LLMProcessor()
    report = processor.analyze(top_articles)

    # 5 — Persist
    memory = MemoryStore()
    articles_meta = [
        {
            "title": a.title,
            "source": a.source,
            "link": a.link,
            "published": a.published.isoformat(),
            "total_score": a.total_score,
            "categories": a.categories_matched,
        }
        for a in top_articles
    ]
    memory.save_report(report, articles_meta)

    # 6 — Deliver
    if dry_run:
        logger.info("Dry-run mode — skipping delivery")
        print("\n" + "=" * 70)
        print(report)
        print("=" * 70 + "\n")
    else:
        Delivery().send(report)

    logger.info("═══ Pipeline complete ═══")
    return report


# ── CLI ───────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Geopolitical Investment Intelligence Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--run-now",
        action="store_true",
        help="Execute the pipeline immediately",
    )
    mode.add_argument(
        "--schedule",
        action="store_true",
        help=f"Start the scheduler (daily at {config.REPORT_TIME} {config.TIMEZONE})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate report but print to stdout instead of delivering",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    if args.run_now:
        run_pipeline(dry_run=args.dry_run)

    elif args.schedule:
        if args.dry_run:
            logger.warning(
                "--dry-run with --schedule: reports will print rather than be delivered"
            )
        start_scheduler(lambda: run_pipeline(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
