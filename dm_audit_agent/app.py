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
import uuid
from datetime import datetime, timedelta
from typing import Optional

import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field, field_validator

from agents.content_agent import run_content_generation
from agents.keyword_research_agent import run_keyword_research
from agents.ppc_metrics_agent import run_ppc_metrics
from agents.seo_audit_agent import run_seo_audit
from agents.smm_gap_analysis_agent import run_smm_gap_analysis
from agents.smm_metrics_agent import run_smm_metrics
from agents.strategy_agent import run_strategy
from config import Config
from metrics_schema import PPC_FIELD_LABELS, PpcMetrics, SEO_FIELD_LABELS, SeoMetrics, SMM_FIELD_LABELS
from pdf_engine import build_pdf
from report_writer import create_run, pdf_filename, save_document
from slide_renderers import RENDERERS
from templates import (
    CATEGORY_LABELS,
    CATEGORY_ORDER,
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


def _normalize_url(value: str) -> str:
    """Prepends "https://" if the user typed a bare domain (e.g.
    "acmerobotics.com" instead of "https://acmerobotics.com") so every
    downstream consumer (website parser, PDF headers, benchmark subtitle)
    always sees a proper, consistent URL regardless of what was typed."""
    value = value.strip()
    if not _URL_RE.match(value):
        value = f"https://{value}"
    return value


def _looks_like_url(value: str) -> bool:
    normalized = _normalize_url(value)
    return bool(_URL_RE.match(normalized)) and "." in normalized.split("://", 1)[-1].split("/")[0]


class _CompanyUrlValidatorMixin(BaseModel):
    """Shared domain/competitor-URL validators, used by both the legacy
    single-shot request model and the new phased-flow "start" request model
    so the exact same normalization logic (bare domains -> https://, etc.)
    applies identically in both flows."""

    domain: str
    competitors_names: str

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, value: str) -> str:
        if not _looks_like_url(value):
            raise ValueError('Domain / Website must be a valid URL (e.g. "example.com" or "https://example.com").')
        return _normalize_url(value)

    @field_validator("competitors_names")
    @classmethod
    def _validate_competitor_urls(cls, value: str) -> str:
        urls = [u.strip() for u in value.split(",") if u.strip()]
        if not urls:
            raise ValueError("At least one competitor company URL is required.")
        for url in urls:
            if not _looks_like_url(url):
                raise ValueError(f'"{url}" is not a valid URL. Provide comma-separated competitor URLs (e.g. "competitor1.com, competitor2.com").')
        return ", ".join(_normalize_url(url) for url in urls)


class DMAuditRequest(_CompanyUrlValidatorMixin):
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


# ---------------------------------------------------------------------------
# Phased per-category review flow — new endpoints below reuse every existing
# agent/PDF/template function UNCHANGED, only moving WHEN each is called
# across multiple HTTP requests instead of one. The legacy /api/dm-audit
# endpoint above is untouched and stays fully functional side-by-side.
# ---------------------------------------------------------------------------

RUN_STATE_TTL = timedelta(hours=6)
RUN_STATE: dict[str, dict] = {}


def _cleanup_stale_runs() -> None:
    """Drops any in-memory run older than RUN_STATE_TTL, checked whenever a
    new run starts, so abandoned runs (tab closed mid-flow) don't grow
    memory unbounded. No durability requirement across process restarts —
    a full audit run completes in minutes, well within the TTL."""
    cutoff = datetime.utcnow() - RUN_STATE_TTL
    stale_ids = [rid for rid, state in RUN_STATE.items() if state["created_at"] < cutoff]
    for rid in stale_ids:
        del RUN_STATE[rid]


def _get_state(run_id: str) -> dict:
    state = RUN_STATE.get(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f'No active audit run found for run_id "{run_id}".')
    return state


