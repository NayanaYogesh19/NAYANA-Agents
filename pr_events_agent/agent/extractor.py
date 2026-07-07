"""Fetch a candidate page, strip it down to clean article text, and pull
a reliable publish date out of its metadata.

This is the step that prevents the two most common errors in a report
like this: including a page whose text LOOKS relevant but was actually
published outside the target window, and mis-titling an item because
the LLM had to work from noisy HTML instead of clean text.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Optional
from urllib.parse import urlparse

import trafilatura
from htmldate import find_date
from trafilatura.settings import use_config

from config import settings
from agent.models import CandidatePage

logger = logging.getLogger(__name__)

_TRAFILATURA_CONFIG = use_config()
_TRAFILATURA_CONFIG.set("DEFAULT", "USER_AGENTS", settings.USER_AGENT)

# Once we've learned a domain needs the no_ssl fallback (incomplete
# certificate chain — see extract()), skip straight to it for every
# other URL on that domain instead of eating a slow failing verified
# attempt every single time. A full crawl can hit 100+ pages on one
# such site, so this avoids a large, pointless multi-minute delay.
_no_ssl_domains: set[str] = set()

# htmldate's extensive_search=True is needed to find real dates on many
# sites (e.g. WordPress pages that print "01/21/2026" as plain text with
# no <meta>/JSON-LD backing it) — strict mode misses those entirely. But
# on some JS-rendered sites with zero genuine date signal anywhere,
# extensive mode's heuristics fall back to something suspiciously close
# to "right now" instead of admitting it found nothing. Rather than
# picking one mode and breaking the other class of site, we use
# extensive mode and then distrust any result that lands implausibly
# close to today — a fabricated "current-ish" date is the one pattern
# that's never a legitimate publish date for a report about the past.
_FABRICATION_GUARD_DAYS = 3


def _parse_date(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def _looks_fabricated(candidate_date: date) -> bool:
    return abs((date.today() - candidate_date).days) <= _FABRICATION_GUARD_DAYS


def extract(candidate: CandidatePage) -> Optional[CandidatePage]:
    """Return the candidate enriched with text + published_date, or None
    if the page could not be fetched/extracted at all.
    """
    if not candidate.url:
        return None

    domain = urlparse(candidate.url).netloc

    if domain in _no_ssl_domains:
        downloaded = trafilatura.fetch_url(candidate.url, no_ssl=True, config=_TRAFILATURA_CONFIG)
    else:
        downloaded = trafilatura.fetch_url(candidate.url, config=_TRAFILATURA_CONFIG)
        if not downloaded:
            # A plain fetch failure can be a dead link, a timeout, or —
            # not uncommonly — a site whose server sends an incomplete
            # TLS certificate chain (missing intermediate cert), which
            # fails strict verification even though the site is
            # otherwise fine. trafilatura doesn't distinguish the
            # reason, so we retry once with verification off rather
            # than losing the page entirely, and remember this domain
            # needs that so every later page on it skips straight to
            # the fast path instead of repeating the slow failure.
            downloaded = trafilatura.fetch_url(candidate.url, no_ssl=True, config=_TRAFILATURA_CONFIG)
            if downloaded:
                _no_ssl_domains.add(domain)
                logger.warning(
                    "Fetched %s only after disabling TLS verification — the site's "
                    "certificate chain could not be verified. Will skip straight to "
                    "this for the rest of %s.", candidate.url, domain,
                )
    if not downloaded:
        logger.debug("Could not fetch %s", candidate.url)
        return None

    text = trafilatura.extract(
        downloaded, include_comments=False, include_tables=False, favor_precision=True
    )
    if not text or len(text.strip()) < 80:
        logger.debug("Extracted text too short/empty for %s", candidate.url)
        return None

    # Some candidates (e.g. from DuckDuckGo News) already arrive with a
    # confirmed exact date from the search result itself — don't let a
    # page-level extraction miss throw that away. Only look for an
    # on-page date if we don't already have a trustworthy one.
    if candidate.date_is_exact and candidate.published_date is not None:
        published = candidate.published_date
        date_is_exact = True
    else:
        raw_date = find_date(downloaded, extensive_search=True)
        published = _parse_date(raw_date)

        if published is not None and _looks_fabricated(published):
            logger.debug(
                "Discarding htmldate result %s for %s: suspiciously close to today, "
                "likely a build/cache timestamp rather than a real publish date",
                published, candidate.url,
            )
            published = None

        date_is_exact = published is not None

        # Fall back to the sitemap's own lastmod, if the page itself
        # had no discoverable (and trustworthy) date. This is real
        # metadata the site published (not a guess) but it means "last
        # modified", not necessarily "first published" — so it's a
        # weaker signal, flagged as inexact rather than treated the
        # same as a real on-page publish date.
        if published is None and candidate.sitemap_lastmod is not None:
            published = candidate.sitemap_lastmod

    if not candidate.title:
        candidate.title = text.split("\n", 1)[0][:140]

    candidate.text = text[:4000]  # cap length fed to the LLM
    candidate.published_date = published
    candidate.date_is_exact = date_is_exact
    return candidate


def within_window(candidate: CandidatePage, start: date, end: date) -> bool:
    """True if the candidate's date is inside the window.

    A report is supposed to contain only items from the requested
    window — an item with no discoverable date anywhere (not on the
    page, not in the sitemap, not from search) can't be verified as
    belonging, so it's excluded rather than shown with a blank/"Unknown"
    date. This trades a small amount of recall (a handful of pages that
    genuinely expose no date signal at all) for the report never
    showing something the user didn't ask for.
    """
    if candidate.published_date is None:
        return False
    return start <= candidate.published_date <= end
