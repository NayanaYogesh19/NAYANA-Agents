"""
generator.py — Builds the self-contained HTML audit report using Jinja2.

All data is embedded inline (base64 images, inline CSS) so the report
opens correctly in any modern browser without external dependencies.
"""

from __future__ import annotations


import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from xhtml2pdf import pisa

from jinja2 import Environment, FileSystemLoader

from agents.content import ContentResult
from agents.crawler import CrawlResult
from agents.onpage_seo import OnPageSEOResult
from agents.performance import PerformanceResult
from agents.scorer import DomainScore
from agents.synthesizer import SynthesisResult
from agents.technical_seo import TechnicalSEOResult
from agents.ux_analyzer import UXResult
from config import Config

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _cwv_color(metric: str, value: float) -> str:
    """Return 'good', 'needs-improvement', or 'poor' for a Core Web Vital value."""
    thresholds = Config.CWV_THRESHOLDS.get(metric, {})
    good = thresholds.get("good", 0)
    needs = thresholds.get("needs_improvement", 0)
    if value <= good:
        return "good"
    if value <= needs:
        return "needs-improvement"
    return "poor"


def _score_color(score: int) -> str:
    """Return CSS class name based on score band."""
    if score >= 80:
        return "good"
    if score >= 60:
        return "warning"
    return "critical"


def _format_ms(value: float) -> str:
    """Format a millisecond value for display."""
    if value >= 1000:
        return f"{value / 1000:.1f}s"
    return f"{int(value)}ms"


def _build_context(
    target_crawl: CrawlResult,
    competitor_crawl: CrawlResult,
    target_tech: TechnicalSEOResult,
    competitor_tech: TechnicalSEOResult,
    target_onpage: OnPageSEOResult,
    competitor_onpage: OnPageSEOResult,
    target_content: ContentResult,
    competitor_content: ContentResult,
    target_ux: UXResult,
    competitor_ux: UXResult,
    target_perf: PerformanceResult,
    competitor_perf: PerformanceResult,
    target_scores: DomainScore,
    competitor_scores: DomainScore,
    synthesis: SynthesisResult,
    audit_duration_s: float,
) -> Dict[str, Any]:
    """Assemble the full Jinja2 template context dictionary."""

    def _perf_dict(perf: PerformanceResult, strategy: str = "mobile") -> Dict:
        src = perf.mobile if strategy == "mobile" else perf.desktop
        if not src:
            return {}
        return {
            "performance_score": src.performance_score,
            "accessibility_score": src.accessibility_score,
            "best_practices_score": src.best_practices_score,
            "seo_score": src.seo_score,
            "lcp_ms": src.lcp_ms,
            "inp_ms": src.inp_ms,
            "cls": src.cls,
            "fcp_ms": src.fcp_ms,
            "ttfb_ms": src.ttfb_ms,
            "speed_index": src.speed_index,
            "total_blocking_time_ms": src.total_blocking_time_ms,
            "opportunities": src.opportunities[:3],
            "diagnostics": src.diagnostics[:5],
        }

    categories = ["performance", "technical_seo", "onpage_seo", "content", "ux"]

    score_comparison = []
    for cat in categories:
        t_val = getattr(target_scores, cat)
        c_val = getattr(competitor_scores, cat)
        score_comparison.append({
            "category": cat.replace("_", " ").title(),
            "key": cat,
            "target": t_val,
            "competitor": c_val,
            "target_color": _score_color(t_val),
            "competitor_color": _score_color(c_val),
            "winner": "target" if t_val >= c_val else "competitor",
        })

    # Content action map counts
    t_actions = target_content.action_counts
    c_actions = competitor_content.action_counts

    return {
        "report_date": datetime.now().strftime("%B %d, %Y at %H:%M"),
        "audit_duration_s": round(audit_duration_s, 1),

        # Domains
        "target_domain": target_crawl.domain,
        "competitor_domain": competitor_crawl.domain,

        # Scores
        "target_scores": target_scores,
        "competitor_scores": competitor_scores,
        "score_comparison": score_comparison,
        "target_overall_color": _score_color(target_scores.overall),
        "competitor_overall_color": _score_color(competitor_scores.overall),

        # Performance
        "target_perf_mobile": _perf_dict(target_perf, "mobile"),
        "competitor_perf_mobile": _perf_dict(competitor_perf, "mobile"),
        "target_perf_desktop": _perf_dict(target_perf, "desktop"),
        "competitor_perf_desktop": _perf_dict(competitor_perf, "desktop"),
        "cwv_color": _cwv_color,
        "format_ms": _format_ms,
        "score_color": _score_color,

        # Technical SEO — pre-build check maps so Jinja2 doesn't need dict mutation
        "target_tech": target_tech,
        "competitor_tech": competitor_tech,
        "target_tech_checks": target_tech.checks,
        "competitor_tech_checks": competitor_tech.checks,
        "target_tech_check_map": {c.name: c for c in target_tech.checks},
        "competitor_tech_check_map": {c.name: c for c in competitor_tech.checks},
        "all_tech_check_names": list(
            dict.fromkeys(
                [c.name for c in target_tech.checks]
                + [c.name for c in competitor_tech.checks]
            )
        ),

        # On-page SEO
        "target_onpage": target_onpage,
        "competitor_onpage": competitor_onpage,
        "target_top_issue_pages": [
            p for p in target_onpage.pages
            if p.url in target_onpage.top_issues_pages
        ][:5],

        # Content
        "target_content": target_content,
        "competitor_content": competitor_content,
        "target_action_counts": t_actions,
        "competitor_action_counts": c_actions,

        # UX
        "target_ux": target_ux,
        "competitor_ux": competitor_ux,

        # Crawl
        "target_crawl": target_crawl,
        "competitor_crawl": competitor_crawl,
        "target_pages": target_crawl.pages[:100],
        "competitor_pages": competitor_crawl.pages[:100],

        # Synthesis
        "synthesis": synthesis,

        # Helpers
        "zip": zip,
        "len": len,
        "enumerate": enumerate,
    }