class DMAuditStartRequest(_CompanyUrlValidatorMixin):
    company_name: str = Field(..., alias="Company Name", min_length=1)
    domain: str = Field(..., alias="Domain/Website", min_length=1)
    industry: str = Field(..., alias="Industry", min_length=1)
    competitors_names: str = Field(..., alias="Competitors Names", min_length=1)
    your_email: EmailStr = Field(..., alias="Your Email")
    categories: list[str] = Field(..., alias="Categories", min_length=1)

    class Config:
        populate_by_name = True


class CategoryReviewRequest(BaseModel):
    seo_metrics: Optional[dict[str, Optional[float]]] = Field(None, alias="SEO Metrics")
    # PPC has no manual numeric metrics anymore — only these 3 ad-transparency
    # library inputs, which drive both the fetched ad-data summary AND (via
    # the content-generation prompt) an LLM-estimated PPC performance
    # snapshot used by the Competitive Benchmark Analysis table.
    google_ads_url: Optional[str] = Field(None, alias="Google Ads URL")
    meta_ads_url: Optional[str] = Field(None, alias="Meta Ads URL")
    linkedin_company_name: Optional[str] = Field(None, alias="LinkedIn Company Name")
    # SMM direct profile URLs — replaces Tavily-based auto-discovery for the
    # phased review flow (the legacy single-shot endpoint is unaffected and
    # still auto-discovers).
    instagram_url: Optional[str] = Field(None, alias="Instagram URL")
    facebook_url: Optional[str] = Field(None, alias="Facebook URL")
    linkedin_url: Optional[str] = Field(None, alias="LinkedIn URL")
    youtube_url: Optional[str] = Field(None, alias="YouTube URL")

    class Config:
        populate_by_name = True


class FinalizeRequest(BaseModel):
    excluded_sections: list[str] = Field(default_factory=list, alias="Excluded Sections")

    class Config:
        populate_by_name = True


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


@app.post("/api/dm-audit/start")
def start_dm_audit(payload: DMAuditStartRequest) -> dict:
    """Phase 1 of the phased per-category review flow. Validates categories,
    creates a run (same create_run() used by the legacy endpoint), runs the
    category-independent Keyword Research agent exactly once (identical call
    to the legacy endpoint's step 1), and stores everything needed for the
    upcoming per-category review calls in memory, keyed by run_id."""
    _cleanup_stale_runs()

    try:
        categories = validate_categories(payload.categories)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    run_id, run_dir = create_run(payload.company_name)
    logger.info("[%s] Starting phased DM Audit run for company=%s categories=%s", run_id, payload.company_name, categories)

    logger.info("[%s] Running Keyword Research agent", run_id)
    research_brief = run_keyword_research(payload.domain, payload.industry)

    pending_categories = [c for c in CATEGORY_ORDER if c in categories]

    RUN_STATE[run_id] = {
        "run_id": run_id,
        "run_dir": run_dir,
        "created_at": datetime.utcnow(),
        "company_name": payload.company_name,
        "domain": payload.domain,
        "industry": payload.industry,
        "competitors_names": payload.competitors_names,
        "your_email": payload.your_email,
        "categories": categories,
        "pending_categories": pending_categories,
        "current_category": pending_categories[0] if pending_categories else None,
        "research_brief": research_brief,
        "seo_metrics": {},
        "ppc_metrics": {},
        "ppc_ad_summary": {},
        "ppc_ad_summary_text_override": None,
        "smm_metrics_summary": {},
        "seo_audit_text": "",
        "smm_audit_text": "",
        "reviewed_categories": [],
        "status": "in_progress",
    }

    return {
        "run_id": run_id,
        "company_name": payload.company_name,
        "categories": categories,
        "current_category": pending_categories[0] if pending_categories else None,
    }


