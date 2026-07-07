"""Removes near-duplicate items — the same story picked up by several
outlets, or the same page found via both the sitemap and a search hit.

Two layers:
  1. Exact URL match (cheap, catches the sitemap+search overlap case)
  2. Fuzzy title match within the same category (catches the same story
     covered by 3-4 different news outlets with slightly different
     headlines)
"""

from __future__ import annotations

from typing import List

from rapidfuzz import fuzz

from agent.models import ReportItem

TITLE_SIMILARITY_THRESHOLD = 85  # 0-100, rapidfuzz token_sort_ratio


def dedupe_items(items: List[ReportItem]) -> List[ReportItem]:
    # Layer 1: exact URL
    seen_urls = set()
    by_url: List[ReportItem] = []
    for item in items:
        if item.url in seen_urls:
            continue
        seen_urls.add(item.url)
        by_url.append(item)

    # Layer 2: fuzzy title match, per category
    kept: List[ReportItem] = []
    for item in by_url:
        is_dupe = False
        for existing in kept:
            if existing.category != item.category:
                continue
            score = fuzz.token_sort_ratio(existing.title.lower(), item.title.lower())
            if score >= TITLE_SIMILARITY_THRESHOLD:
                is_dupe = True
                break
        if not is_dupe:
            kept.append(item)

    return kept
