"""
crawler.py — Fetches robots.txt, parses sitemaps, and crawls up to N pages.

Returns a CrawlResult containing per-page metadata, broken links,
redirect chains, and an internal link graph.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import Config

logger = logging.getLogger(__name__)


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PageData:
    """Metadata collected for a single crawled page."""
    page_url: str
    status_code: int
    redirect_chain: List[str] = field(default_factory=list)
    response_time_ms: float = 0.0
    content_type: str = ""
    page_size_bytes: int = 0
    canonical_url: Optional[str] = None
    meta_robots: str = ""
    html: str = ""


@dataclass
class CrawlResult:
    """All data returned by the crawler for one domain."""
    domain: str
    pages: List[PageData] = field(default_factory=list)
    broken_links: List[str] = field(default_factory=list)
    redirect_issues: List[Tuple[str, List[str]]] = field(default_factory=list)
    internal_link_map: Dict[str, List[str]] = field(default_factory=dict)
    sitemap_urls: List[str] = field(default_factory=list)
    robots_txt: str = ""
    disallowed_paths: List[str] = field(default_factory=list)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _same_domain(url: str, base: str) -> bool:
    """Return True when *url* belongs to the same registrable domain as *base*."""
    return urlparse(url).netloc == urlparse(base).netloc


def _fetch(url: str, session: requests.Session, timeout: int = None) -> requests.Response:
    """GET *url* with a shared session, honouring config timeout."""
    timeout = timeout or Config.CRAWL_TIMEOUT
    return session.get(
        url,
        headers=Config.DEFAULT_HEADERS,
        timeout=timeout,
        allow_redirects=True,
    )


def _parse_robots(domain: str, session: requests.Session) -> Tuple[str, List[str]]:
    """Fetch and parse robots.txt; return raw text and list of disallowed paths."""
    robots_url = urljoin(domain, "/robots.txt")
    disallowed: List[str] = []
    raw = ""
    try:
        resp = _fetch(robots_url, session)
        if resp.status_code == 200:
            raw = resp.text
            for line in raw.splitlines():
                line = line.strip()
                if line.lower().startswith("disallow:"):
                    path = line.split(":", 1)[1].strip()
                    if path:
                        disallowed.append(path)
        logger.debug("robots.txt fetched for %s — %d disallowed paths", domain, len(disallowed))
    except Exception as exc:
        logger.warning("Could not fetch robots.txt for %s: %s", domain, exc)
    return raw, disallowed


def _is_disallowed(url: str, disallowed_paths: List[str]) -> bool:
    """Check whether *url*'s path matches any disallowed prefix."""
    path = urlparse(url).path
    return any(path.startswith(dp) for dp in disallowed_paths if dp)


def _fetch_sitemap_urls(domain: str, session: requests.Session) -> List[str]:
    """Recursively fetch all page URLs from sitemap.xml (handles sitemap index)."""
    urls: List[str] = []
    to_process = [urljoin(domain, "/sitemap.xml")]
    visited: Set[str] = set()

    while to_process:
        sitemap_url = to_process.pop(0)
        if sitemap_url in visited:
            continue
        visited.add(sitemap_url)
        try:
            resp = _fetch(sitemap_url, session)
            if resp.status_code != 200:
                continue
            soup = BeautifulSoup(resp.content, "xml")
            # Sitemap index
            for loc in soup.find_all("sitemap"):
                child = loc.find("loc")
                if child:
                    to_process.append(child.text.strip())
            # Regular sitemap
            for loc in soup.find_all("url"):
                child = loc.find("loc")
                if child:
                    urls.append(child.text.strip())
        except Exception as exc:
            logger.warning("Sitemap fetch failed for %s: %s", sitemap_url, exc)

    logger.debug("Sitemap extracted %d URLs from %s", len(urls), domain)
    return urls


