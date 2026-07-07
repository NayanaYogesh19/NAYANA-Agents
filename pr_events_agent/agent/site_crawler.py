"""Discovery on the company's OWN website.

Strategy (cheapest / most reliable first):
  1. robots.txt -> sitemap location(s)
  2. sitemap.xml (and nested sitemap indexes) -> filter URLs by keyword
  3. common RSS/Atom feed paths -> parsed with feedparser
  4. a small set of common newsroom/blog path guesses, as a last resort

This intentionally does NOT use a headless browser. Most newsroom/blog
listing pages are still server-rendered or exposed via sitemap/RSS; if a
particular company's site is fully client-side rendered, this step will
find fewer candidates and the Google-search step becomes more important.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime
from typing import List, Optional
from urllib.parse import urljoin, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from config import settings
from agent import http
from agent.models import CandidatePage

logger = logging.getLogger(__name__)

# Matches a URL-locale path segment: a 2-letter language code optionally
# followed by a region/script subtag — ja, fr, de, zh-cn, zh-tw, es-mx,
# pt-br, en-gb, etc. Real content path segments (news, events, blog,
# press-releases, ...) are never 2-4 letters in this shape, so this
# generalizes across any site's locale scheme without listing specific
# languages or specific sites.
_LOCALE_SEGMENT_RE = re.compile(r"^[a-z]{2}(-[a-z]{2,4})?$", re.I)


def _strip_locale_prefix(url: str) -> Optional[str]:
    """If the URL's first path segment looks like a locale code, return
    the same URL with that segment removed — a plausible guess at the
    default/English URL, to be verified by actually fetching it before
    use (see crawl_company_site). Returns None if no locale-looking
    prefix is present.
    """
    parsed = urlparse(url)
    segments = parsed.path.split("/")
    # segments[0] is '' (leading slash); the locale would be segments[1]
    if len(segments) < 3 or not _LOCALE_SEGMENT_RE.match(segments[1]):
        return None
    new_path = "/" + "/".join(segments[2:])
    return parsed._replace(path=new_path).geturl()


# Once we've learned whether stripping a given (domain, locale prefix)
# combination actually resolves to a real English page, remember it —
# a site with hundreds of localized URLs would otherwise cost one live
# HTTP verification per URL instead of once per locale actually seen.
_locale_strip_cache: dict[tuple[str, str], bool] = {}


def _resolve_english_url(url: str) -> str:
    """Best-effort: if `url` looks locale-prefixed and an English
    version at the same path resolves, return that instead. Verifies
    (and caches) per (domain, locale) pair rather than per URL.
    """
    english_url = _strip_locale_prefix(url)
    if not english_url or english_url == url:
        return url

    parsed = urlparse(url)
    locale = parsed.path.split("/")[1].lower()
    cache_key = (parsed.netloc, locale)

    if cache_key not in _locale_strip_cache:
        resp = _get(_strip_locale_prefix(url))
        _locale_strip_cache[cache_key] = resp is not None
        if _locale_strip_cache[cache_key]:
            logger.debug(
                "Locale prefix '/%s/' on %s strips to a working English URL; "
                "will do this for the rest of that locale on this domain.",
                locale, parsed.netloc,
            )

    return english_url if _locale_strip_cache[cache_key] else url

KEYWORDS = (
    "press", "news", "newsroom", "media", "blog", "story", "stories",
    "event", "webinar", "award", "recognition", "insight",
)

# Listing/index/tag pages aggregate many articles under one URL with no
# single publish date — e.g. /newsroom/all or /newsroom/tags/research.
# Letting these through as if they were one article is what produces
# report rows whose "direct link" actually opens a list of unrelated
# items instead of the one thing the title describes.
LISTING_PATH_MARKERS = ("/tags/", "/tag/", "/category/", "/categories/", "/page/")
LISTING_PATH_SUFFIXES = ("/all", "/index", "/archive")

# A URL whose LAST path segment is itself a generic section word (with
# nothing more specific after it) is almost always that section's own
# index/listing page — e.g. ".../newsroom/press-releases" — as opposed
# to a real article, which always has an extra segment after the
# section name (a slug, an id, or a marker like "/post/"). This catches
# listing pages that a text-content check can miss, e.g. sites that
# render the latest article's full text inline on the section index.
_SECTION_ROOT_WORDS = {
    "news", "newsroom", "press", "press-release", "press-releases",
    "media", "media-center", "blog", "blogs", "events", "event",
    "webinars", "webinar", "awards", "award", "insights", "stories",
}


def _is_section_root(url: str) -> bool:
    segments = [s for s in urlparse(url).path.rstrip("/").lower().split("/") if s]
    return bool(segments) and segments[-1] in _SECTION_ROOT_WORDS


def _is_listing_url(url: str) -> bool:
    path = urlparse(url).path.rstrip("/").lower()
    if any(marker in path for marker in LISTING_PATH_MARKERS):
        return True
    if any(path.endswith(suffix) for suffix in LISTING_PATH_SUFFIXES):
        return True
    return _is_section_root(url)

COMMON_PATHS = (
    "/news", "/newsroom", "/press", "/press-releases", "/blog",
    "/media", "/media-center", "/events", "/company/news", "/about/news",
)

COMMON_FEED_PATHS = ("/feed", "/rss", "/blog/feed", "/news/feed", "/feed.xml")


def _get(url: str) -> requests.Response | None:
    resp = http.get(url)
    if resp is not None and resp.status_code == 200:
        return resp
    return None


def _root(base_url: str) -> str:
    parsed = urlparse(base_url)
    return f"{parsed.scheme}://{parsed.netloc}"


def _sitemap_urls_from_robots(base_url: str) -> List[str]:
    resp = _get(urljoin(_root(base_url), "/robots.txt"))
    if not resp:
        return []
    return [
        line.split(":", 1)[1].strip()
        for line in resp.text.splitlines()
        if line.lower().startswith("sitemap:")
    ]


def _parse_lastmod(raw: Optional[str]) -> Optional[date]:
    if not raw:
        return None
    try:
        # lastmod is typically ISO 8601, e.g. 2026-06-22T15:03:39Z
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_sitemap(
    url: str, depth: int = 0, seen: set | None = None
) -> List[tuple[str, Optional[date]]]:
    """Returns (url, lastmod_date) pairs. lastmod is real metadata the
    site itself publishes — a legitimate fallback date signal, distinct
    from htmldate's in-page heuristics.
    """
    if seen is None:
        seen = set()
    if url in seen or depth > 2:
        return []
    seen.add(url)

    resp = _get(url)
    if not resp:
        return []

    soup = BeautifulSoup(resp.content, "xml")

    # Sitemap index: recurse into nested sitemaps.
    if soup.find("sitemapindex"):
        urls: List[tuple[str, Optional[date]]] = []
        for nested in [loc.text.strip() for loc in soup.find_all("loc")]:
            urls.extend(_parse_sitemap(nested, depth + 1, seen))
        return urls

    out: List[tuple[str, Optional[date]]] = []
    for url_tag in soup.find_all("url"):
        loc = url_tag.find("loc")
        if not loc or not loc.text.strip():
            continue
        lastmod_tag = url_tag.find("lastmod")
        out.append((loc.text.strip(), _parse_lastmod(lastmod_tag.text.strip() if lastmod_tag else None)))
    return out


def _keyword_filter(urls: List[tuple[str, Optional[date]]]) -> List[tuple[str, Optional[date]]]:
    return [
        (u, d)
        for u, d in urls
        if any(k in u.lower() for k in KEYWORDS) and not _is_listing_url(u)
    ]


def _rss_candidates(base_url: str) -> List[CandidatePage]:
    candidates = []
    root = _root(base_url)
    for path in COMMON_FEED_PATHS:
        feed_url = urljoin(root, path)
        parsed = feedparser.parse(feed_url)
        if parsed.bozo and not parsed.entries:
            continue
        for entry in parsed.entries[:20]:
            candidates.append(
                CandidatePage(
                    url=entry.get("link", ""),
                    title=entry.get("title"),
                    source_type="company_site",
                )
            )
    return candidates


def crawl_company_site(base_url: str) -> List[CandidatePage]:
    """Return candidate pages found directly on the company's own site."""
    candidates: List[CandidatePage] = []
    seen_urls: set = set()

    # 1 & 2: sitemap discovery
    sitemap_urls = _sitemap_urls_from_robots(base_url) or [
        urljoin(_root(base_url), "/sitemap.xml")
    ]
    all_urls: List[tuple[str, Optional[date]]] = []
    for sm in sitemap_urls:
        all_urls.extend(_parse_sitemap(sm))

    for u, lastmod in _keyword_filter(all_urls):
        # Some sites' sitemaps only list localized URL variants (e.g.
        # only /ja/... and /zh-cn/... for a given article, with no
        # separate entry for the plain English path) even though the
        # English version exists at the same path minus the locale
        # segment. Prefer that English URL when it actually resolves,
        # rather than reporting a non-English page as "the" source.
        u = _resolve_english_url(u)

        if u not in seen_urls:
            seen_urls.add(u)
            candidates.append(
                CandidatePage(url=u, source_type="company_site", sitemap_lastmod=lastmod)
            )

    # 3: RSS/Atom feeds
    for c in _rss_candidates(base_url):
        if c.url and c.url not in seen_urls:
            seen_urls.add(c.url)
            candidates.append(c)

    # 4: fallback path guesses, only if we found almost nothing above
    if len(candidates) < 3:
        for path in COMMON_PATHS:
            guess = urljoin(_root(base_url), path)
            if guess not in seen_urls and _get(guess):
                seen_urls.add(guess)
                candidates.append(CandidatePage(url=guess, source_type="company_site"))

    logger.info("Company-site crawl found %d candidate URLs for %s", len(candidates), base_url)
    return candidates
