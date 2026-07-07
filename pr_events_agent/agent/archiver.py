"""Wayback Machine integration.

Role in THIS pipeline (see README for the full explanation): this runs
LAST, only on items that have already survived discovery, extraction,
classification, and dedup. It does not find or verify anything — it
stamps a permanent, dated copy of a page we've already decided belongs
in the report, so the source can't silently change or disappear later.

Three endpoints, two different auth requirements:
  - /wayback/available   -> no key needed, free
  - /cdx/search/cdx      -> no key needed, free
  - /save/<url> (SPN2)   -> needs a free archive.org account + free
                            access/secret key pair from
                            https://archive.org/account/s3.php
"""

from __future__ import annotations

import logging
import time
from datetime import date
from typing import Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

AVAILABLE_ENDPOINT = "https://archive.org/wayback/available"
CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
SAVE_ENDPOINT = "https://web.archive.org/save/"
SAVE_STATUS_ENDPOINT = "https://web.archive.org/save/status/"


def check_existing_snapshot(url: str, near: Optional[date] = None) -> Optional[str]:
    """Free, keyless. Returns the closest existing snapshot URL, if any."""
    params = {"url": url}
    if near:
        params["timestamp"] = near.strftime("%Y%m%d")
    try:
        resp = requests.get(AVAILABLE_ENDPOINT, params=params, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        snap = data.get("archived_snapshots", {}).get("closest")
        return snap.get("url") if snap else None
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Wayback availability check failed for %s: %s", url, exc)
        return None


def capture_history(url: str, start: date, end: date) -> list[str]:
    """Free, keyless. Lists timestamps of known captures of `url` within
    a date range — a weak secondary signal for when a page first
    appeared, NOT a substitute for the real extracted publish date.
    """
    params = {
        "url": url,
        "from": start.strftime("%Y%m%d"),
        "to": end.strftime("%Y%m%d"),
        "output": "json",
        "filter": "statuscode:200",
        "limit": 20,
    }
    try:
        resp = requests.get(CDX_ENDPOINT, params=params, timeout=settings.REQUEST_TIMEOUT)
        resp.raise_for_status()
        rows = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.debug("Wayback CDX lookup failed for %s: %s", url, exc)
        return []

    if not rows or len(rows) < 2:
        return []
    header = rows[0]
    ts_index = header.index("timestamp") if "timestamp" in header else 1
    return [row[ts_index] for row in rows[1:]]


def save_page_now(url: str) -> Optional[str]:
    """Requires WAYBACK_ACCESS_KEY/SECRET (free account). Submits `url`
    for immediate archiving and returns the resulting snapshot URL, or
    None if archiving is disabled, unconfigured, or fails.

    This does basic polling of the SPN2 job status with a short
    timeout; it will not hang indefinitely.
    """
    if not settings.ENABLE_ARCHIVING:
        return None
    if not (settings.WAYBACK_ACCESS_KEY and settings.WAYBACK_SECRET_KEY):
        logger.warning(
            "ENABLE_ARCHIVING is true but WAYBACK_ACCESS_KEY/SECRET are not set; skipping archive for %s",
            url,
        )
        return None

    headers = {
        "Authorization": f"LOW {settings.WAYBACK_ACCESS_KEY}:{settings.WAYBACK_SECRET_KEY}",
        "Accept": "application/json",
    }
    try:
        resp = requests.post(
            SAVE_ENDPOINT,
            data={"url": url, "skip_first_archive": "1"},
            headers=headers,
            timeout=settings.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        job_id = resp.json().get("job_id")
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Save Page Now submission failed for %s: %s", url, exc)
        return None

    if not job_id:
        return None

    # Poll briefly for completion rather than trusting an immediate result.
    for _ in range(6):
        time.sleep(5)
        try:
            status_resp = requests.get(
                SAVE_STATUS_ENDPOINT + job_id, headers=headers, timeout=settings.REQUEST_TIMEOUT
            )
            status_resp.raise_for_status()
            status = status_resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.debug("Save Page Now status check failed for job %s: %s", job_id, exc)
            continue

        if status.get("status") == "success":
            timestamp = status.get("timestamp")
            original = status.get("original_url", url)
            snapshot_url = f"https://web.archive.org/web/{timestamp}/{original}"
            logger.info("Archived %s -> %s", url, snapshot_url)
            return snapshot_url
        if status.get("status") == "error":
            logger.warning("Save Page Now job failed for %s: %s", url, status.get("message"))
            return None

    logger.debug("Save Page Now job for %s did not complete within the polling window", url)
    return None