@app.post("/api/dm-audit/{run_id}/category/{category}")
def review_category(run_id: str, category: str, payload: CategoryReviewRequest) -> dict:
    """Phase 2 (called once per selected category, in fixed SEO -> PPC -> SMM
    order — enforced server-side below, not just by frontend convention).
    Runs ONLY that category's existing, unmodified narrative agent(s) —
    identical calls to the legacy endpoint's steps 2-3, just relocated to
    their own request — and returns the raw narrative text (or, for PPC,
    which has no dedicated narrative agent, an echo of the entered metrics)
    for on-screen review. Never advances run state on failure, so the exact
    same request can be safely retried."""
    state = _get_state(run_id)

    if state["status"] != "in_progress":
        raise HTTPException(status_code=409, detail=f'Audit run "{run_id}" is not awaiting category review (status: {state["status"]}).')
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f'Unknown category "{category}". Expected one of {sorted(VALID_CATEGORIES)}.')
    if category != state["current_category"]:
        raise HTTPException(
            status_code=409,
            detail=f'Category "{category}" is not next in review order for this run (expected "{state["current_category"]}").',
        )

    try:
        if category == "seo":
            if payload.seo_metrics is None:
                raise HTTPException(status_code=400, detail="SEO Metrics are required to review the SEO category.")
            seo_metrics = SeoMetrics(**payload.seo_metrics).model_dump()
            logger.info("[%s] Running SEO Audit agent", run_id)
            seo_audit_text = run_seo_audit(state["domain"], state["industry"], seo_metrics, state["research_brief"])
            save_document(state["run_dir"], "seo_audit_report.txt", "SEO Audit Report", seo_audit_text or "Not generated for this run.")
            state["seo_metrics"] = seo_metrics
            state["seo_audit_text"] = seo_audit_text
            response_body = {"category": "seo", "narrative": seo_audit_text}

        elif category == "ppc":
            if not (payload.google_ads_url and payload.meta_ads_url and payload.linkedin_company_name):
                raise HTTPException(
                    status_code=400,
                    detail="Google Ads URL, Meta Ads URL, and LinkedIn Company Name are all required to review the Performance Marketing category.",
                )

            logger.info("[%s] Fetching PPC ad data (Google/Meta/LinkedIn ad libraries)", run_id)
            ppc_ad_data = run_ppc_metrics(
                google_ads_url=payload.google_ads_url,
                meta_ads_url=payload.meta_ads_url,
                linkedin_company_name=payload.linkedin_company_name,
            )
            ppc_ad_summary = ppc_ad_data.get("summary", {})
            state["ppc_ad_summary"] = ppc_ad_summary

            response_body = {
                "category": "ppc",
                "ad_data": ppc_ad_summary,
            }

        else:  # smm
            if not (payload.instagram_url and payload.facebook_url and payload.linkedin_url and payload.youtube_url):
                raise HTTPException(
                    status_code=400,
                    detail="Instagram, Facebook, LinkedIn, and YouTube profile URLs are all required to review the Social Media category.",
                )
            profile_urls = {
                "instagram": payload.instagram_url,
                "facebook": payload.facebook_url,
                "linkedin": payload.linkedin_url,
                "youtube": payload.youtube_url,
            }
            logger.info("[%s] Scraping SMM profiles from user-provided URLs", run_id)
            smm_metrics_result = run_smm_metrics(state["company_name"], state["domain"], profile_urls=profile_urls)
            smm_metrics_summary = smm_metrics_result.get("summary", {})
            logger.info("[%s] Running SMM Gap Analysis agent", run_id)
            smm_audit_text = run_smm_gap_analysis(
                target_name=state["company_name"],
                industry_name=state["industry"],
                competitor_names=state["competitors_names"],
                smm_metrics=smm_metrics_summary,
            )
            save_document(state["run_dir"], "social_media_audit_report.txt", "Social Media Audit Report", smm_audit_text or "Not generated for this run.")
            state["smm_metrics_summary"] = smm_metrics_summary
            state["smm_audit_text"] = smm_audit_text
            response_body = {"category": "smm", "narrative": smm_audit_text, "metrics_summary": smm_metrics_summary}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("[%s] Category review failed for %s", run_id, category)
        raise HTTPException(status_code=500, detail=f"Analysis failed for {CATEGORY_LABELS.get(category, category)}: {exc}") from exc

    # Only advance state once the category's work has succeeded, so a failed
    # call never skips or corrupts the review order — the client can retry
    # the identical request.
    state["reviewed_categories"].append(category)
    state["pending_categories"] = [c for c in state["pending_categories"] if c != category]
    state["current_category"] = state["pending_categories"][0] if state["pending_categories"] else None
    if state["current_category"] is None:
        state["status"] = "awaiting_finalize"

    response_body.update({
        "run_id": run_id,
        "remaining_categories": state["pending_categories"],
        "next_category": state["current_category"],
        "is_last": state["current_category"] is None,
    })
    return response_body


