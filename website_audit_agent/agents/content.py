"""
content.py — Content quality analysis for all crawled pages.

Evaluates word count, readability (Flesch, Gunning Fog), freshness,
duplicate content detection, multimedia presence, and produces
a content action map (Keep / Update / Merge / Delete).
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import textstat
from bs4 import BeautifulSoup

from agents.crawler import CrawlResult

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PageContentData:
    """Content metrics for a single crawled page."""
    url: str
    word_count: int = 0
    flesch_reading_ease: float = 0.0
    flesch_kincaid_grade: float = 0.0
    gunning_fog: float = 0.0
    date_found: Optional[str] = None
    body_hash: str = ""
    image_count: int = 0
    iframe_count: int = 0
    audio_count: int = 0
    action: str = "Keep"          # Keep | Update | Merge | Delete
    thin_content: bool = False
    very_thin_content: bool = False
    duplicate_of: Optional[str] = None


@dataclass
class ContentResult:
    """Aggregated content analysis for an entire domain."""
    domain: str
    pages: List[PageContentData] = field(default_factory=list)
    thin_content_urls: List[str] = field(default_factory=list)
    duplicate_groups: List[List[str]] = field(default_factory=list)
    action_counts: Dict[str, int] = field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

# Tags whose text is typically UI chrome, not content
_NOISE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}

_DATE_PATTERNS = [
    re.compile(r'\d{4}-\d{2}-\d{2}'),
    re.compile(r'\d{1,2}/\d{1,2}/\d{4}'),
    re.compile(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s+\d{4}', re.I),
]

_KEY_PAGE_KEYWORDS = {"home", "contact", "about", "services", "product", "category"}


def _extract_visible_text(html: str) -> str:
    """Strip noise tags and return only visible body text."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(_NOISE_TAGS):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)


def _count_words(text: str) -> int:
    """Count whitespace-delimited words in *text*."""
    return len(text.split())


def _extract_date(html: str) -> Optional[str]:
    """Try to find a publication/modification date signal in page HTML."""
    # Check <meta> tags first
    soup = BeautifulSoup(html, "lxml")
    for attr in ("article:published_time", "datePublished", "date", "DC.date"):
        tag = soup.find("meta", {"property": attr}) or soup.find("meta", {"name": attr})
        if tag and tag.get("content"):
            return tag["content"][:10]

    # Check <time> element
    time_tag = soup.find("time")
    if time_tag and time_tag.get("datetime"):
        return time_tag["datetime"][:10]

    # Fallback: scan visible text
    text = soup.get_text()
    for pattern in _DATE_PATTERNS:
        m = pattern.search(text)
        if m:
            return m.group(0)

    return None


def _body_hash(text: str) -> str:
    """Return a short MD5 of normalised body text for duplicate detection."""
    normalised = re.sub(r'\s+', ' ', text.lower().strip())
    return hashlib.md5(normalised.encode()).hexdigest()


def _is_key_page(url: str) -> bool:
    """Heuristic: homepage or URL containing a key-page keyword."""
    path = url.rstrip("/").split("/")[-1].lower()
    return not path or any(kw in path for kw in _KEY_PAGE_KEYWORDS)


def _assign_action(
    data: PageContentData,
    duplicate_hashes: Dict[str, str],
) -> str:
    """
    Apply the content action map logic:
      word_count > 300 AND readability ok AND not duplicate → Keep
      word_count < 300 AND key page → Update
      duplicate hash match → Merge
      word_count < 150 AND not key page → Delete
    """
    if data.body_hash in duplicate_hashes and duplicate_hashes[data.body_hash] != data.url:
        data.duplicate_of = duplicate_hashes[data.body_hash]
        return "Merge"
    if data.word_count < 150 and not _is_key_page(data.url):
        return "Delete"
    if data.word_count < 300:
        if _is_key_page(data.url):
            return "Update"
        return "Delete"
    if data.gunning_fog > 12:
        return "Update"
    return "Keep"


# ── Public API ────────────────────────────────────────────────────────────────

def run_content_analysis(crawl: CrawlResult) -> ContentResult:
    """
    Analyse content quality for every page in *crawl*.

    Returns a ContentResult with per-page metrics and a content action map.
    """
    result = ContentResult(domain=crawl.domain)
    logger.info("Running content analysis for %s", crawl.domain)

    # First pass: compute per-page data
    hash_first_seen: Dict[str, str] = {}  # hash → first url
    page_data_list: List[PageContentData] = []

    for page in crawl.pages:
        text = _extract_visible_text(page.html)
        word_count = _count_words(text)
        body_hash = _body_hash(text)

        # Track first occurrence per hash
        if body_hash not in hash_first_seen:
            hash_first_seen[body_hash] = page.page_url

        soup_raw = BeautifulSoup(page.html, "lxml")
        pd = PageContentData(
            url=page.page_url,
            word_count=word_count,
            flesch_reading_ease=textstat.flesch_reading_ease(text) if text else 0.0,
            flesch_kincaid_grade=textstat.flesch_kincaid_grade(text) if text else 0.0,
            gunning_fog=textstat.gunning_fog(text) if text else 0.0,
            date_found=_extract_date(page.html),
            body_hash=body_hash,
            image_count=len(soup_raw.find_all("img")),
            iframe_count=len(soup_raw.find_all("iframe")),
            audio_count=len(soup_raw.find_all("audio")),
            thin_content=word_count < 300,
            very_thin_content=word_count < 150,
        )
        page_data_list.append(pd)

    # Second pass: assign actions with full hash map available
    for pd in page_data_list:
        pd.action = _assign_action(pd, hash_first_seen)
        result.pages.append(pd)

    # Thin content list
    result.thin_content_urls = [p.url for p in result.pages if p.thin_content]

    # Duplicate groups
    dup_map: Dict[str, List[str]] = {}
    for pd in result.pages:
        dup_map.setdefault(pd.body_hash, []).append(pd.url)
    result.duplicate_groups = [urls for urls in dup_map.values() if len(urls) > 1]

    # Action counts
    for action in ("Keep", "Update", "Merge", "Delete"):
        result.action_counts[action] = sum(1 for p in result.pages if p.action == action)

    logger.info(
        "Content analysis done for %s — %d pages, %d thin, %d duplicates",
        crawl.domain,
        len(result.pages),
        len(result.thin_content_urls),
        len(result.duplicate_groups),
    )
    return result
