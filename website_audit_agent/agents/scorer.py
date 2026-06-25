"""
scorer.py — Scoring engine that produces 0-100 category scores and an overall score.

FIX: _score_ux() now uses 50 as neutral base when PageSpeed accessibility_score
is 0 (meaning PageSpeed failed/was blocked), so UX score is always meaningful
and based on real HTML check results. Previously any PageSpeed failure caused
UX = 0 regardless of actual on-page quality.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

from agents.content import ContentResult
from agents.onpage_seo import OnPageSEOResult
from agents.performance import PerformanceResult
from agents.technical_seo import TechnicalSEOResult
from agents.ux_analyzer import UXResult
from config import Config

logger = logging.getLogger(__name__)


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class DomainScore:
    """Final scores for one domain across all categories."""
    domain: str
    overall: int = 0
    performance: int = 0
    technical_seo: int = 0
    onpage_seo: int = 0
    content: int = 0
    ux: int = 0
    grade: str = "D"


# ── Grade mapping ─────────────────────────────────────────────────────────────

def _grade(score: int) -> str:
    for threshold, letter in Config.GRADE_MAP:
        if score >= threshold:
            return letter
    return "D"


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> int:
    return int(max(lo, min(hi, value)))


# ── Category scorers ──────────────────────────────────────────────────────────

def _score_performance(perf: PerformanceResult) -> int:
    """
    Compute performance score from PageSpeed results.

    If both mobile and desktop are available, use their average.
    Otherwise fall back to whichever strategy fetched successfully.
    """
    mobile_score = (
        perf.mobile.performance_score
        if perf.mobile and perf.mobile.fetch_ok
        else None
    )
    desktop_score = (
        perf.desktop.performance_score
        if perf.desktop and perf.desktop.fetch_ok
        else None
    )

    if mobile_score is not None and desktop_score is not None:
        return _clamp((mobile_score + desktop_score) / 2.0)
    if mobile_score is not None:
        return _clamp(mobile_score)
    if desktop_score is not None:
        return _clamp(desktop_score)
    return 0


def _score_technical_seo(tech: TechnicalSEOResult) -> int:
    score = 100.0
    status_map: Dict[str, str] = {c.name: c.status for c in tech.checks}

    if status_map.get("HTTPS Enabled") == "fail":          score -= 20
    if status_map.get("robots.txt Present") == "fail":     score -= 10
    if status_map.get("Sitemap Present") == "fail":        score -= 10
    if status_map.get("Structured Data Present") == "fail": score -= 10
    if status_map.get("Unique Title Tags") == "fail":      score -= 5
    if status_map.get("Unique Meta Descriptions") == "fail": score -= 5

    broken_deduct = min(len(tech.broken_internal_links) * 5, 20)
    score -= broken_deduct
    return _clamp(score)


def _score_onpage_seo(onpage: OnPageSEOResult) -> int:
    score = 100.0
    pages = onpage.pages

    missing_titles = sum(1 for p in pages if p.title_issue == "missing")
    score -= min(missing_titles * 5, 20)

    missing_meta = sum(1 for p in pages if p.meta_desc_issue == "missing")
    score -= min(missing_meta * 3, 15)

    h1_issues = sum(1 for p in pages if p.h1_issue in ("missing", "multiple"))
    score -= min(h1_issues * 5, 15)

    total_missing_alt = sum(len(p.images_missing_alt) for p in pages)
    score -= min(total_missing_alt * 2, 15)

    score -= min(len(onpage.orphan_pages) * 5, 15)
    return _clamp(score)


def _score_content(content: ContentResult) -> int:
    score = 100.0
    pages = content.pages

    thin = sum(1 for p in pages if p.thin_content)
    score -= min(thin * 10, 30)

    dupe_pages = sum(1 for p in pages if p.action == "Merge")
    score -= min(dupe_pages * 10, 20)

    no_multimedia = sum(
        1 for p in pages
        if p.image_count == 0 and p.iframe_count == 0 and p.audio_count == 0
    )
    score -= min(no_multimedia * 5, 15)

    hard_read = sum(1 for p in pages if p.gunning_fog > 12)
    score -= min(hard_read * 5, 15)

    return _clamp(score)


def _score_ux(ux: UXResult, perf: PerformanceResult) -> int:
    """
    Compute UX score from PageSpeed accessibility + HTML check adjustments.

    FIX: When PageSpeed accessibility_score is 0 (meaning the API call failed,
    was blocked, or couldn't complete the Lighthouse audit — NOT that the site
    has zero accessibility), use 50 as a neutral starting base so that real
    HTML check results still produce a meaningful score.

    Score range:
      API succeeded → base 0-100 from PageSpeed + adjustments
      API failed    → base 50 (neutral) + adjustments → range ~10-50
    """
    acc_score = perf.mobile.accessibility_score if perf.mobile else 0

    if acc_score > 0:
        # PageSpeed returned real accessibility data — use it directly
        base = float(acc_score)
        logger.debug("UX base from PageSpeed accessibility: %d", acc_score)
    else:
        # PageSpeed failed or was blocked — use neutral 50 so HTML checks matter
        base = 50.0
        logger.info(
            "PageSpeed accessibility_score=0 (API blocked or failed) — "
            "using neutral base=50 for UX scoring so HTML check results count"
        )

    score = base

    # Adjustments from HTML-based checks (always run regardless of PageSpeed)
    if not ux.cta_above_fold:
        score -= 10
    if not ux.trust_signals_present:
        score -= 10

    check_map: Dict[str, str] = {c.name: c.status for c in ux.checks}

    if check_map.get("Mobile Tap Target Sizes") == "fail":
        score -= 10
    if check_map.get("ARIA Landmark Roles") == "fail":
        score -= 5
    if check_map.get("Form Labels") == "fail":
        score -= 5

    return _clamp(score)


# ── Public API ────────────────────────────────────────────────────────────────

def score_domain(
    domain: str,
    perf: PerformanceResult,
    tech: TechnicalSEOResult,
    onpage: OnPageSEOResult,
    content: ContentResult,
    ux: UXResult,
) -> DomainScore:
    """Compute category scores and weighted overall score for a domain."""
    logger.info("Scoring domain: %s", domain)

    ds = DomainScore(domain=domain)
    ds.performance    = _score_performance(perf)
    ds.technical_seo  = _score_technical_seo(tech)
    ds.onpage_seo     = _score_onpage_seo(onpage)
    ds.content        = _score_content(content)
    ds.ux             = _score_ux(ux, perf)

    w = Config.WEIGHTS
    ds.overall = _clamp(
        ds.performance  * w["performance"]
        + ds.technical_seo * w["technical_seo"]
        + ds.onpage_seo    * w["onpage_seo"]
        + ds.content       * w["content"]
        + ds.ux            * w["ux"]
    )
    ds.grade = _grade(ds.overall)

    logger.info(
        "Score for %s — overall: %d (%s), perf: %d, tech: %d, "
        "onpage: %d, content: %d, ux: %d",
        domain, ds.overall, ds.grade,
        ds.performance, ds.technical_seo,
        ds.onpage_seo, ds.content, ds.ux,
    )
    return ds