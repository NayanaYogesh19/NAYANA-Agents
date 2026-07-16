"""
ppc_metrics_agent.py — auto-fetches real ad data for the PPC review step,
replacing manual numeric metric entry (Ad Spend, Impressions, Clicks, etc.)
with real ads scraped from each platform's public ad transparency library:

  - Google Ads Transparency Center (URL input) via tools/ppc_scrapers/google_ads_scraper.py
  - Meta (Facebook/Instagram) Ads Library (URL input) via tools/ppc_scrapers/meta_ads_scraper.py
  - LinkedIn Ads Library (company/advertiser NAME input, not a URL — LinkedIn's
    ad library has no stable per-advertiser URL, unlike Google/Meta) via
    tools/ppc_scrapers/linkedin_ads_scraper.py

Never raises: any platform that can't be scraped simply comes back with an
"error" field rather than failing the whole run — same pattern as
agents/smm_metrics_agent.py.
"""

from __future__ import annotations

from datetime import datetime

from config import Config
from tools.ppc_scrapers.google_ads_scraper import GoogleAdsScraper
from tools.ppc_scrapers.linkedin_ads_scraper import LinkedInAdsScraper
from tools.ppc_scrapers.meta_ads_scraper import MetaAdsScraper


def _safe_scrape(scraper_fn, arg: str, platform_label: str) -> dict:
    if not arg:
        return {"platform": platform_label, "error": "Not provided"}
    try:
        return scraper_fn(arg)
    except Exception as exc:
        return {"platform": platform_label, "error": f"Scrape failed: {exc}"}


def run_ppc_metrics(google_ads_url: str, meta_ads_url: str, linkedin_company_name: str) -> dict:
    """Returns a dict with per-platform raw scrape results plus a flattened
    "summary" (total ads per platform, sample ad text) used by the review
    screen and the final report. Safe to call even without an Apify token
    configured (all platforms will report an error rather than raising)."""
    if not Config.APIFY_API_TOKEN:
        empty = {"error": "Apify API token not configured"}
        return {"google": empty, "meta": empty, "linkedin": empty, "summary": {"platforms_scraped": 0}}

    google = _safe_scrape(GoogleAdsScraper().scrape, google_ads_url, "Google")
    meta = _safe_scrape(MetaAdsScraper().scrape, meta_ads_url, "Meta")
    linkedin = _safe_scrape(LinkedInAdsScraper().scrape, linkedin_company_name, "LinkedIn")

    results = {"google": google, "meta": meta, "linkedin": linkedin}
    results["summary"] = _build_summary(results)
    return results


def _count_started_this_month(ads: list[dict]) -> int | None:
    """Best-effort count of ads whose date_started falls in the current
    calendar month. Returns None (not 0) if no ad in the list has a
    parseable date, so callers can distinguish "genuinely zero this month"
    from "date format not recognized" rather than silently showing a
    misleading 0."""
    now = datetime.utcnow()
    count = 0
    any_parsed = False
    for ad in ads:
        raw = ad.get("date_started")
        if not raw:
            continue
        parsed = None
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%B %d, %Y", "%b %d, %Y"):
            try:
                parsed = datetime.strptime(str(raw)[:len(fmt) + 5].strip(), fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            continue
        any_parsed = True
        if parsed.year == now.year and parsed.month == now.month:
            count += 1
    return count if any_parsed else None


def _build_summary(results: dict) -> dict:
    platforms_scraped = sum(1 for p in ("google", "meta", "linkedin") if not results[p].get("error"))

    def sample_ads(platform_data: dict, n: int = 5) -> list[dict]:
        ads = platform_data.get("ads") or []
        return [
            {
                "ad_library_id": ad.get("ad_library_id"),
                "headline": ad.get("headline"),
                "primary_text": ad.get("primary_text"),
                "advertiser_name": ad.get("advertiser_name"),
                "platforms": ad.get("platforms"),
                "content_type": ad.get("content_type") or ad.get("media_type"),
                "date_started": ad.get("date_started"),
                "date_ended": ad.get("date_ended"),
                "ad_status": ad.get("ad_status"),
            }
            for ad in ads[:n]
        ]

    return {
        "platforms_scraped": platforms_scraped,
        "google_total_ads": results["google"].get("total_ads"),
        "meta_total_ads": results["meta"].get("total_ads"),
        "linkedin_total_ads": results["linkedin"].get("total_ads"),
        "google_capped": results["google"].get("capped", False),
        "meta_capped": results["meta"].get("capped", False),
        "linkedin_capped": results["linkedin"].get("capped", False),
        "google_ads_started_this_month": _count_started_this_month(results["google"].get("ads") or []),
        "meta_ads_started_this_month": _count_started_this_month(results["meta"].get("ads") or []),
        "linkedin_ads_started_this_month": _count_started_this_month(results["linkedin"].get("ads") or []),
        "google_sample_ads": sample_ads(results["google"]),
        "meta_sample_ads": sample_ads(results["meta"]),
        "linkedin_sample_ads": sample_ads(results["linkedin"]),
    }
