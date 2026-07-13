"""
app.py — FastAPI entry point for the DM Audit Agent.

Rearchitected pipeline (SE Ranking removed entirely — all SEO/PPC/SMM
metrics are entered manually by the user in the UI):

  1. User selects one or more categories — SEO, Performance Marketing (PPC),
     Social Media (SMM), any combination — and optionally excludes specific
     toggleable slides (e.g. "Industry Best Practices").
     Slide structure matches the reference template exactly:
       - Title, Contact — always 1 slide each.
       - Key Metrics / Current Digital State / Visibility Gap — one slide
         PER selected category (so selecting all three gives 3 of each).
       - Industry Best Practices / Benchmark Analysis / Growth
         Recommendations / Summary & Next Steps — one combined slide each,
         content adapted to span all selected categories.
       - Strategic Takeaways becomes its own slide only when all three
         categories are selected (otherwise folded into the Benchmark slide).
     A single selected category always produces exactly 9 slides; all three
     categories together always produce exactly 16.
  2. User manually enters SEO and PPC metrics for each selected category —
     no external SEO API dependency. SMM metrics are NEVER entered manually:
     when SMM is selected, they are auto-fetched via Tavily (discovering the
     company's real Instagram/Facebook/LinkedIn/YouTube profile URLs) +
     Apify (scraping each discovered profile) — see agents/smm_metrics_agent.py.
  3. Keyword Research agent (Tavily + website parser) builds a grounded
     research brief about the company/competitors.
  4. SEO Audit agent (PageSpeed + Tavily + parser + manual metrics) writes a
     unique technical/content narrative — only run if SEO was selected.
  5. SMM Gap Analysis agent (Tavily + parser + auto-fetched SMM metrics)
     writes a unique social gap narrative — only run if SMM was selected.
  6. Strategy agent combines SEO + SMM + PPC input into a strategy narrative.
  7. Content agent produces per-category content for Current State/Visibility
     Gap, plus combined adaptive content for the shared slides — explicitly
     instructed to never be generic and never invent numbers.
  8. The PDF engine renders exactly the resolved slides, in the fixed visual
     template matching the reference PDF, and the file is served back for
     download (filename: "<Company Name> Audit Report.pdf").
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, field_validator

from agents.content_agent import run_content_generation
from agents.keyword_research_agent import run_keyword_research
from agents.seo_audit_agent import run_seo_audit
from agents.smm_gap_analysis_agent import run_smm_gap_analysis
from agents.smm_metrics_agent import run_smm_metrics
from agents.strategy_agent import run_strategy
from config import Config
from metrics_schema import PPC_FIELD_LABELS, SEO_FIELD_LABELS, SMM_FIELD_LABELS
from pdf_engine import build_pdf
from report_writer import create_run, pdf_filename, save_document
from slide_renderers import RENDERERS
from templates import (
    CATEGORY_LABELS,
    VALID_CATEGORIES,
    resolve_included_slides,
    toggleable_groups,
    validate_categories,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("dm_audit_agent")

app = FastAPI(title="DM Audit Agent", version="4.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


def _looks_like_url(value: str) -> bool:
    value = value.strip()
    if not _URL_RE.match(value):
        value = f"https://{value}"
    return bool(_URL_RE.match(value)) and "." in value.split("://", 1)[-1].split("/")[0]


class DMAuditRequest(BaseModel):
    company_name: str = Field(..., alias="Company Name", min_length=1)
    domain: str = Field(..., alias="Domain/Website", min_length=1)
    industry: str = Field(..., alias="Industry", min_length=1)
    competitors_names: str = Field(..., alias="Competitors Names", min_length=1)
    your_email: EmailStr = Field(..., alias="Your Email")

    categories: list[str] = Field(..., alias="Categories", min_length=1)  # any of: seo, ppc, smm
    excluded_sections: list[str] = Field(default_factory=list, alias="Excluded Sections")

    seo_metrics: dict[str, Optional[float]] = Field(default_factory=dict, alias="SEO Metrics")
    ppc_metrics: dict[str, Optional[float]] = Field(default_factory=dict, alias="PPC Metrics")
    # No "SMM Metrics" field — SMM metrics are always auto-fetched (Tavily +
    # Apify) when the "smm" category is selected, never entered by the user.

    class Config:
        populate_by_name = True

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if not _looks_like_url(value):
            raise ValueError('Domain / Website must be a valid URL (e.g. "https://example.com").')
        return value

    @field_validator("competitors_names")
    @classmethod
    def _validate_competitor_urls(cls, value: str) -> str:
        urls = [u.strip() for u in value.split(",") if u.strip()]
        if not urls:
            raise ValueError("At least one competitor company URL is required.")
        for url in urls:
            if not _looks_like_url(url):
                raise ValueError(f'"{url}" is not a valid URL. Provide comma-separated competitor URLs (e.g. "https://competitor1.com, https://competitor2.com").')
        return value


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/categories")
def get_categories() -> dict:
    """Describes the three selectable categories (SEO / PPC / SMM), the
    toggleable slides, and the manual metric field labels per category —
    used by the frontend to build the UI dynamically."""
    return {
        "categories": [
            {"slug": c, "label": CATEGORY_LABELS[c]} for c in ("seo", "ppc", "smm")
        ],
        "toggleable_slides": [
            {"slug": g.slug, "title": g.title} for g in toggleable_groups()
        ],
        "seo_fields": SEO_FIELD_LABELS,
        "ppc_fields": PPC_FIELD_LABELS,
        "smm_fields": SMM_FIELD_LABELS,
    }


@app.post("/api/dm-audit")
def run_dm_audit(payload: DMAuditRequest) -> dict:
    try:
        categories = validate_categories(payload.categories)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    company_name = payload.company_name
    domain = payload.domain
    industry = payload.industry
    competitors_names = payload.competitors_names

    slides = resolve_included_slides(categories, payload.excluded_sections)

    run_id, run_dir = create_run(company_name)
    logger.info("Starting DM Audit run %s for company=%s categories=%s", run_id, company_name, categories)
    logger.info(
        "[%s] Requested exclusions from client: %s | Resolved slide count: %d | Slides: %s",
        run_id, payload.excluded_sections, len(slides),
        [f"{s['slug']}.{s['category']}" if s['category'] else s['slug'] for s in slides],
    )

    try:
        # 1. Research brief
        logger.info("[%s] Running Keyword Research agent", run_id)
        research_brief = run_keyword_research(domain, industry)

        # 2. SEO Audit narrative (only if SEO category selected)
        seo_audit_text = ""
        if "seo" in categories:
            logger.info("[%s] Running SEO Audit agent", run_id)
            seo_audit_text = run_seo_audit(domain, industry, payload.seo_metrics, research_brief)
        save_document(run_dir, "seo_audit_report.txt", "SEO Audit Report", seo_audit_text or "Not generated for this run.")

        # 3. Auto-fetch SMM metrics + SMM Gap Analysis (only if SMM category selected)
        smm_metrics_result: dict = {}
        smm_metrics_summary: dict = {}
        smm_audit_text = ""
        if "smm" in categories:
            logger.info("[%s] Auto-fetching SMM metrics (Tavily profile discovery + Apify scraping)", run_id)
            smm_metrics_result = run_smm_metrics(company_name, domain)
            smm_metrics_summary = smm_metrics_result.get("summary", {})
            logger.info("[%s] Running SMM Gap Analysis agent", run_id)
            smm_audit_text = run_smm_gap_analysis(
                target_name=company_name,
                industry_name=industry,
                competitor_names=competitors_names,
                smm_metrics=smm_metrics_summary,
            )
        save_document(run_dir, "social_media_audit_report.txt", "Social Media Audit Report", smm_audit_text or "Not generated for this run.")

        # 4. Strategy narrative (feeds growth/summary sections)
        logger.info("[%s] Running Strategy agent", run_id)
        ads_input_text = "\n".join(f"{k}: {v}" for k, v in payload.ppc_metrics.items() if v is not None) or "No performance marketing data provided."
        strategy_text = run_strategy(seo_audit_text or research_brief, smm_audit_text or "Not applicable — SMM not selected.", ads_input_text)
        save_document(run_dir, "seo_strategy_report.txt", "SEO Strategy Report", strategy_text or "Not generated for this run.")

        # 5. Dynamic content generation (per-category + combined)
        logger.info("[%s] Running Content Generation agent for categories: %s", run_id, categories)
        content = run_content_generation(
            company_name=company_name,
            industry=industry,
            categories=categories,
            research_brief=research_brief,
            seo_audit_text=seo_audit_text,
            smm_audit_text=smm_audit_text,
            strategy_text=strategy_text,
            seo_metrics=payload.seo_metrics,
            ppc_metrics=payload.ppc_metrics,
            smm_metrics=smm_metrics_summary,
            competitor_names=competitors_names,
        )

        # 6. Render PDF
        logger.info("[%s] Rendering PDF for %d slides", run_id, len(slides))
        has_strategic_takeaways_slide = any(s["slug"] == "strategic_takeaways" for s in slides)
        base_ctx = {
            "company_name": company_name,
            "industry": industry,
            "categories": categories,
            "competitor_names": competitors_names,
            "metrics_by_category": {
                "seo": payload.seo_metrics,
                "ppc": payload.ppc_metrics,
                "smm": smm_metrics_summary,
            },
            "content": content,
            "positioning_line": content.get("positioning_line") or industry,
            "has_strategic_takeaways_slide": has_strategic_takeaways_slide,
            "report_title": (
                "Suggested Digital Marketing Improvement Plan"
                if len(categories) == 1
                else "Integrated Audit & Growth Strategy Report"
            ),
        }

        slide_fns = []
        for slide in slides:
            renderer = RENDERERS.get(slide["render_key"])
            if renderer is None:
                continue
            slide_ctx = dict(base_ctx, category=slide["category"])
            slide_fns.append(lambda sc, r=renderer, c=slide_ctx: r(sc, c))

        filename = pdf_filename(company_name)
        pdf_path = os.path.join(run_dir, filename)
        build_pdf(pdf_path, slide_fns)

        logger.info("[%s] DM Audit run complete", run_id)

        return {
            "run_id": run_id,
            "company_name": company_name,
            "domain": domain,
            "categories": categories,
            "slide_count": len(slides),
            "included_slides": [f"{s['slug']}.{s['category']}" if s['category'] else s['slug'] for s in slides],
            "pdf_filename": filename,
            "download_url": f"/api/reports/{run_id}/{filename}",
        }
    except Exception as exc:
        logger.exception("[%s] DM Audit run failed", run_id)
        raise HTTPException(status_code=500, detail=f"Audit generation failed: {exc}") from exc


@app.get("/api/reports/{run_id}/{filename}")
def download_report(run_id: str, filename: str):
    path = os.path.join(Config.REPORTS_DIR, run_id, filename)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Report not found")
    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "text/plain"
    return FileResponse(path, media_type=media_type, filename=filename)


FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host=Config.APP_HOST, port=Config.APP_PORT, reload=True)
