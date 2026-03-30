"""
Filter Engine — keeps only articles with ≥1 keyword match across the
configured topic categories (geopolitics, macroeconomics, commodities,
high_impact).  Returns articles annotated with which categories matched.
"""
from __future__ import annotations

from loguru import logger

import config
from src.rss_fetcher import Article


class FilterEngine:
    def __init__(self, keywords: dict[str, list[str]] = config.FILTER_KEYWORDS):
        # Pre-lower all keywords once for fast matching
        self._kw: dict[str, list[str]] = {
            cat: [k.lower() for k in words]
            for cat, words in keywords.items()
        }

    def filter(self, articles: list[Article]) -> list[Article]:
        """Return only articles that match at least one category keyword."""
        relevant: list[Article] = []
        for art in articles:
            matched = self._matched_categories(art)
            if matched:
                art.categories_matched = matched
                relevant.append(art)

        logger.info(
            f"Filter: {len(relevant)}/{len(articles)} articles passed relevance check"
        )
        return relevant

    # ── Private ────────────────────────────────────────────────────────────────

    def _matched_categories(self, article: Article) -> list[str]:
        blob = article.text_blob()
        matched: list[str] = []
        for cat, keywords in self._kw.items():
            if any(kw in blob for kw in keywords):
                matched.append(cat)
        return matched