class NarrativeEditRequest(BaseModel):
    narrative: str = Field(..., alias="Narrative")

    class Config:
        populate_by_name = True


_NARRATIVE_STATE_KEY = {"seo": "seo_audit_text", "smm": "smm_audit_text"}


@app.post("/api/dm-audit/{run_id}/category/{category}/narrative")
def edit_category_narrative(run_id: str, category: str, payload: NarrativeEditRequest) -> dict:
    """Lets the user overwrite the review text for a category they've
    ALREADY reviewed (before clicking Proceed), so their edits are what
    actually flows into the final report at finalize time. SEO/SMM store the
    edit as a direct override of their AI narrative text. PPC has no
    narrative (its review is a formatted ad-data summary) — editing it
    stores a text override that REPLACES the ad-data summary passed to the
    Content Generation prompt, rather than overwriting the underlying
    structured scrape data itself."""
    state = _get_state(run_id)
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f'Unknown category "{category}".')
    if category not in state["reviewed_categories"]:
        raise HTTPException(status_code=409, detail=f'Category "{category}" has not been reviewed yet in this run.')

    if category == "ppc":
        state["ppc_ad_summary_text_override"] = payload.narrative
    else:
        state[_NARRATIVE_STATE_KEY[category]] = payload.narrative
    return {"run_id": run_id, "category": category, "narrative": payload.narrative}


@app.get("/api/dm-audit/{run_id}/finalize-options")
def finalize_options(run_id: str) -> dict:
    """Returns the same toggleable-slide shape as /api/categories, scoped to
    this run, so the finalize step can present "Sections to include"
    checkboxes (reusing the existing, unmodified toggleable_groups())."""
    _get_state(run_id)  # 404s if unknown/expired
    return {
        "toggleable_slides": [
            {"slug": g.slug, "title": g.title} for g in toggleable_groups()
        ],
    }


