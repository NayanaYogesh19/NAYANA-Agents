"""
config.py — Central configuration for the DM Audit Agent.

Loads settings from .env: OpenRouter (LLM), Tavily (web search), Google
PageSpeed Insights, and Apify (SMM profile scraping). SEO/PPC metrics are
entered manually by the user; SMM metrics are auto-fetched via Tavily
(profile discovery) + Apify (Instagram/Facebook/LinkedIn/YouTube scraping) —
no SE Ranking or other paid SEO API dependency.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    PAGESPEED_API_KEY: str = os.getenv("PAGESPEED_API_KEY", "")

    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")

    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8010"))

    REPORTS_DIR: str = os.path.join(os.path.dirname(__file__), "reports")
    STORAGE_DIR: str = os.path.join(os.path.dirname(__file__), "storage")


os.makedirs(Config.REPORTS_DIR, exist_ok=True)
os.makedirs(Config.STORAGE_DIR, exist_ok=True)
