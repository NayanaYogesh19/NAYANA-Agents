"""
technical_seo.py — Runs technical SEO checks against a crawled domain.

Checks: HTTPS/SSL, crawlability, indexability, structured data,
mobile viewport, and internal/external link counts.
"""

from __future__ import annotations

import logging
import re
import socket
import ssl
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import extruct
import requests
from bs4 import BeautifulSoup

from agents.crawler import CrawlResult
from config import Config

logger = logging.getLogger(__name__)

# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class Check:
    """A single technical SEO check result."""
    name: str
    status: str          # "pass" | "fail" | "warning"
    detail: str = ""
    value: Any = None


@dataclass
class TechnicalSEOResult:
    """All technical SEO findings for one domain."""
    domain: str
    checks: List[Check] = field(default_factory=list)
    structured_data_types: List[str] = field(default_factory=list)
    broken_internal_links: List[str] = field(default_factory=list)
    mobile_screenshot_path: Optional[str] = None
    internal_link_count: int = 0
    external_link_count: int = 0


# ── Individual check functions ────────────────────────────────────────────────

def _check_https(domain: str, session: requests.Session) -> List[Check]:
    """Verify HTTPS availability, HTTP→HTTPS redirect, and SSL certificate."""
    checks: List[Check] = []
    parsed = urlparse(domain)
    host = parsed.hostname or ""

    # Is site on HTTPS?
    is_https = parsed.scheme == "https"
    checks.append(Check(
        name="HTTPS Enabled",
        status="pass" if is_https else "fail",
        detail="Site is served over HTTPS" if is_https else "Site is NOT on HTTPS",
    ))

    # HTTP → HTTPS redirect
    if is_https:
        http_url = domain.replace("https://", "http://", 1)
        try:
            resp = session.get(
                http_url,
                headers=Config.DEFAULT_HEADERS,
                timeout=Config.CRAWL_TIMEOUT,
                allow_redirects=True,
            )
            redirected_to_https = resp.url.startswith("https://")
            checks.append(Check(
                name="HTTP→HTTPS Redirect",
                status="pass" if redirected_to_https else "fail",
                detail=f"HTTP redirects to: {resp.url}",
            ))
        except Exception as exc:
            checks.append(Check(
                name="HTTP→HTTPS Redirect",
                status="warning",
                detail=f"Could not test redirect: {exc}",
            ))

    # SSL certificate validity
    try:
        ctx = ssl.create_default_context()
        with ctx.wrap_socket(socket.socket(), server_hostname=host) as sock:
            sock.settimeout(Config.CRAWL_TIMEOUT)
            sock.connect((host, 443))
            cert = sock.getpeercert()
            checks.append(Check(
                name="SSL Certificate Valid",
                status="pass",
                detail=f"Cert subject: {cert.get('subject')}",
                value=cert,
            ))
    except Exception as exc:
        checks.append(Check(
            name="SSL Certificate Valid",
            status="fail",
            detail=f"SSL error: {exc}",
        ))

    return checks


def _check_mixed_content(pages_html: List[str]) -> Check:
    """Scan page HTML for http:// references in src/href attributes."""
    found_on: List[str] = []
    pattern = re.compile(r'(?:src|href)=["\']http://', re.IGNORECASE)
    for i, html in enumerate(pages_html[:5]):  # check first 5 pages only
        if pattern.search(html):
            found_on.append(f"page_{i+1}")
    if found_on:
        return Check(
            name="No Mixed Content",
            status="warning",
            detail=f"Mixed content found on: {', '.join(found_on)}",
        )
    return Check(name="No Mixed Content", status="pass", detail="No mixed content detected")


def _check_robots(crawl: CrawlResult, session: requests.Session) -> List[Check]:
    """Check robots.txt presence, parseability, and sitemap reference."""
    checks: List[Check] = []

    has_robots = bool(crawl.robots_txt)
    checks.append(Check(
        name="robots.txt Present",
        status="pass" if has_robots else "fail",
        detail="robots.txt found and parsed" if has_robots else "No robots.txt found",
    ))

    sitemap_in_robots = "sitemap:" in crawl.robots_txt.lower() if crawl.robots_txt else False
    checks.append(Check(
        name="Sitemap in robots.txt",
        status="pass" if sitemap_in_robots else "warning",
        detail="Sitemap directive found in robots.txt" if sitemap_in_robots else "No sitemap: directive in robots.txt",
    ))

    return checks


