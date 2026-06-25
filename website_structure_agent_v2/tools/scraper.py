"""
tools/scraper.py
Tavily-powered competitor and target site scraper.
Primary: Tavily Search API  |  Fallback: requests + BeautifulSoup
"""
import re
import logging
from typing import List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient

from config import settings

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _bs4_scrape(url: str) -> dict:
    """Fallback: requests + BeautifulSoup HTML scraper."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.warning(f"BS4 scrape failed for {url}: {e}")
        return {"raw_content": "", "nav_labels": [], "url_patterns": [], "error": str(e)}

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    # Nav labels
    nav_labels = []
    for nav in soup.find_all(["nav", "header"]):
        for link in nav.find_all("a"):
            text = link.get_text(strip=True)
            if text and len(text) < 50 and text not in nav_labels:
                nav_labels.append(text)

    # URL patterns from internal links
    base_domain  = urlparse(url).netloc
    url_patterns = set()
    for a in soup.find_all("a", href=True):
        href   = a["href"]
        parsed = urlparse(href)
        if parsed.netloc in ("", base_domain):
            path  = parsed.path.strip("/")
            if path:
                parts   = path.split("/")
                pattern = "/" + "/".join(
                    ["*" if re.match(r"^\d+$", p) else p for p in parts]
                )
                url_patterns.add(pattern)

    raw_text = soup.get_text(separator=" ", strip=True)
    return {
        "raw_content":  raw_text[:4000],
        "nav_labels":   nav_labels[:20],
        "url_patterns": list(url_patterns)[:30],
        "error":        None,
    }


def _tavily_scrape(url: str) -> dict:
    """Primary: Tavily Search API to get content about the URL's structure."""
    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        domain = urlparse(url).netloc
        result = client.search(
            query              = f"site:{domain} navigation sitemap pages structure",
            search_depth       = "basic",
            max_results        = 5,
            include_raw_content= True,
        )
        parts = []
        for r in result.get("results", []):
            raw = r.get("raw_content") or r.get("content", "")
            if raw:
                parts.append(raw[:800])
        return {"raw_content": " | ".join(parts)[:4000], "error": None}
    except Exception as e:
        logger.warning(f"Tavily scrape failed for {url}: {e}")
        return {"raw_content": "", "error": str(e)}


# ── Public API ────────────────────────────────────────────────────────────────

def scrape_website(url: str) -> dict:
    """
    Scrape a single website.
    Tries Tavily first; merges with BeautifulSoup for nav/URL data.
    Returns dict with: url, raw_content, nav_labels, url_patterns,
                       content_depth, page_count, error
    """
    url          = _normalise_url(url)
    tavily_data  = _tavily_scrape(url)
    bs4_data     = _bs4_scrape(url)

    raw_content  = bs4_data.get("raw_content") or tavily_data.get("raw_content", "")
    nav_labels   = bs4_data.get("nav_labels",   [])
    url_patterns = bs4_data.get("url_patterns", [])

    content_depth = max(
        (len(p.split("/")) - 1 for p in url_patterns if p),
        default=2,
    )
    page_count = max(len(url_patterns), 10)

    error = None
    if not raw_content:
        error = tavily_data.get("error") or bs4_data.get("error") or "No content extracted"

    logger.info(f"Scraped {url} | nav={len(nav_labels)} urls={len(url_patterns)} depth={content_depth}")
    return {
        "url":           url,
        "raw_content":   raw_content,
        "nav_labels":    nav_labels,
        "url_patterns":  url_patterns,
        "content_depth": content_depth,
        "page_count":    page_count,
        "error":         error,
    }


def scrape_multiple(urls: List[str]) -> List[dict]:
    """Scrape multiple URLs sequentially."""
    return [scrape_website(u) for u in urls]
