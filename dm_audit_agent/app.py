"""
app.py — FastAPI entry point for the DM Audit Agent.

Rearchitected pipeline (SE Ranking removed entirely — all SEO/PPC/SMM
metrics are entered manually by the user in the UI):

  1. User selects an audit mode ("seo" = 9 slides, "full" = 15 slides,
     within the requested 14-16 range) and optionally excludes specific
     toggleable sections (e.g. "Conversion Funnel").
  2. User manually enters SEO metrics (Health Score, Organic Traffic,
     Organic Keywords, Passed Checks, Crawled Pages, Errors, Warnings,
     Notices) and, in "full" mode, Performance Marketing (PPC) and Social
     Media (SMM) metrics — no external SEO API dependency.
  3. Keyword Research agent (Tavily + website parser) builds a grounded
     research brief about the company/competitors.
  4. SEO Audit agent (PageSpeed + Tavily + parser + manual metrics) writes a
     unique technical/content narrative.
  5. SMM Gap Analysis agent (Tavily + parser + manual SMM metrics) writes a
     unique social gap narrative.
  6. Strategy agent combines SEO + SMM + PPC input into a strategy narrative.
  7. Content agent produces per-section JSON text (only for the sections the
     user actually requested) plus benchmark/KPI table data — explicitly
     instructed to never be generic and never invent numbers.
  8. The PDF engine renders exactly the requested slides, in the fixed
     visual template matching the reference PDFs, and the file is served
     back for download (filename: "<Company Name> Audit Report.pdf").
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agents.content_agent import run_content_generation
from agents.keyword_research_agent import run_keyword_research
from agents.seo_audit_agent import run_seo_audit
from agents.smm_gap_analysis_agent import run_smm_gap_analysis
from agents.strategy_agent import run_strategy
from config import Config
from metrics_schema import PPC_FIELD_LABELS, SEO_FIELD_LABELS, SMM_FIELD_LABELS
from pdf_engine import build_pdf
from report_writer import create_run, pdf_filename, save_document
from slide_renderers import RENDERERS
from templates import MODES, get_sections, resolve_included_slugs, toggleable_sections

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("dm_audit_agent")

app = FastAPI(title="DM Audit Agent", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class DMAuditRequest(BaseModel):
    company_name: str = Field(..., alias="Company Name")
    domain: str = Field(..., alias="Domain/Website")
    industry: str = Field(..., alias="Industry")
    competitors_names: str = Field(..., alias="Competitors Names")
    your_email: str = Field(..., alias="Your Email")

    audit_mode: str = Field(..., alias="Audit Mode")  # "seo" | "full"
    excluded_sections: list[str] = Field(default_factory=list, alias="Excluded Sections")

    seo_metrics: dict[str, Optional[float]] = Field(default_factory=dict, alias="SEO Metrics")
    ppc_metrics: dict[str, Optional[float]] = Field(default_factory=dict, alias="PPC Metrics")
    smm_metrics: dict[str, Optional[float]] = Field(default_factory=dict, alias="SMM Metrics")

    class Config:
        populate_by_name = True


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/modes")
def get_modes() -> dict:
    """Describes the two selectable audit modes and their toggleable
    sections, and the manual metric fields to render in the form — used by
    the frontend to build the UI dynamically instead of hardcoding it."""
    modes_out = {}
    for key, meta in MODES.items():
        modes_out[key] = {
            "label": meta["label"],
            "slide_count": meta["slide_count"],
            "toggleable_sections": [
                {"slug": s.slug, "title": s.title} for s in toggleable_sections(key)
            ],
        }
    return {
        "modes": modes_out,
        "seo_fields": SEO_FIELD_LABELS,
        "ppc_fields": PPC_FIELD_LABELS,
        "smm_fields": SMM_FIELD_LABELS,
    }


@app.post("/api/dm-audit")
def run_dm_audit(payload: DMAuditRequest) -> dict:
    if payload.audit_mode not in MODES:
        raise HTTPException(status_code=400, detail=f"Invalid audit_mode: {payload.audit_mode!r}")

    company_name = payload.company_name
    domain = payload.domain
    industry = payload.industry
    competitors_names = payload.competitors_names

    included_slugs = resolve_included_slugs(payload.audit_mode, payload.excluded_sections)

    run_id, run_dir = create_run(company_name)
    logger.info("Starting DM Audit run %s for company=%s mode=%s", run_id, company_name, payload.audit_mode)

    try:
        # 1. Research brief
        logger.info("[%s] Running Keyword Research agent", run_id)
        research_brief = run_keyword_research(domain, industry)

        # 2. SEO Audit narrative (only if any SEO-dependent section requested)
        seo_audit_text = ""
        if any(s in included_slugs for s in ("current_state", "visibility_gap", "seo_technical_audit", "benchmarks_seo")):
            logger.info("[%s] Running SEO Audit agent", run_id)
            seo_audit_text = run_seo_audit(domain, industry, payload.seo_metrics, research_brief)
        save_document(run_dir, "seo_audit_report.txt", "SEO Audit Report", seo_audit_text or "Not generated for this run.")

        # 3. SMM Gap Analysis (only in full mode, if requested)
        smm_audit_text = ""
        if "smm_audit" in included_slugs or "benchmarks_smm" in included_slugs:
            logger.info("[%s] Running SMM Gap Analysis agent", run_id)
            smm_audit_text = run_smm_gap_analysis(
                target_name=company_name,
                industry_name=industry,
                competitor_names=competitors_names,
                smm_metrics=payload.smm_metrics,
            )
        save_document(run_dir, "social_media_audit_report.txt", "Social Media Audit Report", smm_audit_text or "Not generated for this run.")

        # 4. Strategy narrative (feeds growth/summary/strategic-recommendations sections)
        strategy_text = ""
        if any(s in included_slugs for s in ("growth_recommendations", "summary_next_steps", "strategic_recommendations", "kpis_targets")):
            logger.info("[%s] Running Strategy agent", run_id)
            ads_input_text = "\n".join(f"{k}: {v}" for k, v in payload.ppc_metrics.items() if v is not None) or "No performance marketing data provided."
            strategy_text = run_strategy(seo_audit_text or research_brief, smm_audit_text or "Not applicable in this mode.", ads_input_text)
        save_document(run_dir, "seo_strategy_report.txt", "SEO Strategy Report", strategy_text or "Not generated for this run.")

        # 5. Dynamic per-section content generation
        logger.info("[%s] Running Content Generation agent for sections: %s", run_id, included_slugs)
        content_sections_needed = [s for s in included_slugs if s not in ("title", "metrics", "contact")]
        content = run_content_generation(
            company_name=company_name,
            industry=industry,
            requested_sections=content_sections_needed,
            research_brief=research_brief,
            seo_audit_text=seo_audit_text,
            smm_audit_text=smm_audit_text,
            strategy_text=strategy_text,
            seo_metrics=payload.seo_metrics,
            ppc_metrics=payload.ppc_metrics,
            smm_metrics=payload.smm_metrics,
            competitor_names=competitors_names,
        )

        # 6. Render PDF
        logger.info("[%s] Rendering PDF for sections: %s", run_id, included_slugs)
        ctx = {
            "company_name": company_name,
            "industry": industry,
            "seo_metrics": payload.seo_metrics,
            "ppc_metrics": payload.ppc_metrics,
            "smm_metrics": payload.smm_metrics,
            "section_text": content.get("sections", {}),
            "benchmarks": content.get("benchmarks", {}),
            "kpi_targets": content.get("kpi_targets", {}),
            "positioning_line": content.get("positioning_line", industry),
            "report_title": (
                "Suggested Digital Marketing Improvement Plan"
                if payload.audit_mode == "seo"
                else "Integrated Audit & Growth Strategy Report"
            ),
        }

        slide_fns = []
        for slug in included_slugs:
            renderer = RENDERERS.get(slug)
            if renderer is None:
                continue
            slide_fns.append(lambda sc, r=renderer: r(sc, ctx))

        filename = pdf_filename(company_name)
        pdf_path = os.path.join(run_dir, filename)
        build_pdf(pdf_path, slide_fns)

        logger.info("[%s] DM Audit run complete", run_id)

        return {
            "run_id": run_id,
            "company_name": company_name,
            "domain": domain,
            "audit_mode": payload.audit_mode,
            "included_sections": included_slugs,
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
