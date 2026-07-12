"""
website_parser_tool.py — Website/URL parser.

Mirrors the "Website Parser1" / "Website parser" sub-workflow tool ("Parser"
workflow, id OzM394pggyuOIbsr) used by the Keyword Research, SEO Audit and
SMM Gap Analysis agents to extract on-page content from a URL.
"""

from __future__ import annotations

import re

import requests
from bs4 import BeautifulSoup
from langchain.tools import tool


@tool("website_parser", return_direct=False)
def website_parser(url: str) -> str:
    """Parse a website URL and return its navigation, headings (H1/H2), hero
    copy, and visible text content — used to extract seed keywords, product
    or service names, and social presence info."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (DM-Audit-Agent)"},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        title = soup.title.string.strip() if soup.title and soup.title.string else "N/A"
        h1s = [h.get_text(strip=True) for h in soup.find_all("h1")][:10]
        h2s = [h.get_text(strip=True) for h in soup.find_all("h2")][:15]

        nav_links = []
        for nav in soup.find_all(["nav"]):
            for a in nav.find_all("a"):
                text = a.get_text(strip=True)
                if text:
                    nav_links.append(text)
        nav_links = nav_links[:20]

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        body_text = re.sub(r"\s+", " ", soup.get_text(separator=" ", strip=True))
        body_text = body_text[:3000]

        result = (
            f"URL: {url}\n"
            f"Title: {title}\n"
            f"Nav_Links: {', '.join(nav_links) if nav_links else 'N/A'}\n"
            f"H1: {', '.join(h1s) if h1s else 'N/A'}\n"
            f"H2: {', '.join(h2s) if h2s else 'N/A'}\n"
            f"Body_Excerpt: {body_text}\n"
        )
        return result
    except Exception as exc:
        return f"Parser Tool Unavailable for {url}. Error: {exc}"