def _extract_page_metadata(url: str, resp: requests.Response) -> PageData:
    """Build a PageData object from a completed HTTP response."""
    soup = BeautifulSoup(resp.content, "lxml")

    # Canonical
    canonical_tag = soup.find("link", {"rel": "canonical"})
    canonical = canonical_tag["href"] if canonical_tag and canonical_tag.get("href") else None

    # Meta robots
    robots_tag = soup.find("meta", {"name": lambda n: n and n.lower() == "robots"})
    meta_robots = robots_tag.get("content", "") if robots_tag else ""

    # Redirect chain from response history
    chain = [r.url for r in resp.history] + [resp.url]

    return PageData(
        page_url=url,
        status_code=resp.status_code,
        redirect_chain=chain,
        response_time_ms=resp.elapsed.total_seconds() * 1000,
        content_type=resp.headers.get("content-type", ""),
        page_size_bytes=len(resp.content),
        canonical_url=canonical,
        meta_robots=meta_robots,
        html=resp.text,
    )


def _collect_links(html: str, base_url: str) -> List[str]:
    """Return all href links found in *html*, resolved against *base_url*."""
    soup = BeautifulSoup(html, "lxml")
    links: List[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if href.startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        # Keep only http/https
        if parsed.scheme in ("http", "https"):
            links.append(full)
    return links


# ── Public API ────────────────────────────────────────────────────────────────

def crawl_domain(domain: str) -> CrawlResult:
    """
    Entry point: crawl *domain* up to Config.CRAWL_MAX_PAGES pages.

    Steps:
      1. Fetch robots.txt
      2. Parse sitemap.xml
      3. BFS crawl from homepage, respecting robots.txt and page limit
      4. Collect per-page metadata, broken links, redirect issues, link graph
    """
    result = CrawlResult(domain=domain)
    session = requests.Session()

    logger.info("Starting crawl for %s", domain)

    # Step 1 — robots.txt
    result.robots_txt, result.disallowed_paths = _parse_robots(domain, session)

    # Step 2 — sitemap
    result.sitemap_urls = _fetch_sitemap_urls(domain, session)

    # Seed queue: sitemap URLs first, then homepage
    seed_urls: List[str] = [domain]
    if result.sitemap_urls:
        # Prioritise sitemap URLs that belong to same domain
        same_domain_sitemap = [u for u in result.sitemap_urls if _same_domain(u, domain)]
        seed_urls = same_domain_sitemap[:Config.CRAWL_MAX_PAGES] + seed_urls

    to_visit: List[str] = list(dict.fromkeys(seed_urls))  # deduplicate, preserve order
    visited: Set[str] = set()

    while to_visit and len(result.pages) < Config.CRAWL_MAX_PAGES:
        url = to_visit.pop(0)

        # Normalise — strip fragment
        url = url.split("#")[0].rstrip("/") or url

        if url in visited:
            continue
        visited.add(url)

        if _is_disallowed(url, result.disallowed_paths):
            logger.debug("Skipping disallowed URL: %s", url)
            continue

        try:
            time.sleep(Config.CRAWL_DELAY_SECONDS)
            resp = _fetch(url, session)
        except Exception as exc:
            logger.warning("Request failed for %s: %s", url, exc)
            result.broken_links.append(url)
            continue

        # Broken link detection
        if resp.status_code >= 400:
            result.broken_links.append(url)
            logger.debug("Broken link detected: %s (%d)", url, resp.status_code)
            continue

        # Redirect chain length check
        if len(resp.history) > 2:
            chain = [r.url for r in resp.history] + [resp.url]
            result.redirect_issues.append((url, chain))
            logger.debug("Long redirect chain for %s: %s", url, chain)

        # Only process HTML pages
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type:
            continue

        page_data = _extract_page_metadata(url, resp)
        result.pages.append(page_data)

        # Extract internal links for BFS + link graph
        links = _collect_links(resp.text, url)
        internal = [l for l in links if _same_domain(l, domain)]
        result.internal_link_map[url] = internal

        # Enqueue unvisited internal links
        for link in internal:
            norm = link.split("#")[0].rstrip("/") or link
            if norm not in visited and len(to_visit) < Config.CRAWL_MAX_PAGES * 3:
                to_visit.append(norm)

        logger.debug("Crawled: %s (%d)", url, resp.status_code)

    logger.info(
        "Crawl complete for %s — %d pages, %d broken links",
        domain, len(result.pages), len(result.broken_links),
    )
    return result