@app.post("/api/dm-audit/{run_id}/finalize")
def finalize_dm_audit(run_id: str, payload: FinalizeRequest) -> dict:
    """Phase 3 — runs after every selected category has been reviewed.
    Executes the SAME strategy -> content-generation -> PDF-build sequence as
    the legacy endpoint's steps 4-6, unchanged, reading accumulated state
    instead of one request payload. Content generation and PDF building
    remain single, unconditional, cross-category calls (they cannot be
    correctness-preserving if split per category — see benchmarks/summary
    slides, which synthesize across ALL selected categories at once)."""
    state = _get_state(run_id)
    if state["status"] != "awaiting_finalize":
        raise HTTPException(
            status_code=409,
            detail=f'Audit run "{run_id}" is not ready to finalize (status: {state["status"]}, still pending: {state["pending_categories"]}).',
        )

    run_id_log = run_id
    run_dir = state["run_dir"]
    categories = state["categories"]
    company_name = state["company_name"]
    industry = state["industry"]
    competitors_names = state["competitors_names"]
    seo_metrics = state["seo_metrics"]
    ppc_metrics = state["ppc_metrics"]
    ppc_ad_summary = state["ppc_ad_summary"]
    ppc_ad_summary_override = state["ppc_ad_summary_text_override"]
    smm_metrics_summary = state["smm_metrics_summary"]
    seo_audit_text = state["seo_audit_text"]
    smm_audit_text = state["smm_audit_text"]
    research_brief = state["research_brief"]

    # If the user edited the PPC ad-data summary on the review screen, that
    # edited text REPLACES the structured summary for content generation —
    # otherwise pass the real scraped dict through unchanged.
    ppc_ad_data_for_content = ppc_ad_summary_override if ppc_ad_summary_override is not None else ppc_ad_summary

    slides = resolve_included_slides(categories, payload.excluded_sections)
    logger.info(
        "[%s] Finalizing | Requested exclusions: %s | Resolved slide count: %d | Slides: %s",
        run_id_log, payload.excluded_sections, len(slides),
        [f"{s['slug']}.{s['category']}" if s['category'] else s['slug'] for s in slides],
    )

    try:
        # Strategy narrative (feeds growth/summary sections) — same call as
        # the legacy endpoint's step 4, but ads_input_text is now built from
        # the fetched ad-library summary (no more manual numeric metrics).
        logger.info("[%s] Running Strategy agent", run_id_log)
        if ppc_ad_summary_override is not None:
            ads_input_text = ppc_ad_summary_override
        elif ppc_ad_summary and ppc_ad_summary.get("platforms_scraped"):
            ads_input_text = (
                f"Google Ads: {ppc_ad_summary.get('google_total_ads')} ads found. "
                f"Meta Ads: {ppc_ad_summary.get('meta_total_ads')} ads found. "
                f"LinkedIn Ads: {ppc_ad_summary.get('linkedin_total_ads')} ads found."
            )
        else:
            ads_input_text = "No performance marketing data provided."
        strategy_text = run_strategy(seo_audit_text or research_brief, smm_audit_text or "Not applicable — SMM not selected.", ads_input_text)
        save_document(run_dir, "seo_strategy_report.txt", "SEO Strategy Report", strategy_text or "Not generated for this run.")

        # Dynamic content generation (per-category + combined) — identical
        # to legacy endpoint's step 5, the one unconditional cross-category call.
        logger.info("[%s] Running Content Generation agent for categories: %s", run_id_log, categories)
        content = run_content_generation(
            company_name=company_name,
            industry=industry,
            categories=categories,
            research_brief=research_brief,
            seo_audit_text=seo_audit_text,
            smm_audit_text=smm_audit_text,
            strategy_text=strategy_text,
            seo_metrics=seo_metrics,
            ppc_metrics=ppc_metrics,
            smm_metrics=smm_metrics_summary,
            competitor_names=competitors_names,
            ppc_ad_data=ppc_ad_data_for_content,
        )

        # Render PDF — identical to legacy endpoint's step 6.
        logger.info("[%s] Rendering PDF for %d slides", run_id_log, len(slides))
        has_strategic_takeaways_slide = any(s["slug"] == "strategic_takeaways" for s in slides)
        base_ctx = {
            "company_name": company_name,
            "industry": industry,
            "categories": categories,
            "competitor_names": competitors_names,
            "metrics_by_category": {
                "seo": seo_metrics,
                "ppc": ppc_metrics,
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

        state["status"] = "finalized"
        logger.info("[%s] DM Audit run complete (phased flow)", run_id_log)

        return {
            "run_id": run_id,
            "company_name": company_name,
            "domain": state["domain"],
            "categories": categories,
            "slide_count": len(slides),
            "included_slides": [f"{s['slug']}.{s['category']}" if s['category'] else s['slug'] for s in slides],
            "pdf_filename": filename,
            "download_url": f"/api/reports/{run_id}/{filename}",
        }
    except Exception as exc:
        logger.exception("[%s] Finalize failed", run_id_log)
        raise HTTPException(status_code=500, detail=f"Audit finalization failed: {exc}") from exc


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
