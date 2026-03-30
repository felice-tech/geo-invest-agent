# Geopolitical Investment Intelligence Agent

A daily investment intelligence agent that aggregates global geopolitical and macroeconomic news, filters for market-moving signals, and delivers sharp, opinionated investment briefs via Telegram or Email every day at 07:00.

---

## Architecture

```
geo-invest-agent/
├── main.py                  ← Entry point (CLI)
├── config.py                ← All settings (loaded from .env)
├── requirements.txt
├── .env.example
├── src/
│   ├── rss_fetcher.py       ← Fetch & parse RSS feeds (10 sources)
│   ├── filter_engine.py     ← Keyword-based relevance filter
│   ├── scoring_engine.py    ← Score: Economic Impact · Urgency · Duration
│   ├── llm_processor.py     ← GPT-4 analysis with PRD prompt design
│   ├── delivery.py          ← Telegram bot + SMTP email delivery
│   ├── scheduler.py         ← APScheduler cron (timezone-aware)
│   └── memory.py            ← Persist reports; 7-day trend context
└── data/
    ├── reports/             ← Daily JSON report store (auto-created)
    └── agent.log            ← Rotating log file
```

### Pipeline Flow

```
RSS Feeds (10 sources, up to 30 articles)
    │
    ▼
Filter Engine  ← geopolitics · macro · commodities · high-impact keywords
    │
    ▼
Scoring Engine ← Economic Impact (1-5) · Urgency (1-5) · Duration (1-5)
    │           → keeps top 3-7 articles
    ▼
LLM Processor  ← GPT-4o  (system + user prompt from PRD)
    │           → structured brief with signals & actionable insight
    ▼
Memory Store   ← JSON archive + 7-day trend context
    │
    ▼
Delivery       ← Telegram (split to 4096-char chunks) + optional Email
```

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- A Telegram Bot token + your Chat ID  
  _(create a bot via [@BotFather](https://t.me/botfather), get your chat ID via [@userinfobot](https://t.me/userinfobot))_

### 2. Install

```bash
git clone <your-repo-url>
cd geo-invest-agent

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` — at minimum fill in:

| Variable             | Description                                        |
| -------------------- | -------------------------------------------------- |
| `OPENAI_API_KEY`     | Your OpenAI secret key                             |
| `OPENAI_MODEL`       | `gpt-4o` (default) or `gpt-4-turbo`, `gpt-4o-mini` |
| `TELEGRAM_BOT_TOKEN` | Token from @BotFather                              |
| `TELEGRAM_CHAT_ID`   | Your personal or group chat ID                     |
| `REPORT_TIME`        | Delivery time in `HH:MM` (24h), default `07:00`    |
| `TIMEZONE`           | pytz timezone, default `Asia/Jakarta`              |

### 4. Test run (no delivery)

```bash
python main.py --run-now --dry-run
```

This fetches live news, scores it, calls GPT-4, and prints the report to stdout — nothing is sent to Telegram/Email.

### 5. Run once and deliver

```bash
python main.py --run-now
```

### 6. Start the daily scheduler

```bash
python main.py --schedule
```

Runs forever, firing every day at the configured time in the configured timezone. Use a process manager (systemd, PM2, Docker) for production.

---

## Deployment (production)

### systemd (Linux)

Create `/etc/systemd/system/geo-invest-agent.service`:

```ini
[Unit]
Description=Geopolitical Investment Intelligence Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/geo-invest-agent
ExecStart=/opt/geo-invest-agent/.venv/bin/python main.py --schedule
Restart=on-failure
RestartSec=30
User=invest-agent

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now geo-invest-agent
sudo journalctl -fu geo-invest-agent
```

### Docker

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py", "--schedule"]
```

```bash
docker build -t geo-invest-agent .
docker run -d --env-file .env --restart unless-stopped geo-invest-agent
```

---

## Configuration Reference

| Variable             | Default             | Description                          |
| -------------------- | ------------------- | ------------------------------------ |
| `OPENAI_API_KEY`     | _(required)_        | OpenAI secret key                    |
| `OPENAI_MODEL`       | `gpt-4o`            | Model name                           |
| `LLM_MAX_TOKENS`     | `2000`              | Max tokens in LLM response           |
| `LLM_TEMPERATURE`    | `0.3`               | Lower = more decisive, less creative |
| `TELEGRAM_BOT_TOKEN` | _(required for TG)_ | Bot token from @BotFather            |
| `TELEGRAM_CHAT_ID`   | _(required for TG)_ | Target chat/channel ID               |
| `EMAIL_ENABLED`      | `false`             | Set `true` to enable email delivery  |
| `SMTP_HOST`          | `smtp.gmail.com`    | SMTP server                          |
| `SMTP_PORT`          | `587`               | SMTP port (STARTTLS)                 |
| `SMTP_USER`          | —                   | Gmail address                        |
| `SMTP_PASSWORD`      | —                   | Gmail App Password                   |
| `EMAIL_TO`           | —                   | Recipient address                    |
| `REPORT_TIME`        | `07:00`             | Daily delivery time (HH:MM)          |
| `TIMEZONE`           | `Asia/Jakarta`      | pytz timezone string                 |
| `MAX_ARTICLES`       | `30`                | Max articles fetched per run         |
| `TOP_ARTICLES_COUNT` | `7`                 | Articles sent to LLM                 |
| `MIN_ARTICLE_SCORE`  | `3.0`               | Minimum weighted score to keep       |

---

## Scoring Details

Each article receives three scores (1–5):

| Dimension           | Weight | How scored                                      |
| ------------------- | ------ | ----------------------------------------------- |
| **Economic Impact** | 40%    | Keyword severity + category breadth             |
| **Urgency**         | 30%    | Time since publication + breaking-news keywords |
| **Duration**        | 30%    | Expected longevity of the market effect         |

`total_score = (EI × 0.4 + U × 0.3 + D × 0.3) × source_weight`

Reuters/CNBC Economy carry a `1.2× source_weight` boost.

---

## News Sources

| Source             | RSS Feed                                 | Weight |
| ------------------ | ---------------------------------------- | ------ |
| Reuters Top News   | `feeds.reuters.com/reuters/topNews`      | 1.2    |
| Reuters Business   | `feeds.reuters.com/reuters/businessNews` | 1.2    |
| Reuters World      | `feeds.reuters.com/reuters/worldNews`    | 1.2    |
| CNBC World News    | `cnbc.com`                               | 1.0    |
| CNBC Economy       | `cnbc.com`                               | 1.1    |
| CNBC Markets       | `cnbc.com`                               | 1.0    |
| MarketWatch        | `marketwatch.com`                        | 1.0    |
| Yahoo Finance      | `finance.yahoo.com`                      | 0.9    |
| The Guardian World | `theguardian.com`                        | 0.9    |
| CNBC Indonesia     | `cnbcindonesia.com`                      | 1.0    |

---

## Roadmap (from PRD)

- [ ] **Memory Layer** — inject 7-day trend context into LLM prompt for escalation detection
- [ ] **Market Data Integration** — validate analysis against live oil/gold/index prices
- [ ] **Alert Mode** — push instant alert when article score exceeds critical threshold or black-swan keywords are detected
- [ ] **Multi-model support** — Groq / Anthropic Claude fallback
- [ ] **Web dashboard** — read-only HTML report viewer

---

## License

MIT
