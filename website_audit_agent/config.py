"""
config.py — Central configuration loaded from environment variables via python-dotenv.
All API keys and tunable constants live here so nothing is hard-coded elsewhere.
"""

import os
from dotenv import load_dotenv

load_dotenv()




class Config:
    """Singleton-style config object — import and use Config.FIELD directly."""

    # ── API Keys ──────────────────────────────────────────────────────────────
    PAGESPEED_API_KEY: str = os.getenv("PAGESPEED_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

    # ── Crawler settings ──────────────────────────────────────────────────────
    CRAWL_MAX_PAGES: int = int(os.getenv("CRAWL_MAX_PAGES", "50"))
    CRAWL_DELAY_SECONDS: float = float(os.getenv("CRAWL_DELAY_SECONDS", "1.0"))
    CRAWL_TIMEOUT: int = int(os.getenv("CRAWL_TIMEOUT", "10"))

    # ── Playwright settings ───────────────────────────────────────────────────
    PLAYWRIGHT_TIMEOUT: int = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000"))

    # ── Output ────────────────────────────────────────────────────────────────
    REPORT_OUTPUT_DIR: str = os.getenv("REPORT_OUTPUT_DIR", "./output")

    # ── Claude model ──────────────────────────────────────────────────────────
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"

    # ── Scoring weights (must sum to 1.0) ─────────────────────────────────────
    WEIGHTS: dict = {
        "performance": 0.25,
        "technical_seo": 0.20,
        "onpage_seo": 0.20,
        "content": 0.20,
        "ux": 0.15,
    }

    # ── Grade thresholds ──────────────────────────────────────────────────────
    GRADE_MAP: list = [
        (90, "A+"),
        (85, "A"),
        (80, "B+"),
        (75, "B"),
        (70, "C+"),
        (65, "C"),
        (60, "D+"),
        (0,  "D"),
    ]

    # ── PageSpeed API ─────────────────────────────────────────────────────────
    PAGESPEED_ENDPOINT: str = (
        "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    )
    PAGESPEED_RETRIES: int = 3

    # ── Core Web Vitals thresholds (for colour coding) ────────────────────────
    CWV_THRESHOLDS: dict = {
        "lcp_ms":  {"good": 2500,  "needs_improvement": 4000},
        "inp_ms":  {"good": 200,   "needs_improvement": 500},
        "cls":     {"good": 0.1,   "needs_improvement": 0.25},
        "fcp_ms":  {"good": 1800,  "needs_improvement": 3000},
        "ttfb_ms": {"good": 800,   "needs_improvement": 1800},
    }

    # ── Request headers ───────────────────────────────────────────────────────
    DEFAULT_HEADERS: dict = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; WebsiteAuditBot/1.0; "
            "+https://github.com/audit-agent)"
        )
    }
