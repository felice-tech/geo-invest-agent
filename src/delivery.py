"""
Delivery — sends the formatted brief via Telegram and/or Email.

Telegram uses the Bot HTTP API directly (no library dependency).
Email uses smtplib with STARTTLS.
"""
from __future__ import annotations

import smtplib
import textwrap
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from loguru import logger

import config

# Telegram hard limit per message
_TG_MAX_LEN = 4096


class Delivery:
    """Unified delivery: attempts Telegram, then Email (if enabled)."""

    def send(self, report: str) -> None:
        telegram_ok = False
        if config.TELEGRAM_BOT_TOKEN and config.TELEGRAM_CHAT_ID:
            telegram_ok = _TelegramChannel().send(report)
        else:
            logger.warning(
                "Telegram not configured "
                "(TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing)"
            )

        if config.EMAIL_ENABLED:
            _EmailChannel().send(report)
        elif not telegram_ok:
            # Last resort: print to stdout so the report is never lost
            logger.warning("No delivery channel succeeded — printing report to stdout")
            print("\n" + report)


# ── Telegram ──────────────────────────────────────────────────────────────────

class _TelegramChannel:
    def send(self, text: str) -> bool:
        """Split into ≤4096-char chunks and post each as a separate message."""
        chunks = _split_message(text, _TG_MAX_LEN)
        success = True
        for chunk in chunks:
            if not self._post(chunk):
                success = False
        return success

    def _post(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            resp = requests.post(url, json=payload, timeout=15)
            if resp.ok:
                logger.info("Telegram: message delivered")
                return True
            logger.error(
                f"Telegram API error {resp.status_code}: {resp.text[:200]}"
            )
            return False
        except requests.RequestException as exc:
            logger.error(f"Telegram request failed: {exc}")
            return False


# ── Email ─────────────────────────────────────────────────────────────────────

class _EmailChannel:
    def send(self, text: str) -> bool:
        if not all([config.SMTP_USER, config.SMTP_PASSWORD, config.EMAIL_TO]):
            logger.warning("Email not fully configured — skipping")
            return False

        from datetime import datetime
        subject = (
            f"📊 Geo-Invest Brief — {datetime.now().strftime('%b %d, %Y %H:%M')}"
        )
        html_body = _text_to_html(text)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_FROM
        msg["To"] = config.EMAIL_TO
        msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        try:
            with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as srv:
                srv.ehlo()
                srv.starttls()
                srv.login(config.SMTP_USER, config.SMTP_PASSWORD)
                srv.sendmail(config.EMAIL_FROM, config.EMAIL_TO, msg.as_string())
            logger.info(f"Email: delivered to {config.EMAIL_TO}")
            return True
        except smtplib.SMTPException as exc:
            logger.error(f"Email send failed: {exc}")
            return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split_message(text: str, max_len: int) -> list[str]:
    """Split on newlines, keeping chunks ≤ max_len chars."""
    if len(text) <= max_len:
        return [text]

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for line in text.splitlines(keepends=True):
        if current_len + len(line) > max_len and current:
            chunks.append("".join(current))
            current = []
            current_len = 0
        # If a single line exceeds max_len, hard-wrap it
        if len(line) > max_len:
            for part in textwrap.wrap(line, max_len):
                chunks.append(part)
        else:
            current.append(line)
            current_len += len(line)

    if current:
        chunks.append("".join(current))

    return chunks


def _text_to_html(text: str) -> str:
    """Minimal plain-text → HTML conversion for the email body."""
    import html as html_mod
    lines = text.splitlines()
    html_lines: list[str] = ["<html><body><pre style='font-family:monospace;font-size:14px;'>"]
    for line in lines:
        html_lines.append(html_mod.escape(line))
    html_lines.append("</pre></body></html>")
    return "\n".join(html_lines)
