"""Loads configuration from environment variables (via .env).

Only ANTHROPIC_API_KEY is required. Everything else degrades gracefully:
if a key is missing, that integration is skipped with a warning instead
of crashing the run.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # Required: OpenRouter (OpenAI-compatible) credentials
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )

    # Optional: Google Custom Search (paid after free daily quota).
    # If unset, discovery still works via the free Google News RSS feed.
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID", "")

    # Optional: Wayback Machine Save Page Now (free account + free key).
    WAYBACK_ACCESS_KEY = os.getenv("WAYBACK_ACCESS_KEY", "")
    WAYBACK_SECRET_KEY = os.getenv("WAYBACK_SECRET_KEY", "")
    ENABLE_ARCHIVING = _bool("ENABLE_ARCHIVING", default=False)

    # Optional: Google Sheets output (service account JSON file).
    GOOGLE_SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")

    # Optional: email output via SMTP (e.g. a Gmail app password).
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")
    REPORT_RECIPIENT = os.getenv("REPORT_RECIPIENT", "")

    # Behaviour
    SEARCH_WINDOW_BUFFER_DAYS = int(os.getenv("SEARCH_WINDOW_BUFFER_DAYS", "15"))
    MAX_CANDIDATES_PER_CATEGORY = int(os.getenv("MAX_CANDIDATES_PER_CATEGORY", "8"))
    REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; PREventsAgent/1.0; +https://example.com/bot)",
    )

    @classmethod
    def validate(cls) -> None:
        if not cls.OPENROUTER_API_KEY:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Copy .env.example to .env and fill it in."
            )


settings = Settings()
