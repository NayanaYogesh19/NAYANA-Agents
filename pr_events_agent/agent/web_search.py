"""Discovery of THIRD-PARTY mentions: press coverage, webinars, events,
awards that live off the company's own site.

Three sources, used together when available:

  1. Google News RSS  — free, no API key, no signup. Supports only a
     relative "past N days" window (`when:Nd`), not an arbitrary
     start/end range. We ask for a generous buffer window and rely on
     the extractor step to pin down and verify the real publish date.

  2. Google Custom Search JSON API — optional, needs GOOGLE_API_KEY and
     GOOGLE_CSE_ID (100 free queries/day, then paid). Same buffering
     approach: its `dateRestrict` param is also relative, not exact.

  3. DuckDuckGo News (via the free `ddgs` library, no API key/signup).
     Unlike the other two, it accepts a real "YYYY-MM-DD..YYYY-MM-DD"
     date range AND returns each result's actual publish date up
     front — so candidates from this source arrive pre-dated instead
     of needing a full fetch+extract just to learn when they ran. This
     is also what picks up coverage that ran on third-party outlets
     (wire services, trade press) rather than only the company's own
     site.

None of the three can be trusted as the final word on date filtering
on their own — that filtering happens later, against the real
extracted (or DDG-provided) publish date.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import List
from urllib.parse import quote_plus

import feedparser
import requests
from ddgs import DDGS
from googlenewsdecoder import gnewsdecoder

from config import settings
from agent.models import CandidatePage

logger = logging.getLogger(__name__)

# Each category maps to one or more plain-keyword query variants rather
# than a single boolean "(a OR b OR c)" query: Google News RSS and,
# critically, DuckDuckGo News don't reliably honor parenthesized OR
# grouping (DuckDuckGo has been observed to return zero results for a
# grouped query while the identical search with just one of the terms
# returns real hits) — so a multi-synonym category was silently losing
# almost all of its coverage. Running each synonym as its own query
# against every source and merging/deduping the results gets the same
# recall in a way every backend actually understands.
QUERY_TEMPLATES: dict[str, tuple[str, ...]] = {
    "press_release": ('"{company}" press release',),
    "webinar": ('"{company}" webinar',),
    "event": (
        '"{company}" event',
        '"{company}" exhibition',
        '"{company}" conference',
        '"{company}" summit',
    ),
    "award": (
        '"{company}" award',
        '"{company}" wins',
        '"{company}" recognized',
        '"{company}" winner',
    ),
}


def _window_days(period_start: date, period_end: date) -> int:
    span = (date.today() - period_start).days
    return max(span + settings.SEARCH_WINDOW_BUFFER_DAYS, 7)


def _resolve_google_news_url(link: str) -> str:
    """Google News RSS `link` values point at a Google-hosted redirect
    page (an obfuscated article id), not the publisher's own URL — and
    that redirect page has no real article text, so trafilatura's
    extraction fails on it every time. Decode it to the actual
    publisher URL so extraction has real content to work with. Falls
    back to the original link if decoding fails for any reason (rate
    limiting, format change) — same as before this existed.
    """
    try:
        result = gnewsdecoder(link, interval=1)
    except Exception as exc:
        logger.debug("Google News URL decode failed for %s: %s", link, exc)
        return link
    if result.get("status") and result.get("decoded_url"):
        return result["decoded_url"]
    return link


def _search_google_news_rss(query: str, days: int) -> List[CandidatePage]:
    url = (
        "https://news.google.com/rss/search?q="
        f"{quote_plus(query)}+when:{days}d&hl=en-US&gl=US&ceid=US:en"
    )
    try:
        parsed = feedparser.parse(url)
    except Exception as exc:  # feedparser rarely raises, but be safe
        logger.warning("Google News RSS request failed for %r: %s", query, exc)
        return []

    results = []
    for entry in parsed.entries[: settings.MAX_CANDIDATES_PER_CATEGORY]:
        link = entry.get("link", "")
        if link:
            link = _resolve_google_news_url(link)
        results.append(
            CandidatePage(
                url=link,
                title=entry.get("title"),
                source_type="search",
            )
        )
    return results


def _search_google_custom(query: str) -> List[CandidatePage]:
    if not (settings.GOOGLE_API_KEY and settings.GOOGLE_CSE_ID):
        return []
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": settings.GOOGLE_API_KEY,
                "cx": settings.GOOGLE_CSE_ID,
                "q": query,
                "num": min(settings.MAX_CANDIDATES_PER_CATEGORY, 10),
            },
            timeout=settings.REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.warning("Google Custom Search request failed for %r: %s", query, exc)
        return []

    results = []
    for item in data.get("items", []):
        results.append(
            CandidatePage(
                url=item.get("link", ""),
                title=item.get("title"),
                source_type="search",
            )
        )
    return results


def _parse_ddg_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        # DDG returns ISO 8601 with a time/offset, e.g. 2026-06-30T10:54:00+00:00
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def _search_duckduckgo(query: str) -> List[CandidatePage]:
    # Deliberately NOT passing a "start..end" timelimit here (despite
    # ddgs.DDGS().news() accepting one): observed behaviour is that
    # supplying it doesn't reliably filter by date — instead it changes
    # WHICH underlying engines get merged (one engine's date-range
    # support throws and gets silently dropped, and another far noisier
    # backend fills the gap instead), so the exact same query can return
    # a genuinely relevant top hit unfiltered but only unrelated noise
    # once a date range is added. Searching undated and relying on the
    # real per-page date + within_window() filtering downstream (which
    # we need anyway, since none of the three search sources can be
    # trusted as the final word on dates) is both simpler and more
    # reliable than trying to use this parameter at all.
    try:
        results = DDGS().news(query, max_results=settings.MAX_CANDIDATES_PER_CATEGORY)
    except Exception as exc:
        logger.warning("DuckDuckGo search failed for %r: %s", query, exc)
        return []

    out = []
    for item in results:
        out.append(
            CandidatePage(
                url=item.get("url", ""),
                title=item.get("title"),
                source_type="search",
                published_date=_parse_ddg_date(item.get("date")),
                date_is_exact=item.get("date") is not None,
            )
        )
    return out


def search_all_categories(
    company_name: str, period_start: date, period_end: date
) -> dict[str, List[CandidatePage]]:
    """Run all search sources for each of the 4 categories.

    Returns a dict keyed by category -> list of CandidatePage.
    """
    days = _window_days(period_start, period_end)
    out: dict[str, List[CandidatePage]] = {}

    for category, templates in QUERY_TEMPLATES.items():
        found: List[CandidatePage] = []
        for template in templates:
            query = template.format(company=company_name)
            found += _search_google_news_rss(query, days)
            found += _search_google_custom(query)
            found += _search_duckduckgo(query)

        # de-dupe by URL while preserving order
        seen = set()
        deduped = []
        for c in found:
            if c.url and c.url not in seen:
                seen.add(c.url)
                deduped.append(c)

        out[category] = deduped[: settings.MAX_CANDIDATES_PER_CATEGORY]
        logger.info("Search found %d candidates for category=%s", len(out[category]), category)

    return out
