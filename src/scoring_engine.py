"""
Scoring Engine — assigns three independent scores (1–5) to each article
and computes a weighted total.

  Economic Impact  (weight 0.40)  — how large is the market/economic effect?
  Urgency          (weight 0.30)  — how recent / time-sensitive is this?
  Duration         (weight 0.30)  — how long-lasting is the effect likely to be?

Articles are then sorted by total_score (desc) and the top N are returned.
"""
from __future__ import annotations

from loguru import logger

import config
from src.rss_fetcher import Article


class ScoringEngine:
    def __init__(
        self,
        top_n: int = config.TOP_ARTICLES_COUNT,
        min_score: float = config.MIN_ARTICLE_SCORE,
        weights: dict[str, float] = config.SCORING_WEIGHTS,
    ):
        self.top_n = top_n
        self.min_score = min_score
        self.weights = weights

        # Pre-lower keyword lists
        self._high_impact = [k.lower() for k in config.ECONOMIC_IMPACT_HIGH]
        self._med_impact = [k.lower() for k in config.ECONOMIC_IMPACT_MED]
        self._urgency_kw = [k.lower() for k in config.URGENCY_KEYWORDS]
        self._duration_high = [k.lower() for k in config.DURATION_HIGH]
        self._duration_med = [k.lower() for k in config.DURATION_MED]

    # ── Public ─────────────────────────────────────────────────────────────────

    def score_and_rank(self, articles: list[Article]) -> list[Article]:
        """Score every article, filter by min_score, return top N sorted desc."""
        for art in articles:
            self._score_article(art)

        above_min = [a for a in articles if a.total_score >= self.min_score]
        above_min.sort(key=lambda a: a.total_score, reverse=True)

        top = above_min[: self.top_n]
        logger.info(
            f"Scoring: {len(top)} articles selected "
            f"(min_score={self.min_score}, top_n={self.top_n})"
        )
        return top

    # ── Private ────────────────────────────────────────────────────────────────

    def _score_article(self, article: Article) -> None:
        blob = article.text_blob()

        ei = self._economic_impact(blob, article.categories_matched)
        ur = self._urgency(blob, article.age_hours())
        du = self._duration(blob, article.categories_matched)

        # Apply source weight (e.g. Reuters gets a slight bump)
        raw = (
            ei * self.weights["economic_impact"]
            + ur * self.weights["urgency"]
            + du * self.weights["duration"]
        ) * article.source_weight

        article.economic_impact = ei
        article.urgency = ur
        article.duration = du
        article.total_score = round(raw, 3)

    def _economic_impact(self, blob: str, categories: list[str]) -> int:
        # Base from category breadth
        score = len(categories)  # 1–4

        # Boost if high-impact nuclear/war/crash words present
        if any(kw in blob for kw in self._high_impact):
            score = max(score, 4)
            if sum(1 for kw in self._high_impact if kw in blob) >= 2:
                score = 5

        # Medium-impact macro/commodity keywords
        if any(kw in blob for kw in self._med_impact):
            score = max(score, 3)

        # "high_impact" category matched → at least 4
        if "high_impact" in categories:
            score = max(score, 4)

        return min(5, max(1, score))

    def _urgency(self, blob: str, age_hours: float) -> int:
        # Time-based base score
        if age_hours < 2:
            base = 5
        elif age_hours < 6:
            base = 4
        elif age_hours < 12:
            base = 3
        elif age_hours < 24:
            base = 2
        else:
            base = 1

        # Keyword boost
        if any(kw in blob for kw in self._urgency_kw):
            base = min(5, base + 1)

        return base

    def _duration(self, blob: str, categories: list[str]) -> int:
        if any(kw in blob for kw in self._duration_high):
            return 5
        if any(kw in blob for kw in self._duration_med):
            return 4
        # Geopolitics tends to have lasting effects
        if "geopolitics" in categories:
            return max(3, 3)
        if "macroeconomics" in categories:
            return 3
        if "commodities" in categories:
            return 2
        return 1