def _check_sitemap(crawl: CrawlResult) -> Check:
    """Check whether the sitemap returned any URLs."""
    has_sitemap = len(crawl.sitemap_urls) > 0
    return Check(
        name="Sitemap Present",
        status="pass" if has_sitemap else "fail",
        detail=f"{len(crawl.sitemap_urls)} URLs found in sitemap" if has_sitemap else "No sitemap.xml found",
    )


def _check_key_pages_blocked(crawl: CrawlResult) -> Check:
    """Flag if homepage or key pages are blocked by robots.txt."""
    blocked = []
    for path in crawl.disallowed_paths:
        if path in ("/", ""):
            blocked.append(path)
    if blocked:
        return Check(
            name="Key Pages Not Blocked",
            status="fail",
            detail=f"Homepage or root blocked by robots.txt: {blocked}",
        )
    return Check(name="Key Pages Not Blocked", status="pass", detail="Homepage not blocked")


def _check_noindex(pages: list) -> Check:
    """Check for noindex on homepage or top pages."""
    noindex_pages = []
    for p in pages[:10]:
        if "noindex" in p.meta_robots.lower():
            noindex_pages.append(p.page_url)
    if noindex_pages:
        return Check(
            name="No Noindex on Key Pages",
            status="fail",
            detail=f"noindex found on: {noindex_pages[:5]}",
        )
    return Check(name="No Noindex on Key Pages", status="pass", detail="No noindex on key pages")


def _check_canonicals(pages: list) -> Check:
    """Detect canonical tags pointing away from the page URL."""
    issues = []
    for p in pages:
        if p.canonical_url and p.canonical_url != p.page_url:
            # Allow trailing slash differences
            norm_page = p.page_url.rstrip("/")
            norm_canon = p.canonical_url.rstrip("/")
            if norm_page != norm_canon:
                issues.append(f"{p.page_url} → {p.canonical_url}")
    if issues:
        return Check(
            name="Canonical Tags Valid",
            status="warning",
            detail=f"{len(issues)} non-self canonicals found: {issues[:3]}",
        )
    return Check(name="Canonical Tags Valid", status="pass", detail="All canonicals self-reference or are absent")


def _check_duplicate_titles(pages: list) -> Check:
    """Detect duplicate title tags across crawled pages."""
    titles: List[str] = []
    for p in pages:
        soup = BeautifulSoup(p.html, "lxml")
        tag = soup.find("title")
        if tag and tag.text.strip():
            titles.append(tag.text.strip())
    dupes = len(titles) - len(set(titles))
    if dupes > 0:
        return Check(
            name="Unique Title Tags",
            status="fail",
            detail=f"{dupes} duplicate title tags detected",
            value=dupes,
        )
    return Check(name="Unique Title Tags", status="pass", detail="All title tags are unique")


def _check_duplicate_metas(pages: list) -> Check:
    """Detect duplicate meta descriptions across crawled pages."""
    metas: List[str] = []
    for p in pages:
        soup = BeautifulSoup(p.html, "lxml")
        tag = soup.find("meta", {"name": lambda n: n and n.lower() == "description"})
        if tag and tag.get("content", "").strip():
            metas.append(tag["content"].strip())
    dupes = len(metas) - len(set(metas))
    if dupes > 0:
        return Check(
            name="Unique Meta Descriptions",
            status="fail",
            detail=f"{dupes} duplicate meta descriptions detected",
            value=dupes,
        )
    return Check(name="Unique Meta Descriptions", status="pass", detail="All meta descriptions are unique")


def _check_structured_data(domain: str, homepage_html: str) -> tuple[Check, List[str]]:
    """Extract structured data from homepage using extruct."""
    types_found: List[str] = []
    try:
        base_url = domain
        data = extruct.extract(
            homepage_html,
            base_url=base_url,
            syntaxes=["json-ld", "microdata", "opengraph"],
            uniform=True,
        )
        for item in data.get("json-ld", []):
            t = item.get("@type")
            if t:
                types_found.append(str(t))
        for item in data.get("microdata", []):
            t = item.get("type")
            if t:
                types_found.append(str(t))
        if data.get("opengraph"):
            types_found.append("OpenGraph")
    except Exception as exc:
        logger.warning("extruct failed: %s", exc)

    types_found = list(set(types_found))
    if types_found:
        return (
            Check(
                name="Structured Data Present",
                status="pass",
                detail=f"Schema types found: {', '.join(types_found)}",
                value=types_found,
            ),
            types_found,
        )
    return (
        Check(
            name="Structured Data Present",
            status="fail",
            detail="No structured data found on homepage",
        ),
        [],
    )


