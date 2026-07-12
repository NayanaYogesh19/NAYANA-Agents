"""
pagespeed_tool.py — Google PageSpeed Insights wrapper.

Mirrors the "Desktop2"/"Desktop3"/"Mobile1" HTTP Request nodes + the
"mobile1"/"Desktop Speed1"/"Mobile Speed1" Code/Set nodes in the SEO Audit
sub-workflow: fetch Lighthouse results for mobile and desktop strategies and
extract FCP, LCP, CLS, INP, fetch time.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import requests

from config import Config

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def _extract_metrics(payload: dict) -> dict:
    lighthouse = payload.get("lighthouseResult") or {}
    audits = lighthouse.get("audits") or {}

    fetch_time_raw = lighthouse.get("fetchTime")
    fetch_time = "-"
    if fetch_time_raw:
        try:
            fetch_time = datetime.fromisoformat(
                fetch_time_raw.replace("Z", "+00:00")
            ).strftime("%d/%m/%Y, %H:%M:%S")
        except Exception:
            fetch_time = fetch_time_raw

    inp_value = "-"
    try:
        inp = (
            payload.get("loadingExperience", {})
            .get("metrics", {})
            .get("INTERACTION_TO_NEXT_PAINT", {})
            .get("percentile")
        )
        if isinstance(inp, (int, float)):
            inp_value = f"{inp} ms"
    except Exception:
        pass

    return {
        "FCP": audits.get("first-contentful-paint", {}).get("displayValue", "-"),
        "LCP": audits.get("largest-contentful-paint", {}).get("displayValue", "-"),
        "CLS": audits.get("cumulative-layout-shift", {}).get("displayValue", "-"),
        "INP": inp_value,
        "fetchTime": fetch_time,
    }


def run_pagespeed(domain: str, strategy: str) -> dict:
    """Run a PageSpeed Insights check for a domain with strategy 'mobile' or
    'desktop'. Returns FCP/LCP/CLS/INP/fetchTime, defaulting to '-' values on
    any failure (never raises), matching the n8n neverError HTTP option."""
    if not domain.startswith(("http://", "https://")):
        domain = "https://" + domain

    if not Config.PAGESPEED_API_KEY:
        return {"FCP": "-", "LCP": "-", "CLS": "-", "INP": "-", "fetchTime": "-"}

    params = {
        "url": domain,
        "key": Config.PAGESPEED_API_KEY,
        "strategy": strategy,
    }

    try:
        resp = requests.get(PAGESPEED_URL, params=params, timeout=45)
        payload = resp.json()
        return _extract_metrics(payload)
    except Exception:
        return {"FCP": "-", "LCP": "-", "CLS": "-", "INP": "-", "fetchTime": "-"}
