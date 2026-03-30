"""
LLM Processor — sends the top-scored articles to OpenAI and returns the
fully formatted investment brief using the exact prompt design from the PRD.
"""
from __future__ import annotations

import re
import time
from datetime import datetime

from loguru import logger
from openai import OpenAI, APIError, RateLimitError

import config
from src.rss_fetcher import Article

# ── Prompts (verbatim from PRD) ────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a geopolitical macro investment analyst.

Your job is NOT to summarize news.
Your job is to extract actionable investment signals.

You think like a hedge fund manager:
- Focus on cause → effect → market impact
- Ignore low-impact news
- Be decisive, not descriptive

You must:
- Prioritize high-impact global events
- Identify second-order effects (not obvious ones)
- Translate news into market implications

Avoid:
- Generic summaries
- Obvious statements
- Safe or vague language

Output must be sharp, structured, and opinionated.\
"""

USER_PROMPT_TEMPLATE = """\
Analyze the following news:

{news_block}

---

Step 1 — Select the most important 3–5 events only.

Step 2 — For each event:
- What happened (1 sentence)
- Why it matters (real reason, not surface-level)
- Market impact:
  - Equities
  - Commodities
  - Crypto
  - Currency

Step 3 — Cross-event analysis:
- What bigger trend is forming?

Step 4 — Investment signals:
- Bullish sectors/assets
- Bearish sectors/assets
- Neutral / unclear

Step 5 — Actionable insight:
- What should an investor pay attention to in the next 24–72 hours?

Be specific. No generic advice.

---

Format your response EXACTLY as follows (use plain text, no markdown headers):

📅 DAILY GEOPOLITICAL INVESTMENT BRIEF — {date}

🔴 KEY EVENTS

1. [Event title]
   What happened: [1 sentence]
   Why it matters: [real reason]
   Market impact:
     Equities: [impact]
     Commodities: [impact]
     Crypto: [impact]
     Currency: [impact]

2. [next event...]

🌍 MACRO TREND
[Emerging pattern — 2–3 sentences]

📈 INVESTMENT SIGNALS

Bullish:
- [asset/sector with brief rationale]

Bearish:
- [asset/sector with brief rationale]

Neutral / Unclear:
- [asset/sector]

⚠️ RISK WATCH
- [What could go wrong or surprise the market]

🎯 ACTIONABLE INSIGHT
[Clear, specific, practical takeaway for the next 24–72 hours]\
"""


class LLMProcessor:
    def __init__(self):
        if config.LLM_PROVIDER == "gemini":
            if not config.GEMINI_API_KEY:
                raise ValueError(
                    "GEMINI_API_KEY is not set. "
                    "Get a free key at https://aistudio.google.com/app/apikey "
                    "then add GEMINI_API_KEY=... to your .env."
                )
            self._client = OpenAI(
                api_key=config.GEMINI_API_KEY,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            )
            self._model = config.GEMINI_MODEL
        else:
            if not config.OPENAI_API_KEY:
                raise ValueError(
                    "OPENAI_API_KEY is not set. "
                    "Copy .env.example to .env and add your key."
                )
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
            self._model = config.OPENAI_MODEL

    # ── Public ─────────────────────────────────────────────────────────────────

    def analyze(self, articles: list[Article]) -> str:
        """Send articles to the LLM and return the formatted brief."""
        if not articles:
            return self._empty_brief()

        news_block = self._format_articles(articles)
        user_prompt = USER_PROMPT_TEMPLATE.format(
            news_block=news_block,
            date=datetime.now().strftime("%B %d, %Y"),
        )

        logger.info(
            f"Sending {len(articles)} articles to {self._model} "
            f"[provider={config.LLM_PROVIDER}] …"
        )

        return self._call_with_retry(user_prompt)

    # ── Private ────────────────────────────────────────────────────────────────

    def _call_with_retry(self, user_prompt: str, max_retries: int = 3) -> str:
        last_error: Exception | None = None
        for attempt in range(1, max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user",   "content": user_prompt},
                    ],
                    max_tokens=config.LLM_MAX_TOKENS,
                    temperature=config.LLM_TEMPERATURE,
                )
                content = response.choices[0].message.content or ""
                logger.info(
                    f"LLM response received "
                    f"(tokens used: {response.usage.total_tokens})"
                )
                return content.strip()

            except (RateLimitError, APIError) as exc:
                last_error = exc
                if attempt == max_retries:
                    break
                wait = self._parse_retry_delay(exc) or (2 ** attempt)
                logger.warning(
                    f"API error (attempt {attempt}/{max_retries}). "
                    f"Retrying in {wait}s … [{exc}]"
                )
                time.sleep(wait)

        logger.error(f"LLM call failed after {max_retries} attempts: {last_error}")
        raise RuntimeError(
            f"LLM analysis failed: {last_error}"
        ) from last_error

    @staticmethod
    def _parse_retry_delay(exc: Exception) -> float | None:
        """Extract retry delay seconds from API error message (e.g. Gemini retryDelay hint)."""
        match = re.search(r"retry[_ ]?(?:after|delay)['\"]?\s*[:\s]+['\"]?(\d+(?:\.\d+)?)", str(exc), re.IGNORECASE)
        if match:
            return float(match.group(1)) + 2  # small buffer
        # Also handle "Please retry in Xs" pattern from Gemini
        match = re.search(r"retry in (\d+(?:\.\d+)?)s", str(exc), re.IGNORECASE)
        if match:
            return float(match.group(1)) + 2
        return None

    @staticmethod
    def _format_articles(articles: list[Article]) -> str:
        lines: list[str] = []
        for i, art in enumerate(articles, 1):
            lines.append(f"NEWS ITEM {i}:")
            lines.append(f"Source:    {art.source}")
            lines.append(f"Published: {art.age_label()}")
            lines.append(f"Title:     {art.title}")
            if art.summary:
                lines.append(f"Summary:   {art.summary}")
            lines.append(
                f"Scores:    economic_impact={art.economic_impact}  "
                f"urgency={art.urgency}  duration={art.duration}  "
                f"total={art.total_score:.2f}"
            )
            lines.append(f"Categories: {', '.join(art.categories_matched)}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _empty_brief() -> str:
        date_str = datetime.now().strftime("%B %d, %Y")
        return (
            f"📅 DAILY GEOPOLITICAL INVESTMENT BRIEF — {date_str}\n\n"
            "No high-signal news items found in the last 24 hours "
            "that meet the minimum scoring threshold.\n\n"
            "🎯 ACTIONABLE INSIGHT\n"
            "Monitor overnight session closely; low news flow can precede "
            "sharp gap moves. Reduce position sizing until clearer signals emerge."
        )
