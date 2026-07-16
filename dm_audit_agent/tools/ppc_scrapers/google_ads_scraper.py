"""
google_ads_scraper.py — ported from competitor_insight/meta_ads_intelligence_agent's
scrapers/google_scraper.py, adapted to this project's conventions (uses the
shared APIFY_API_TOKEN env var already configured for the SMM scrapers,
rather than a separate APIFY_TOKEN).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


def _format_timestamp(raw) -> str | None:
    """The actor returns firstShownAt/lastShownAt as Unix-epoch-seconds
    STRINGS (e.g. "1710421161"), not human dates — convert to a readable
    "YYYY-MM-DD" so the review screen never shows a raw timestamp. Returns
    None (not the raw value) if it isn't a parseable epoch number, so a
    genuinely unavailable date is distinguishable from a formatting bug."""
    if not raw:
        return None
    try:
        return datetime.fromtimestamp(int(raw), tz=timezone.utc).strftime("%Y-%m-%d")
    except (ValueError, TypeError, OverflowError):
        return None


class GoogleAdsScraper:
    def __init__(self):
        token = os.getenv("APIFY_API_TOKEN")
        if not token:
            raise Exception("APIFY_API_TOKEN not found in .env file")
        self.client = ApifyClient(token)

    def scrape(self, url: str, max_ads: int = 100) -> dict:
        """Scrapes a Google Ads Transparency Center URL via the
        lexis-solutions/google-ads-scraper Apify actor and returns a summary
        dict (never raises — errors come back as an "error" key, matching
        the SMM scrapers' pattern). The actor has no separate "true total ad
        count" field — max_ads both requests and caps how many are fetched,
        so `capped=True` signals the advertiser may have more ads than shown."""
        try:
            ads = self._collect_ads(url, max_ads)
        except Exception as exc:
            return {"platform": "Google", "error": f"Scrape failed: {exc}"}

        return {
            "platform": "Google",
            "total_ads": len(ads),
            "capped": len(ads) >= max_ads,
            "ads": ads,
        }

    def _collect_ads(self, url: str, max_ads: int) -> list[dict]:
        collected_signatures = set()
        run_input = {"startUrls": [{"url": url}], "maxItems": max_ads}

        run = self.client.actor("lexis-solutions/google-ads-scraper").call(run_input=run_input)
        dataset_id = run["defaultDatasetId"] if isinstance(run, dict) else run.default_dataset_id
        dataset_items = list(self.client.dataset(dataset_id).iterate_items())

        ads = []
        for item in dataset_items:
            media_type = "image"
            video_url = None
            image_url = None

            possible_video_fields = [
                item.get("videoUrl"), item.get("videoURL"), item.get("video"),
                item.get("videoUrls"), item.get("video_urls"), item.get("mediaUrl"),
                item.get("media_url"), item.get("creativeUrl"),
            ]
            possible_image_fields = [
                item.get("imageUrl"), item.get("imageURL"), item.get("image"),
                item.get("thumbnail"), item.get("thumbnailUrl"),
            ]

            for field in possible_video_fields:
                if not field:
                    continue
                field_str = str(field).lower()
                if any(ext in field_str for ext in [".mp4", ".webm", ".mov", "video", "youtube"]):
                    video_url = field
                    media_type = "video"
                    break

            for field in possible_image_fields:
                if field:
                    image_url = field
                    break

            if item.get("carousel"):
                media_type = "carousel"

            # "format" is the actor's real content-type field (TEXT/IMAGE/VIDEO);
            # also check other possible field names as a fallback.
            for field in [item.get("format"), item.get("mediaType"), item.get("creativeType"), item.get("assetType"), item.get("type")]:
                if not field:
                    continue
                field_str = str(field).lower()
                if "video" in field_str:
                    media_type = "video"
                elif "carousel" in field_str:
                    media_type = "carousel"
                elif "text" in field_str:
                    media_type = "text"

            advertiser_name = item.get("advertiserName") or item.get("advertiser") or "Unknown Advertiser"

            # The actor's real ad copy lives in variants[].textContent, not a
            # flat "headline"/"adText" field — reading only the flat fields
            # (as the original ported code did) produced "(no text)" for
            # every real ad. Pull the first non-empty variant text instead,
            # falling back to the flat fields in case a future actor version
            # adds them.
            variant_texts = [
                v.get("textContent") for v in (item.get("variants") or [])
                if v.get("textContent")
            ]
            headline = item.get("headline") or (variant_texts[0] if variant_texts else None)
            primary_text = item.get("primaryText") or item.get("adText") or item.get("description") or (
                " / ".join(variant_texts) if variant_texts else None
            )
            landing_url = item.get("landingPage") or item.get("landingUrl")

            # Real ad library ID from the actor's own output (creativeId/id) —
            # NOT a randomly generated placeholder, so it matches what a user
            # would see on the actual Google Ads Transparency Center page.
            library_id = item.get("creativeId") or item.get("id") or item.get("adId")

            signature = f"{library_id or ''}{advertiser_name}{headline}{landing_url}{media_type}"
            if signature in collected_signatures:
                continue
            collected_signatures.add(signature)

            platforms = item.get("platforms")
            if not platforms:
                country_stats = item.get("countryStats") or []
                platform_codes = set()
                for cs in country_stats:
                    for p in cs.get("platformStats") or []:
                        code = p.get("code")
                        if code:
                            platform_codes.add(code)
                platforms = sorted(platform_codes) or ["Google"]

            date_started = _format_timestamp(item.get("firstShownAt") or item.get("firstShown") or item.get("dateShown"))
            date_ended = _format_timestamp(item.get("lastShownAt"))
            # An ad is still running if it has no "last shown" date at all,
            # or that date is very recent (the transparency center only
            # reports a lastShownAt once an ad has actually stopped serving,
            # but some actor versions stamp a rolling "last seen" date even
            # for active ads — treat "ended within the last day" as still active).
            is_active = item.get("isActive")
            if is_active is None:
                last_shown_raw = item.get("lastShownAt")
                if not last_shown_raw:
                    is_active = True
                else:
                    try:
                        last_shown_dt = datetime.fromtimestamp(int(last_shown_raw), tz=timezone.utc)
                        is_active = (datetime.now(timezone.utc) - last_shown_dt).days < 1
                    except (ValueError, TypeError, OverflowError):
                        is_active = False

            ads.append({
                "ad_library_id": library_id,
                "advertiser_name": advertiser_name,
                "advertiser_id": item.get("advertiserId"),
                "ad_status": "Active" if is_active else "Inactive",
                "date_started": date_started,
                "date_ended": None if is_active else date_ended,
                "date_scraped": time.strftime("%Y-%m-%d"),
                "platforms": platforms,
                "content_type": media_type,
                "impressions": item.get("impressions"),
                "shown_countries": item.get("shownCountries"),
                "primary_text": primary_text,
                "headline": headline,
                "description": item.get("description"),
                "cta_text": item.get("cta"),
                "landing_url": landing_url,
                "media_type": media_type,
                "creative_image_url": image_url,
                "creative_video_url": video_url,
                "ad_snapshot_url": item.get("url") or item.get("previewUrl") or item.get("adUrl") or url,
            })

        return ads
