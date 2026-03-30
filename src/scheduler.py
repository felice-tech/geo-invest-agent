"""
Scheduler — registers the daily 07:00 job using APScheduler with full
timezone support.  Call start_scheduler() to block and run indefinitely.
"""
from __future__ import annotations

import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

import config


def start_scheduler(job_fn) -> None:
    """
    Block the current thread, firing job_fn every day at REPORT_TIME
    in the configured TIMEZONE.

    Parameters
    ----------
    job_fn : callable
        Zero-argument function to execute (e.g. ``run_pipeline``).
    """
    tz = pytz.timezone(config.TIMEZONE)
    hour, minute = _parse_time(config.REPORT_TIME)

    scheduler = BlockingScheduler(timezone=tz)
    scheduler.add_job(
        job_fn,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=tz),
        id="daily_brief",
        name=f"Daily Brief @ {config.REPORT_TIME} {config.TIMEZONE}",
        misfire_grace_time=300,   # tolerate up to 5 min late start
    )

    logger.info(
        f"Scheduler started — daily brief at "
        f"{config.REPORT_TIME} {config.TIMEZONE}"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


def _parse_time(hhmm: str) -> tuple[int, int]:
    parts = hhmm.strip().split(":")
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0
