"""Orchestrates the full run for one company URL + date range.

Deliberately a plain, deterministic function rather than a free-roaming
agent loop: given the same inputs, it always takes the same steps in
the same order. The LLM is used only inside classifier.py, for the one
task (does this page belong, and what's a good title) that genuinely
needs judgement. Everything else — what to search for, how to filter
by date, how to dedupe — is ordinary code, which is what makes the run
predictable and debuggable.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Callable, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from config import settings
from agent import http
from agent.models import CandidatePage, CompanyReport, ReportItem
from agent.site_crawler import crawl_company_site
from agent.web_search import search_all_categories
from agent.extractor import extract, within_window
from agent.classifier import classify
from agent.dedupe import dedupe_items
from agent.archiver import save_page_now

logger = logging.getLogger(__name__)


def _guess_company_name(url: str) -> str:
    """Best-effort company name: try the <title>/og:site_name, fall back
    to the domain. Used to build search queries and label the report.
    """
    resp = http.get(url)
    if resp is not None:
        soup = BeautifulSoup(resp.content, "html.parser")
        og = soup.find("meta", property="og:site_name")
        if og and og.get("content"):
            return og["content"].strip()
        if soup.title and soup.title.text:
            # Titles are often "Company Name | Tagline" — take the first chunk.
            return soup.title.text.split("|")[0].split("-")[0].strip()
    else:
        logger.debug("Could not fetch %s to guess company name", url)

    domain = urlparse(url).netloc.replace("www.", "")
    return domain.split(".")[0].capitalize()


def _process_candidates(
    candidates: List[CandidatePage], company_name: str, start: date, end: date
) -> List[ReportItem]:
    items: List[ReportItem] = []
    for candidate in candidates:
        enriched = extract(candidate)
        if not enriched:
            continue
        if not within_window(enriched, start, end):
            logger.debug(
                "Dropping %s: published_date %s outside %s..%s",
                enriched.url, enriched.published_date, start, end,
            )
            continue
        item = classify(enriched, company_name, start, end)
        if item:
            items.append(item)
    return items


def run(
    company_url: str,
    start: date,
    end: date,
    on_progress: Optional[Callable[[str], None]] = None,
) -> CompanyReport:
    """Runs the full pipeline for one company and returns a CompanyReport.

    `on_progress`, if given, is called with short human-readable status
    strings as each stage starts — purely cosmetic (e.g. for a UI
    progress indicator), the pipeline's behavior does not depend on it.
    """
    def notify(stage: str) -> None:
        if on_progress:
            on_progress(stage)

    settings.validate()

    notify("Identifying company")
    company_name = _guess_company_name(company_url)
    logger.info("Running report for %s (%s) — window %s to %s", company_name, company_url, start, end)

    report = CompanyReport(
        company_name=company_name,
        company_url=company_url,
        period_start=start,
        period_end=end,
    )

    # 1. Company's own site
    notify("Crawling company site")
    site_candidates = crawl_company_site(company_url)
    notify("Extracting and classifying company-site pages")
    report_items = _process_candidates(site_candidates, company_name, start, end)

    # 2. Third-party search, per category
    notify("Searching for third-party coverage")
    search_results = search_all_categories(company_name, start, end)
    notify("Extracting and classifying search results")
    for category_candidates in search_results.values():
        report_items.extend(_process_candidates(category_candidates, company_name, start, end))

    # 3. Dedupe across everything found so far
    notify("Deduplicating results")
    report_items = dedupe_items(report_items)

    # 4. Archive each surviving item (optional, off by default — see .env.example)
    if settings.ENABLE_ARCHIVING:
        notify("Archiving sources to the Wayback Machine")
        for item in report_items:
            item.archived_url = save_page_now(item.url)

    for item in report_items:
        report.add(item)

    logger.info(
        "Done: %d press releases, %d webinars, %d events, %d awards",
        len(report.press_releases), len(report.webinars),
        len(report.events), len(report.awards),
    )
    notify("Done")
    return report
