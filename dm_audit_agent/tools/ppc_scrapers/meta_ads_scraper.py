"""
meta_ads_scraper.py — scrapes a Meta (Facebook/Instagram) Ads Library URL via
the official "apify/facebook-ads-scraper" Apify actor. Same ApifyClient
pattern as tools/smm_scrapers and tools/ppc_scrapers/google_ads_scraper.py —
reuses the shared APIFY_API_TOKEN, no new credentials needed.
"""

from __future__ import annotations

import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


class MetaAdsScraper:
    def __init__(self):
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            raise Exception("APIFY_API_TOKEN not found in .env file")
        self.client = ApifyClient(token)

    def scrape(self, url: str, max_ads: int = 100) -> dict:
        """Scrapes a Meta Ad Library URL (page, brand, or search URL) via the
        apify/facebook-ads-scraper actor and returns a summary dict (never
        raises — errors come back as an "error" key). `capped=True` signals
        the advertiser may have more ads than max_ads shown."""
        try:
            ads = self._collect_ads(url, max_ads)
        except Exception as exc:
            return {"platform": "Meta", "error": f"Scrape failed: {exc}"}

        return {
            "platform": "Meta",
            "total_ads": len(ads),
            "capped": len(ads) >= max_ads,
            "ads": ads,
        }

    def _collect_ads(self, url: str, max_ads: int) -> list[dict]:
        run_input = {"startUrls": [{"url": url}], "resultsLimit": max_ads}

        run = self.client.actor("apify/facebook-ads-scraper").call(run_input=run_input)
        dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
        dataset_items = list(self.client.dataset(dataset_id).iterate_items())

        ads = []
        for item in dataset_items[:max_ads]:
            image_url = item.get("imageUrl") or item.get("image_url")
            video_url = item.get("videoUrl") or item.get("video_url")
            content_type = "video" if video_url else ("image" if image_url else "text")

            ads.append({
                "ad_library_id": item.get("adArchiveID") or item.get("ad_archive_id"),
                "advertiser_name": item.get("pageName") or item.get("page_name") or "Unknown Advertiser",
                "page_id": item.get("pageID") or item.get("page_id"),
                "ad_status": "Active" if item.get("isActive", True) else "Inactive",
                "date_started": item.get("startDateFormatted") or item.get("start_date"),
                "date_ended": item.get("endDateFormatted") or item.get("end_date"),
                "content_type": content_type,
                "primary_text": item.get("body") or item.get("adText") or item.get("title"),
                "headline": item.get("title") or item.get("headline"),
                "cta_text": item.get("ctaText") or item.get("cta_text"),
                "landing_url": item.get("linkUrl") or item.get("link_url"),
                "platforms": item.get("publisherPlatform") or item.get("platforms") or ["Facebook", "Instagram"],
                "creative_image_url": image_url,
                "creative_video_url": video_url,
            })

        return ads
