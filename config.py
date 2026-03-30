"""
Central configuration — loads .env and exposes all settings as module-level constants.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM ────────────────────────────────────────────────────────────────────────
# LLM_PROVIDER: "openai" (default) or "gemini"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai").lower()

# OpenAI settings (used when LLM_PROVIDER=openai)
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# Gemini settings (used when LLM_PROVIDER=gemini)
# Free models: gemini-2.5-flash-lite, gemini-2.0-flash-lite, gemini-2.0-flash
# Get a free API key at https://aistudio.google.com/app/apikey
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))

# ── Telegram ───────────────────────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID: str = os.getenv("TELEGRAM_CHAT_ID", "")

# ── Email ──────────────────────────────────────────────────────────────────────
EMAIL_ENABLED: bool = os.getenv("EMAIL_ENABLED", "false").lower() == "true"
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", SMTP_USER)
EMAIL_TO: str = os.getenv("EMAIL_TO", "")

# ── Scheduler ─────────────────────────────────────────────────────────────────
REPORT_TIME: str = os.getenv("REPORT_TIME", "07:00")   # HH:MM
TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jakarta")

# ── Article fetch/scoring ─────────────────────────────────────────────────────
MAX_ARTICLES: int = int(os.getenv("MAX_ARTICLES", "30"))
TOP_ARTICLES_COUNT: int = int(os.getenv("TOP_ARTICLES_COUNT", "7"))
MIN_ARTICLE_SCORE: float = float(os.getenv("MIN_ARTICLE_SCORE", "3.0"))

# ── RSS sources ───────────────────────────────────────────────────────────────
# weight > 1.0 → slight boost to that source's scores
# Note: Reuters discontinued public RSS feeds; replaced with Bloomberg, BBC, Al Jazeera
RSS_SOURCES: list[dict] = [
    {
        "name": "Bloomberg Markets",
        "url": "https://feeds.bloomberg.com/markets/news.rss",
        "weight": 1.2,
    },
    {
        "name": "BBC World News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "weight": 1.1,
    },
    {
        "name": "Al Jazeera English",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "weight": 1.1,
    },
    {
        "name": "CNBC World News",
        "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "weight": 1.0,
    },
    {
        "name": "CNBC Economy",
        "url": "https://www.cnbc.com/id/20910258/device/rss/rss.html",
        "weight": 1.1,
    },
    {
        "name": "CNBC Markets",
        "url": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "weight": 1.0,
    },
    {
        "name": "MarketWatch Top Stories",
        "url": "https://feeds.marketwatch.com/marketwatch/topstories",
        "weight": 1.0,
    },
    {
        "name": "Yahoo Finance",
        "url": "https://finance.yahoo.com/news/rssindex",
        "weight": 0.9,
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
        "weight": 1.0,
    },
    {
        "name": "CNBC Indonesia",
        "url": "https://www.cnbcindonesia.com/rss",
        "weight": 1.0,
    },
]

# ── Filter keywords by category ───────────────────────────────────────────────
FILTER_KEYWORDS: dict[str, list[str]] = {
    "geopolitics": [
        "war", "invasion", "military", "attack", "airstrike", "offensive",
        "sanctions", "embargo", "blockade", "conflict", "nato",
        "ukraine", "russia", "china", "taiwan", "middle east", "iran",
        "israel", "north korea", "south korea", "hamas", "hezbollah",
        "trade war", "tariff", "export ban", "nuclear", "missile",
        "geopolitical", "alliance", "treaty", "diplomacy", "coup",
        "election", "xi jinping", "putin", "trump", "biden",
        "g7", "g20", "un security council", "pentagon", "pentagon",
        "regime", "protest", "prime minister", "chancellor",
    ],
    "macroeconomics": [
        "interest rate", "federal reserve", "fed rate", "inflation",
        "deflation", "cpi", "pce", "gdp", "recession", "stagflation",
        "unemployment", "nonfarm payrolls", "jobs report",
        "central bank", "ecb", "bank of japan", "boj", "bank of england",
        "imf", "world bank", "monetary policy", "fiscal policy",
        "quantitative easing", "rate hike", "rate cut", "rate pause",
        "yield curve", "treasury yield", "10-year", "debt ceiling",
        "economic growth", "contraction", "stimulus", "austerity",
        "current account", "trade deficit", "trade surplus", "wto",
    ],
    "commodities": [
        "oil", "crude", "brent", "wti", "opec", "opec+",
        "natural gas", "lng", "pipeline",
        "gold", "silver", "copper", "nickel", "iron ore", "lithium",
        "supply chain", "shortage", "surplus", "inventory",
        "mining", "commodities", "raw materials",
        "wheat", "corn", "soybean", "food prices", "energy prices",
        "refinery", "barrel", "per barrel",
    ],
    "high_impact": [
        "black swan", "default", "collapse", "crisis", "crash",
        "bubble", "bailout", "bankruptcy", "contagion", "systemic risk",
        "bank run", "market crash", "financial crisis", "shock",
        "emergency", "breaking", "urgent", "alert",
    ],
}

# ── Scoring keyword tables ────────────────────────────────────────────────────
# Words that push Economic Impact toward 5
ECONOMIC_IMPACT_HIGH: list[str] = [
    "war", "invasion", "default", "collapse", "crisis", "shock",
    "nuclear", "sanctions regime", "embargo", "bank run", "crash",
]
ECONOMIC_IMPACT_MED: list[str] = [
    "interest rate", "federal reserve", "inflation", "gdp", "tariff",
    "sanctions", "central bank", "recession", "rate hike", "rate cut",
    "oil", "gold", "opec", "imf", "trade war",
]

# Words that boost Urgency score (added on top of time-based score)
URGENCY_KEYWORDS: list[str] = [
    "breaking", "just in", "urgent", "developing", "alert",
    "emergency", "flash", "immediate", "critical",
]

# Words that push Duration toward 5 (long-lasting effects)
DURATION_HIGH: list[str] = [
    "war", "treaty", "nuclear", "alliance", "structural", "sanctions",
    "long-term", "decade", "permanent", "constitutional",
]
DURATION_MED: list[str] = [
    "policy", "legislation", "election", "reform", "regulation",
    "rate cycle", "trade deal", "agreement", "accord",
]

# Scoring weights (must sum to 1.0)
SCORING_WEIGHTS: dict[str, float] = {
    "economic_impact": 0.40,
    "urgency": 0.30,
    "duration": 0.30,
}
