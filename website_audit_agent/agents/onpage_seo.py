"""
onpage_seo.py — Per-page on-page SEO analysis across all crawled pages.

Evaluates title tags, meta descriptions, heading structure, image alt text,
URL quality, and identifies orphan/weak pages.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from agents.crawler import CrawlResult
from config import Config

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PageOnPageData:
    """On-page SEO data for a single page."""
    url: str
    title: str = ""
    title_length: int = 0
    title_issue: str = ""          # "missing" | "too_short" | "too_long" | "ok"
    meta_description: str = ""
    meta_desc_length: int = 0
    meta_desc_issue: str = ""
    h1_count: int = 0
    h1_text: str = ""
    h1_issue: str = ""
    heading_hierarchy_ok: bool = True
    total_headings: int = 0
    total_images: int = 0
    images_missing_alt: List[str] = field(default_factory=list)
    images_no_dimensions: int = 0
    unoptimized_images: List[str] = field(default_factory=list)
    url_length: int = 0
    url_has_underscores: bool = False
    url_has_params: bool = False
    url_depth: int = 0
    url_issue: str = ""


@dataclass
class OnPageSEOResult:
    """Aggregated on-page SEO findings for an entire domain."""
    domain: str
    pages: List[PageOnPageData] = field(default_factory=list)
    orphan_pages: List[str] = field(default_factory=list)
    weak_pages: List[str] = field(default_factory=list)
    title_coverage_pct: float = 0.0
    meta_desc_coverage_pct: float = 0.0
    h1_health_pct: float = 0.0
    alt_text_coverage_pct: float = 0.0
    top_issues_pages: List[str] = field(default_factory=list)


# ── Per-page analysis ─────────────────────────────────────────────────────────

def _analyse_title(soup: BeautifulSoup) -> tuple[str, int, str]:
    """Return (title_text, length, issue_code)."""
    tag = soup.find("title")
    if not tag or not tag.text.strip():
        return "", 0, "missing"
    text = tag.text.strip()
    length = len(text)
    if length < 30:
        issue = "too_short"
    elif length > 60:
        issue = "too_long"
    else:
        issue = "ok"
    return text, length, issue


def _analyse_meta_desc(soup: BeautifulSoup) -> tuple[str, int, str]:
    """Return (meta_desc_text, length, issue_code)."""
    tag = soup.find("meta", {"name": lambda n: n and n.lower() == "description"})
    if not tag or not tag.get("content", "").strip():
        return "", 0, "missing"
    text = tag["content"].strip()
    length = len(text)
    if length < 120:
        issue = "too_short"
    elif length > 158:
        issue = "too_long"
    else:
        issue = "ok"
    return text, length, issue


def _analyse_headings(soup: BeautifulSoup) -> tuple[int, str, str, bool, int]:
    """Return (h1_count, h1_text, h1_issue, hierarchy_ok, total_headings)."""
    h_tags = soup.find_all(re.compile(r"^h[1-6]$"))
    total = len(h_tags)
    h1_tags = [t for t in h_tags if t.name == "h1"]
    h1_count = len(h1_tags)
    h1_text = h1_tags[0].get_text(strip=True) if h1_tags else ""

    if h1_count == 0:
        h1_issue = "missing"
    elif h1_count > 1:
        h1_issue = "multiple"
    elif len(h1_text.split()) <= 3:
        h1_issue = "too_short"
    else:
        h1_issue = "ok"

    # Check heading hierarchy (no level jumps, e.g. H1 → H3)
    levels = [int(t.name[1]) for t in h_tags]
    hierarchy_ok = True
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            hierarchy_ok = False
            break

    return h1_count, h1_text, h1_issue, hierarchy_ok, total


def _analyse_images(soup: BeautifulSoup) -> tuple[int, List[str], int, List[str]]:
    """Return (total_images, missing_alt_srcs, no_dimensions_count, unoptimized_srcs)."""
    imgs = soup.find_all("img")
    total = len(imgs)
    missing_alt: List[str] = []
    no_dims = 0
    unoptimized: List[str] = []

    for img in imgs:
        src = img.get("src", "")
        alt = img.get("alt")
        if alt is None or alt.strip() == "":
            missing_alt.append(src)
        if not img.get("width") or not img.get("height"):
            no_dims += 1
        if src.lower().endswith((".bmp", ".tiff", ".tif")):
            unoptimized.append(src)

    return total, missing_alt, no_dims, unoptimized


def _analyse_url(url: str) -> tuple[int, bool, bool, int, str]:
    """Return (length, has_underscores, has_params, depth, issue)."""
    parsed = urlparse(url)
    path = parsed.path
    length = len(url)
    has_underscores = "_" in path
    has_params = bool(parsed.query)
    depth = path.strip("/").count("/") + 1 if path.strip("/") else 0

    issues = []
    if length > 75:
        issues.append("too_long")
    if has_underscores:
        issues.append("underscores")
    if has_params:
        issues.append("params")
    if depth > 4:
        issues.append("deep")

    return length, has_underscores, has_params, depth, "|".join(issues) or "ok"


def _analyse_page(page) -> PageOnPageData:
    """Run all on-page checks for a single crawled page."""
    soup = BeautifulSoup(page.html, "lxml")
    data = PageOnPageData(url=page.page_url)

    data.title, data.title_length, data.title_issue = _analyse_title(soup)
    data.meta_description, data.meta_desc_length, data.meta_desc_issue = _analyse_meta_desc(soup)
    (
        data.h1_count,
        data.h1_text,
        data.h1_issue,
        data.heading_hierarchy_ok,
        data.total_headings,
    ) = _analyse_headings(soup)
    (
        data.total_images,
        data.images_missing_alt,
        data.images_no_dimensions,
        data.unoptimized_images,
    ) = _analyse_images(soup)
    (
        data.url_length,
        data.url_has_underscores,
        data.url_has_params,
        data.url_depth,
        data.url_issue,
    ) = _analyse_url(page.page_url)

    return data


def _issue_count(page_data: PageOnPageData) -> int:
    """Return a simple count of distinct issues on a page (for ranking)."""
    count = 0
    if page_data.title_issue != "ok":
        count += 1
    if page_data.meta_desc_issue != "ok":
        count += 1
    if page_data.h1_issue != "ok":
        count += 1
    count += len(page_data.images_missing_alt)
    if page_data.url_issue != "ok":
        count += 1
    return count


# ── Public API ────────────────────────────────────────────────────────────────

def run_onpage_seo(crawl: CrawlResult) -> OnPageSEOResult:
    """
    Analyse on-page SEO factors for all pages in *crawl*.

    Returns an OnPageSEOResult with per-page data and site-wide aggregate flags.
    """
    result = OnPageSEOResult(domain=crawl.domain)
    logger.info("Running on-page SEO analysis for %s", crawl.domain)

    for page in crawl.pages:
        page_data = _analyse_page(page)
        result.pages.append(page_data)

    total = len(result.pages)
    if total == 0:
        return result

    # Coverage metrics
    with_title = sum(1 for p in result.pages if p.title_issue not in ("missing",))
    with_meta = sum(1 for p in result.pages if p.meta_desc_issue not in ("missing",))
    good_h1 = sum(1 for p in result.pages if p.h1_issue == "ok")

    total_images = sum(p.total_images for p in result.pages)
    images_with_alt = sum(p.total_images - len(p.images_missing_alt) for p in result.pages)

    result.title_coverage_pct = round(with_title / total * 100, 1)
    result.meta_desc_coverage_pct = round(with_meta / total * 100, 1)
    result.h1_health_pct = round(good_h1 / total * 100, 1)
    result.alt_text_coverage_pct = (
        round(images_with_alt / total_images * 100, 1) if total_images > 0 else 100.0
    )

    # Orphan and weak pages (based on inbound internal links)
    inbound_counts: Dict[str, int] = {p.url: 0 for p in result.pages}
    for source, targets in crawl.internal_link_map.items():
        for t in targets:
            norm = t.rstrip("/")
            for key in list(inbound_counts.keys()):
                if key.rstrip("/") == norm:
                    inbound_counts[key] += 1

    for url, count in inbound_counts.items():
        if url == crawl.domain.rstrip("/"):
            continue  # skip homepage
        if count == 0:
            result.orphan_pages.append(url)
        elif count == 1:
            result.weak_pages.append(url)

    # Top 5 pages with most issues
    ranked = sorted(result.pages, key=_issue_count, reverse=True)
    result.top_issues_pages = [p.url for p in ranked[:5]]

    logger.info(
        "On-page SEO done for %s — %d pages, %.0f%% title coverage",
        crawl.domain, total, result.title_coverage_pct,
    )
    return result
