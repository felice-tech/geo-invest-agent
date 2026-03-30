"""
RSS Fetcher — pulls articles from all configured sources, deduplicates,
and returns only articles published within the last 24 hours.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests
from loguru import logger

import config

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; geo-invest-agent/1.0)"}


def strip_html(text: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&[a-z]+;", " ", clean)   # basic HTML entities
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


@dataclass
class Article:
    title: str
    summary: str
    link: str
    source: str
    source_weight: float
    published: datetime

    # Populated by ScoringEngine
    economic_impact: int = 0
    urgency: int = 0
    duration: int = 0
    total_score: float = 0.0
    categories_matched: list[str] = field(default_factory=list)

    def age_hours(self) -> float:
        now = datetime.now(timezone.utc)
        pub = self.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        return max(0.0, (now - pub).total_seconds() / 3600)

    def age_label(self) -> str:
        h = self.age_hours()
        if h < 1:
            return f"{int(h * 60)}m ago"
        if h < 24:
            return f"{int(h)}h ago"
        return f"{int(h / 24)}d ago"

    def text_blob(self) -> str:
        """Lowercase combined text for keyword matching."""
        return f"{self.title} {self.summary}".lower()


class RSSFetcher:
    def __init__(
        self,
        sources: list[dict] = config.RSS_SOURCES,
        max_articles: int = config.MAX_ARTICLES,
    ):
        self.sources = sources
        self.max_articles = max_articles

    # ── Public ─────────────────────────────────────────────────────────────────

    def fetch_all(self) -> list[Article]:
        """Fetch all sources, deduplicate, filter to last 24 h, sort newest-first."""
        all_articles: list[Article] = []
        seen_links: set[str] = set()

        for source in self.sources:
            try:
                articles = self._fetch_source(source)
                for art in articles:
                    normalized = art.link.rstrip("/")
                    if normalized and normalized not in seen_links:
                        seen_links.add(normalized)
                        all_articles.append(art)
            except Exception as exc:
                logger.warning(f"Feed error [{source['name']}]: {exc}")

        # Keep only articles ≤ 24 h old, sort newest-first, cap at max_articles
        recent = [a for a in all_articles if a.age_hours() <= 24]
        recent.sort(key=lambda a: a.published, reverse=True)

        logger.info(
            f"Fetched {len(recent)} articles "
            f"(from {len(self.sources)} sources, last 24 h)"
        )
        return recent[: self.max_articles]

    # ── Private ────────────────────────────────────────────────────────────────

    def _fetch_source(self, source: dict) -> list[Article]:
        # Use requests (certifi-backed SSL) instead of feedparser's urllib to
        # avoid CERTIFICATE_VERIFY_FAILED on macOS and allow proper User-Agent.
        resp = requests.get(source["url"], headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        # feedparser sets bozo=True on malformed XML; still parse entries if present
        if feed.bozo and not feed.entries:
            raise ValueError(str(feed.bozo_exception))

        articles: list[Article] = []
        for entry in feed.entries:
            art = self._parse_entry(entry, source["name"], source.get("weight", 1.0))
            if art:
                articles.append(art)

        logger.debug(f"  {source['name']}: {len(articles)} articles")
        return articles

    def _parse_entry(
        self, entry, source_name: str, weight: float
    ) -> Optional[Article]:
        title = strip_html(getattr(entry, "title", ""))
        if not title:
            return None

        # Prefer full content (e.g. Guardian content:encoded) over summary/description
        content_raw = ""
        content_list = getattr(entry, "content", None)
        if content_list:
            content_raw = content_list[0].get("value", "")
        if not content_raw:
            content_raw = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or ""
            )
        summary = strip_html(content_raw)[:2000]
        link = getattr(entry, "link", "")
        published = self._parse_time(entry)

        return Article(
            title=title,
            summary=summary,
            link=link,
            source=source_name,
            source_weight=weight,
            published=published,
        )

    @staticmethod
    def _parse_time(entry) -> datetime:
        for attr in ("published_parsed", "updated_parsed"):
            t = getattr(entry, attr, None)
            if t:
                try:
                    return datetime(
                        t.tm_year, t.tm_mon, t.tm_mday,
                        t.tm_hour, t.tm_min, t.tm_sec,
                        tzinfo=timezone.utc,
                    )
                except Exception:
                    pass
        return datetime.now(timezone.utc)
