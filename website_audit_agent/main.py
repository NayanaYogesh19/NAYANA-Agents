"""
main.py — Entry point for the Website Audit Strategy Agent.

Usage:
  python main.py --target https://example.com --competitor https://rival.com
"""

from __future__ import annotations

import argparse
import logging
import os

import sys
import argparse

sys.stdout.reconfigure(encoding="utf-8")
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from tqdm import tqdm

from agents.content import run_content_analysis
from agents.crawler import crawl_domain
from agents.onpage_seo import run_onpage_seo
from agents.performance import run_performance
from agents.scorer import score_domain
from agents.synthesizer import run_synthesis
from agents.technical_seo import run_technical_seo
from agents.ux_analyzer import run_ux_analysis
from config import Config
from report.pdf_generator import generate_pdf_report
# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.FileHandler("audit.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _validate_url(url: str) -> str:
    """Normalise and validate a URL; raise SystemExit if unreachable."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        resp = requests.head(
            url,
            headers=Config.DEFAULT_HEADERS,
            timeout=Config.CRAWL_TIMEOUT,
            allow_redirects=True,
        )
        logger.info("Validated %s — HTTP %d", url, resp.status_code)
        return url
    except Exception as exc:
        logger.error("Cannot reach %s: %s", url, exc)
        print(f"\n  Cannot reach {url}: {exc}")
        sys.exit(1)


def _domain_slug(url: str) -> str:
    """Return a filesystem-safe slug for a domain URL."""
    return (
        urlparse(url)
        .netloc.replace("www.", "")
        .replace(".", "_")
        .replace("-", "_")
    )


def _run_all_agents(domain: str, progress: tqdm) -> dict:
    """
    Run crawler + all analysis agents for one domain.

    Returns a bundle dict with keys: crawl, tech, onpage, content, ux, perf.
    """
    logger.info("=== Starting full audit pipeline for %s ===", domain)

    host = domain.replace("https://", "").replace("http://", "")[:30]
    # Step 1 — Crawl
    progress.set_description(f"  Crawl {host}")
    crawl = crawl_domain(domain)
    progress.update(1)

    # Steps 2-6 — Analysis agents (run in parallel where possible)
    results = {}

    def _run_tech():
        return ("tech", run_technical_seo(crawl))

    def _run_onpage():
        return ("onpage", run_onpage_seo(crawl))

    def _run_content():
        return ("content", run_content_analysis(crawl))

    def _run_ux():
        return ("ux", run_ux_analysis(domain))

    def _run_perf():
        return ("perf", run_performance(domain))

    tasks = [_run_tech, _run_onpage, _run_content, _run_ux, _run_perf]

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fn): fn.__name__ for fn in tasks}
        for future in as_completed(futures):
            key, value = future.result()
            results[key] = value
            progress.set_description(f"  {key.capitalize()} {host}")
            progress.update(1)

    return {
        "crawl": crawl,
        "tech": results["tech"],
        "onpage": results["onpage"],
        "content": results["content"],
        "ux": results["ux"],
        "perf": results["perf"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """Orchestrate the full dual-domain audit pipeline."""
    parser = argparse.ArgumentParser(
        description="Website Audit Strategy Agent — full SEO, performance, UX, and content audit."
    )
    parser.add_argument("--target", required=True, help="Target domain URL, e.g. https://example.com")
    parser.add_argument("--competitor", required=True, help="Competitor domain URL, e.g. https://rival.com")
    args = parser.parse_args()

    print("\n" + "=" * 62)
    print("     Website Audit Strategy Agent")
    print("=" * 62)

    # Validate URLs
    target_url = _validate_url(args.target)
    competitor_url = _validate_url(args.competitor)

    print(f"\n  Target:     {target_url}")
    print(f"  Competitor: {competitor_url}\n")

    start_time = time.time()

    # Run both domains in parallel — each gets its own tqdm bar
    target_bundle: dict = {}
    competitor_bundle: dict = {}

    print("  Running audit pipeline for both domains in parallel…\n")

    t_bar = tqdm(total=6, desc=f"  {target_url[:40]}", unit="step", ncols=72, position=0, leave=True)
    c_bar = tqdm(total=6, desc=f"  {competitor_url[:40]}", unit="step", ncols=72, position=1, leave=True)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_target = executor.submit(_run_all_agents, target_url, t_bar)
        future_competitor = executor.submit(_run_all_agents, competitor_url, c_bar)

        target_bundle = future_target.result()
        competitor_bundle = future_competitor.result()

    t_bar.close()
    c_bar.close()

    progress = tqdm(total=3, desc="  Post-processing", unit="step", ncols=72, leave=True)

    # Scoring
    progress.set_description("  Scoring domains")
    target_scores = score_domain(
        domain=target_url,
        perf=target_bundle["perf"],
        tech=target_bundle["tech"],
        onpage=target_bundle["onpage"],
        content=target_bundle["content"],
        ux=target_bundle["ux"],
    )
    competitor_scores = score_domain(
        domain=competitor_url,
        perf=competitor_bundle["perf"],
        tech=competitor_bundle["tech"],
        onpage=competitor_bundle["onpage"],
        content=competitor_bundle["content"],
        ux=competitor_bundle["ux"],
    )
    progress.update(1)

    # Attach scores to bundles for synthesiser
    target_bundle["scores"] = target_scores
    competitor_bundle["scores"] = competitor_scores

    # AI Synthesis
    progress.set_description("  Claude AI synthesis")
    synthesis = run_synthesis(target_bundle, competitor_bundle)
    progress.update(1)

    # Report generation
    progress.set_description(
    "  Generating PDF report"
    )
    audit_duration = time.time() - start_time
    report_path = generate_pdf_report(

       target_bundle=target_bundle,

       competitor_bundle=competitor_bundle,

       synthesis=synthesis,

       audit_duration=audit_duration

    )
    print(f"PDF generated successfully.")
    print(f"PDF location: {report_path}")

    progress.update(1)
    progress.close()

    # ── Final summary ──────────────────────────────────────────────────────────

    print("\n" + "=" * 62)
    print("          Website Audit Completed")
    print("=" * 62)

    print(
        f"Target Score:      {target_scores.overall}/100 ({target_scores.grade})"
    )

    print(
        f"Competitor Score: {competitor_scores.overall}/100 ({competitor_scores.grade})"
    )

    print(
        f"Report saved to:  {report_path}"
    )

    print(
        f"Audit duration:   {audit_duration:.1f} seconds"
    )

    print("=" * 62 + "\n")

    if synthesis.error:

        print(
            f"AI synthesis note: {synthesis.error}\n"
        )


if __name__ == "__main__":
    main()