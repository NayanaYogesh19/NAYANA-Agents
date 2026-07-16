"""
linkedin_ads_scraper.py — scrapes LinkedIn Ad Library data via the
"xtech/linkedin-adlibrary-scraper" Apify actor. Unlike Google/Meta, LinkedIn's
Ad Library has no stable per-advertiser URL to scrape — every available
Apify actor for it searches by company/advertiser name instead. So this
scraper (and the corresponding review-step input field) takes a company
name, not a URL.
"""

from __future__ import annotations

import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


class LinkedInAdsScraper:
    def __init__(self):
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            raise Exception("APIFY_API_TOKEN not found in .env file")
        self.client = ApifyClient(token)

    def scrape(self, company_name: str, max_ads: int = 100) -> dict:
        """Scrapes LinkedIn Ad Library ads for the given company/advertiser
        name via the xtech/linkedin-adlibrary-scraper actor and returns a
        summary dict (never raises — errors come back as an "error" key).
        `capped=True` signals the advertiser may have more ads than max_ads
        shown."""
        try:
            ads = self._collect_ads(company_name, max_ads)
        except Exception as exc:
            return {"platform": "LinkedIn", "error": f"Scrape failed: {exc}"}

        return {
            "platform": "LinkedIn",
            "total_ads": len(ads),
            "capped": len(ads) >= max_ads,
            "ads": ads,
        }

    def _collect_ads(self, company_name: str, max_ads: int) -> list[dict]:
        run_input = {"companyOrAdvertiser": company_name, "max_ads": max_ads}

        run = self.client.actor("xtech/linkedin-adlibrary-scraper").call(run_input=run_input)
        dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
        dataset_items = list(self.client.dataset(dataset_id).iterate_items())

        ads = []
        for item in dataset_items[:max_ads]:
            media_url = item.get("adMediaUrl")
            ad_type = (item.get("adType") or "").lower()
            content_type = "video" if "video" in ad_type else ("image" if media_url else "text")

            ads.append({
                "ad_library_id": item.get("adId") or item.get("id"),
                "advertiser_name": item.get("payingEntity") or company_name,
                "advertiser_profile_url": item.get("advertiserProfileUrl"),
                "ad_status": "Active" if not item.get("endDate") else "Inactive",
                "date_started": item.get("startDate"),
                "date_ended": item.get("endDate"),
                "content_type": content_type,
                "platforms": ["LinkedIn"],
                "primary_text": item.get("adDescription") or item.get("adTitle"),
                "headline": item.get("adHeadline") or item.get("adTitle"),
                "cta_text": item.get("ctaText"),
                "landing_url": item.get("ctaLink"),
                "creative_image_url": media_url,
                "total_impressions": item.get("totalImpressions"),
            })

        return ads