def generate_report(
    target_crawl: CrawlResult,
    competitor_crawl: CrawlResult,
    target_tech: TechnicalSEOResult,
    competitor_tech: TechnicalSEOResult,
    target_onpage: OnPageSEOResult,
    competitor_onpage: OnPageSEOResult,
    target_content: ContentResult,
    competitor_content: ContentResult,
    target_ux: UXResult,
    competitor_ux: UXResult,
    target_perf: PerformanceResult,
    competitor_perf: PerformanceResult,
    target_scores: DomainScore,
    competitor_scores: DomainScore,
    synthesis: SynthesisResult,
    audit_duration_s: float = 0.0,
) -> str:
    """
    Render the Jinja2 HTML template with all audit data.

    Returns the path to the generated HTML report file.
    """
    logger.info("Generating HTML report")

    context = _build_context(
        target_crawl=target_crawl,
        competitor_crawl=competitor_crawl,
        target_tech=target_tech,
        competitor_tech=competitor_tech,
        target_onpage=target_onpage,
        competitor_onpage=competitor_onpage,
        target_content=target_content,
        competitor_content=competitor_content,
        target_ux=target_ux,
        competitor_ux=competitor_ux,
        target_perf=target_perf,
        competitor_perf=competitor_perf,
        target_scores=target_scores,
        competitor_scores=competitor_scores,
        synthesis=synthesis,
        audit_duration_s=audit_duration_s,
    )

    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    env.globals.update({"zip": zip, "len": len, "enumerate": enumerate})
    template = env.get_template("report.html")
    html_content = template.render(**context)

    # Determine output path
    os.makedirs(Config.REPORT_OUTPUT_DIR, exist_ok=True)
    t_host = target_crawl.domain.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "_")
    c_host = competitor_crawl.domain.replace("https://", "").replace("http://", "").replace("/", "").replace(".", "_")
    filename = f"{t_host}_vs_{c_host}_audit.html"
    output_path = os.path.join(Config.REPORT_OUTPUT_DIR, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    logger.info(
        "HTML report saved to: %s",
        output_path
    )

    pdf_path = output_path.replace(
    ".html",
    ".pdf"
    )

    try:

        with open(
            output_path,
            "r",
            encoding="utf-8"
        ) as html_file:

            html_content = html_file.read()

        with open(
            pdf_path,
            "wb"
        ) as pdf_file:

            pisa.CreatePDF(
                html_content,
                dest=pdf_file
            )

        logger.info(
            "PDF report saved to: %s",
            pdf_path
        )

        return pdf_path

    except Exception as e:

        logger.error(
            "PDF generation failed: %s",
            str(e)
        )

    return output_path