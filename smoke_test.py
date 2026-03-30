"""Quick smoke test — no installed packages needed."""
import sys
sys.path.insert(0, ".")

import types

# ── stubs for uninstalled packages ─────────────────────────────────────────────
fp = types.ModuleType("feedparser")
sys.modules["feedparser"] = fp

loguru = types.ModuleType("loguru")
class _L:
    def info(self, *a, **k): pass
    def debug(self, *a, **k): pass
    def warning(self, *a, **k): print("WARN:", *a)
    def error(self, *a, **k): print("ERR:", *a)
    def remove(self, *a): pass
    def add(self, *a, **k): pass
loguru.logger = _L()
sys.modules["loguru"] = loguru

dotenv = types.ModuleType("dotenv")
dotenv.load_dotenv = lambda: None
sys.modules["dotenv"] = dotenv

# ── import core modules ────────────────────────────────────────────────────────
import config, src.filter_engine, src.scoring_engine
from src.rss_fetcher import Article
from datetime import datetime, timezone

# ── test article: high-signal ──────────────────────────────────────────────────
a = Article(
    title="US Federal Reserve signals emergency rate cut after oil shock",
    summary=(
        "The Fed is preparing a surprise rate cut as oil prices spike "
        "following Middle East conflict escalation."
    ),
    link="https://example.com/1",
    source="Reuters Top News",
    source_weight=1.2,
    published=datetime.now(timezone.utc),
)

fe = src.filter_engine.FilterEngine()
result = fe.filter([a])
assert len(result) == 1, "Expected 1 article to pass filter"
cats = result[0].categories_matched
print(f"FilterEngine OK — categories: {cats}")
assert "macroeconomics" in cats
assert "geopolitics" in cats or "commodities" in cats

se = src.scoring_engine.ScoringEngine(top_n=5, min_score=3.0)
ranked = se.score_and_rank(result)
r = ranked[0]
print(f"ScoringEngine OK — EI={r.economic_impact} U={r.urgency} D={r.duration} total={r.total_score}")
assert r.economic_impact >= 3
assert r.urgency >= 4   # published just now
assert r.total_score > 0

# ── test article: low-signal (should be filtered out) ─────────────────────────
b = Article(
    title="Company XYZ reports quarterly earnings",
    summary="XYZ Corp posted a 3% gain in revenue this quarter.",
    link="https://example.com/2",
    source="MarketWatch",
    source_weight=1.0,
    published=datetime.now(timezone.utc),
)
filtered_out = fe.filter([b])
assert len(filtered_out) == 0, "Low-signal article should be filtered out"
print("Filter correctly removed low-signal article")

print("\nAll smoke tests PASSED ✓")