def _check_viewport(homepage_html: str) -> Check:
    """Check for viewport meta tag."""
    soup = BeautifulSoup(homepage_html, "lxml")
    vp = soup.find("meta", {"name": lambda n: n and n.lower() == "viewport"})
    if vp:
        return Check(
            name="Viewport Meta Tag",
            status="pass",
            detail=f"viewport: {vp.get('content', '')}",
        )
    return Check(name="Viewport Meta Tag", status="fail", detail="No viewport meta tag found")


def _count_links(homepage_html: str, domain: str) -> tuple[int, int]:
    """Return (internal_link_count, external_link_count) for homepage."""
    soup = BeautifulSoup(homepage_html, "lxml")
    internal = external = 0
    parsed_base = urlparse(domain)
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        parsed = urlparse(urljoin(domain, href))
        if parsed.netloc == parsed_base.netloc:
            internal += 1
        elif parsed.netloc:
            external += 1
    return internal, external


def _mobile_screenshot(domain: str) -> Optional[str]:
    """Attempt to capture a mobile screenshot via Playwright; return file path or None."""
    try:
        from playwright.sync_api import sync_playwright
        import os

        output_dir = Config.REPORT_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        host = urlparse(domain).netloc.replace(".", "_")
        path = os.path.join(output_dir, f"{host}_mobile.png")

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 375, "height": 812})
            page.goto(domain, timeout=Config.PLAYWRIGHT_TIMEOUT)
            page.wait_for_load_state("networkidle", timeout=Config.PLAYWRIGHT_TIMEOUT)
            page.screenshot(path=path, full_page=True)
            browser.close()
        logger.info("Mobile screenshot saved: %s", path)
        return path
    except Exception as exc:
        logger.warning("Playwright mobile screenshot failed: %s", exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def run_technical_seo(crawl: CrawlResult) -> TechnicalSEOResult:
    """
    Run all technical SEO checks against *crawl* data.

    Returns a TechnicalSEOResult with per-check status and aggregated findings.
    """
    result = TechnicalSEOResult(domain=crawl.domain)
    session = requests.Session()

    homepage_html = ""
    if crawl.pages:
        homepage_html = crawl.pages[0].html

    logger.info("Running technical SEO checks for %s", crawl.domain)

    # HTTPS & Security
    result.checks.extend(_check_https(crawl.domain, session))
    if homepage_html:
        result.checks.append(_check_mixed_content([p.html for p in crawl.pages[:5]]))

    # Crawlability
    result.checks.extend(_check_robots(crawl, session))
    result.checks.append(_check_sitemap(crawl))
    result.checks.append(_check_key_pages_blocked(crawl))

    # Indexability
    if crawl.pages:
        result.checks.append(_check_noindex(crawl.pages))
        result.checks.append(_check_canonicals(crawl.pages))
        result.checks.append(_check_duplicate_titles(crawl.pages))
        result.checks.append(_check_duplicate_metas(crawl.pages))

    # Structured data
    if homepage_html:
        sd_check, sd_types = _check_structured_data(crawl.domain, homepage_html)
        result.checks.append(sd_check)
        result.structured_data_types = sd_types

    # Mobile viewport
    if homepage_html:
        result.checks.append(_check_viewport(homepage_html))

    # Link counts
    if homepage_html:
        ic, ec = _count_links(homepage_html, crawl.domain)
        result.internal_link_count = ic
        result.external_link_count = ec

    # Broken internal links
    result.broken_internal_links = list(crawl.broken_links)

    # Mobile screenshot (best-effort)
    result.mobile_screenshot_path = _mobile_screenshot(crawl.domain)

    logger.info(
        "Technical SEO done for %s — %d checks run",
        crawl.domain, len(result.checks),
    )
    return result
