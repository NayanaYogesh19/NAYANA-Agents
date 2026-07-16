"""
smm_metrics_agent.py — auto-fetches SMM metrics for the Key Metrics Overview
slide (SMM category), replacing manual entry entirely.

Two steps:
  1. Discover the company's real Instagram / Facebook / LinkedIn / YouTube
     profile URLs via Tavily search (no separate URL input field required).
  2. Scrape each discovered profile via the ported
     Reach_Engagement_Follower_Analytics_Agent scrapers (Apify), each
     returning followers/subscribers, content strategy signals, and AI-
     generated brand/audience insights.

Never raises: any platform that can't be discovered or scraped simply comes
back with "Data not available" fields rather than failing the whole run.
"""

from __future__ import annotations

import re

from config import Config
from tools.smm_scrapers.facebook_scraper import FacebookScraper
from tools.smm_scrapers.instagram_scraper import InstagramScraper
from tools.smm_scrapers.linkedin_scraper import LinkedInScraper
from tools.smm_scrapers.youtube_scraper import YouTubeScraper
from tools.tavily_tool import tavily_search_raw

PLATFORM_DOMAINS = {
    "instagram": "instagram.com",
    "facebook": "facebook.com",
    "linkedin": "linkedin.com/company",
    "youtube": "youtube.com",
}


def _find_profile_url(company_name: str, domain: str, platform: str) -> str:
    """Uses Tavily to find the company's real profile URL for a given
    platform. Returns "" if nothing plausible is found."""
    site_domain = PLATFORM_DOMAINS[platform]
    query = f'{company_name} official {platform} page site:{site_domain}'
    results = tavily_search_raw(query, max_results=5)

    for result in results:
        url = result.get("url", "")
        if site_domain.split("/")[0] in url:
            if platform == "linkedin" and "/company/" not in url:
                continue
            return url
    return ""


def discover_profile_urls(company_name: str, domain: str) -> dict[str, str]:
    return {platform: _find_profile_url(company_name, domain, platform) for platform in PLATFORM_DOMAINS}


def _safe_scrape(scraper_fn, url: str, platform_label: str) -> dict:
    if not url:
        return {"platform": platform_label, "error": "Profile not found"}
    try:
        return scraper_fn(url)
    except Exception as exc:
        return {"platform": platform_label, "error": f"Scrape failed: {exc}"}


def run_smm_metrics(company_name: str, domain: str, profile_urls: dict[str, str] | None = None) -> dict:
    """Returns a dict with per-platform raw scrape results plus a flattened
    "summary" of the numbers the Key Metrics slide actually displays. Safe to
    call even without an Apify token configured (all platforms will report
    'Data not available' rather than raising).

    If `profile_urls` is given (the phased review flow's user-entered
    Instagram/Facebook/LinkedIn/YouTube URLs), those are scraped directly —
    Tavily-based auto-discovery is skipped entirely. If omitted, falls back
    to the original auto-discovery behavior unchanged (used by the legacy
    single-shot endpoint)."""
    if not Config.APIFY_API_TOKEN:
        empty = {"error": "Apify API token not configured"}
        return {
            "instagram": empty, "facebook": empty, "linkedin": empty, "youtube": empty,
            "summary": {"platforms_found": 0},
        }

    if profile_urls is None:
        profile_urls = discover_profile_urls(company_name, domain)

    instagram = _safe_scrape(InstagramScraper().scrape, profile_urls["instagram"], "Instagram")
    facebook = _safe_scrape(FacebookScraper().scrape, profile_urls["facebook"], "Facebook")
    linkedin = _safe_scrape(LinkedInScraper().scrape, profile_urls["linkedin"], "LinkedIn")
    youtube = _safe_scrape(YouTubeScraper().scrape, profile_urls["youtube"], "YouTube")

    results = {"instagram": instagram, "facebook": facebook, "linkedin": linkedin, "youtube": youtube}
    results["profile_urls"] = profile_urls
    results["summary"] = _build_summary(results)
    return results


def _build_summary(results: dict) -> dict:
    def get_num(data: dict, *keys):
        for k in keys:
            v = data.get(k)
            if isinstance(v, (int, float)):
                return v
        return None

    platforms_found = sum(1 for p in ("instagram", "facebook", "linkedin", "youtube") if not results[p].get("error"))

    return {
        "platforms_found": platforms_found,
        "instagram_followers": get_num(results["instagram"], "followers"),
        "facebook_followers": get_num(results["facebook"], "followers"),
        "linkedin_followers": get_num(results["linkedin"], "followers"),
        "linkedin_company_size": results["linkedin"].get("company_size"),
        "linkedin_industry": results["linkedin"].get("industry"),
        "youtube_subscribers": get_num(results["youtube"], "subscribers"),
        "content_strategy": (
            results["linkedin"].get("recommended_strategy")
            or results["instagram"].get("recommended_strategy")
            or []
        ),
        "brand_tone": results["linkedin"].get("brand_tone") or results["instagram"].get("brand_tone"),
    }
