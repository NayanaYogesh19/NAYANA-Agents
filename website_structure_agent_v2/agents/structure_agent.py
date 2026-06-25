"""
agents/structure_agent.py
LangChain-powered Website Structure Planning Agent.
AI model: Claude Haiku via OpenRouter
Scraping:  Tavily Search API + BeautifulSoup fallback

Two modes
─────────
audit_existing  → scrape target + competitors → extract audit issues →
                  AI designs corrected structure → recommendations to FIX → PDF

new_structure   → scrape target URL to discover existing endpoints →
                  AI designs optimal new structure based on what's there →
                  recommendations how to BUILD correctly → PDF
"""
import json
import re
import logging
from typing import List, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from models import (
    AgentRequest, AgentOutput, ScrapedSite, AuditFindings,
    StructurePlan, PageNode, NavigationMenu, ConversionPath, AnalysisMode,
)
from tools.scraper import scrape_website, scrape_multiple
from tools.pdf_generator import generate_pdf
from prompts.templates import (
    SITE_ANALYSIS_PROMPT,
    AUDIT_EXTRACTION_PROMPT,
    TARGET_SITE_AUDIT_PROMPT,
    NEW_STRUCTURE_PROMPT,
)

logger = logging.getLogger(__name__)


# ── LLM: Claude Haiku via OpenRouter ─────────────────────────────────────────

def _get_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model        = "anthropic/claude-haiku-4-5",
        api_key      = settings.openai_api_key,
        base_url     = "https://openrouter.ai/api/v1",
        max_tokens   = 8000,
        temperature  = 0.1,
        default_headers = {
            "HTTP-Referer": "https://website-structure-agent.local",
            "X-Title": "Website Structure Agent",
        },
    )


# ── JSON extraction ───────────────────────────────────────────────────────────

def _safe_json(text: str) -> dict:
    text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    start = text.find("{")
    if start == -1:
        return {}
    depth = 0
    end   = start
    for i, ch in enumerate(text[start:], start):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    try:
        return json.loads(text[start:end])
    except json.JSONDecodeError:
        try:
            return json.loads(text)
        except Exception:
            logger.warning("JSON parse failed — returning empty dict")
            return {}


# ── Step helpers ──────────────────────────────────────────────────────────────

def _analyse_site(llm: ChatOpenAI, raw: dict, label: str = "site") -> ScrapedSite:
    """Ask AI to extract structured data from a raw scrape."""
    if raw.get("error") and not raw.get("raw_content"):
        return ScrapedSite(url=raw["url"], error=raw["error"])

    prompt = SITE_ANALYSIS_PROMPT.format(
        url         = raw["url"],
        label       = label,
        raw_content = (raw.get("raw_content") or "")[:4000],
    )
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        data = _safe_json(resp.content)
    except Exception as e:
        logger.error(f"Site analysis failed for {raw['url']}: {e}")
        data = {}

    return ScrapedSite(
        url              = raw["url"],
        nav_labels       = data.get("nav_labels",       raw.get("nav_labels",    [])),
        url_patterns     = data.get("url_patterns",     raw.get("url_patterns",  [])),
        url_endpoints    = data.get("url_endpoints",    []),
        content_depth    = int(data.get("content_depth", raw.get("content_depth", 2))),
        page_count       = int(data.get("page_count",    raw.get("page_count",    0))),
        top_pages        = data.get("top_pages",        []),
        structural_notes = data.get("structural_notes", []),
        error            = raw.get("error"),
    )


def _extract_audit_findings(llm: ChatOpenAI, audit_text: str) -> AuditFindings:
    prompt = AUDIT_EXTRACTION_PROMPT.format(audit_text=audit_text[:5000])
    try:
        resp = llm.invoke([HumanMessage(content=prompt)])
        data = _safe_json(resp.content)
    except Exception as e:
        logger.error(f"Audit extraction failed: {e}")
        data = {}

    return AuditFindings(
        crawl_errors        = data.get("crawl_errors",        []),
        orphan_pages        = data.get("orphan_pages",        []),
        redirect_chains     = data.get("redirect_chains",     []),
        thin_content_pages  = data.get("thin_content_pages",  []),
        missing_pages       = data.get("missing_pages",       []),
        structural_issues   = data.get("structural_issues",   []),
        raw_notes           = audit_text,
    )


def _build_site_summary(site: ScrapedSite, label: str) -> str:
    lines = [
        f"{label}: {site.url}",
        f"  Nav labels    : {', '.join(site.nav_labels[:10]) or 'N/A'}",
        f"  Depth         : {site.content_depth} levels | Pages ~{site.page_count}",
        f"  URL patterns  : {', '.join(site.url_patterns[:8]) or 'N/A'}",
        f"  URL endpoints : {', '.join(site.url_endpoints[:15]) or 'N/A'}",
        f"  Top pages     : {', '.join(site.top_pages[:8]) or 'N/A'}",
        f"  Structure notes: {'; '.join(site.structural_notes[:3]) or 'N/A'}",
    ]
    return "\n".join(lines)


def _build_competitor_summary(sites: List[ScrapedSite]) -> str:
    parts = []
    for i, s in enumerate(sites, 1):
        parts.append(_build_site_summary(s, f"Competitor {i}"))
    return "\n\n".join(parts)


def _parse_plan(data: dict) -> StructurePlan:
    pages = []
    for p in data.get("pages", []):
        try:
            pages.append(PageNode(
                page_name         = p.get("page_name", "Unnamed"),
                tier              = int(p.get("tier", 1)),
                url_slug          = p.get("url_slug", "/"),
                page_type         = p.get("page_type", "page"),
                parent_page       = p.get("parent_page"),
                priority          = p.get("priority", "Medium"),
                cta_type          = p.get("cta_type"),
                wireframe_pattern = p.get("wireframe_pattern"),
            ))
        except Exception as e:
            logger.warning(f"Skipping malformed page: {e}")

    nr = data.get("navigation", {})
    nav = NavigationMenu(
        primary_nav             = nr.get("primary_nav",             []),
        secondary_nav           = nr.get("secondary_nav",           []),
        breadcrumb_example      = nr.get("breadcrumb_example",      []),
        internal_linking_rules  = nr.get("internal_linking_rules",  []),
    )

    cps = [
        ConversionPath(
            goal              = cp.get("goal", ""),
            funnel_steps      = cp.get("funnel_steps",      []),
            cta_per_tier      = cp.get("cta_per_tier",      {}),
            key_landing_pages = cp.get("key_landing_pages", []),
        )
        for cp in data.get("conversion_paths", [])
    ]

    return StructurePlan(
        pages                   = pages,
        navigation              = nav,
        conversion_paths        = cps,
        recommendations         = data.get("recommendations",         []),
        implementation_strategy = data.get("implementation_strategy", []),
    )


# ── Main agent runner ─────────────────────────────────────────────────────────

def run_agent(request: AgentRequest) -> AgentOutput:
    logger.info(f"[Agent] START | mode={request.mode} | target={request.target_url}")

    effective_goal = (
        request.custom_goal
        if request.business_goal.value == "Custom" and request.custom_goal
        else request.business_goal.value
    )

    output = AgentOutput(
        mode          = request.mode.value,
        target_url    = request.target_url,
        business_type = request.business_type.value,
        business_goal = effective_goal,
        status        = "running",
    )

    llm = _get_llm()

    try:
        if request.mode == AnalysisMode.AUDIT_EXISTING:
            # ── STEP 1: Scrape competitors ────────────────────────────────────
            logger.info(f"[Step 1] Scraping {len(request.competitor_urls)} competitor(s)…")
            raw_comp   = scrape_multiple(request.competitor_urls)
            comp_sites = [_analyse_site(llm, r, f"Competitor {i+1}") for i, r in enumerate(raw_comp)]
            output.scraped_competitors = comp_sites
            comp_summary = _build_competitor_summary(comp_sites)

            # ── STEP 2: Scrape target site ────────────────────────────────────
            logger.info(f"[Step 2] Scraping target site: {request.target_url}")
            raw_target     = scrape_website(request.target_url)
            target_site    = _analyse_site(llm, raw_target, "Target Site")
            output.scraped_target = target_site
            target_summary = _build_site_summary(target_site, "Target Site")

            # ── STEP 3: Audit findings (only if user pasted notes) ───────────
            audit_findings    = None
            audit_section_str = ""
            if request.audit_text and request.audit_text.strip():
                logger.info("[Step 3] Extracting audit findings…")
                audit_findings = _extract_audit_findings(llm, request.audit_text)
                output.audit_findings = audit_findings
                audit_section_str = (
                    f"User-provided audit notes:\n{request.audit_text[:2500]}\n\n"
                    f"Extracted issues:\n"
                    f"  Crawl errors      : {', '.join(audit_findings.crawl_errors)      or 'None'}\n"
                    f"  Orphan pages      : {', '.join(audit_findings.orphan_pages)      or 'None'}\n"
                    f"  Redirect chains   : {', '.join(audit_findings.redirect_chains)   or 'None'}\n"
                    f"  Thin content      : {', '.join(audit_findings.thin_content_pages) or 'None'}\n"
                    f"  Structural issues : {', '.join(audit_findings.structural_issues)  or 'None'}\n"
                )
            # If no audit text provided, leave audit_findings as None — skip PDF section

            # ── STEPS 4-6: AI structure design ───────────────────────────────
            logger.info("[Steps 4-6] AI designing corrected structure…")
            system_msg = SystemMessage(content=(
                "You are an expert website architect, SEO strategist, and UX designer. "
                "You produce precise, actionable, site-specific JSON-formatted website structure plans. "
                "Base ALL recommendations on the actual scraped data provided — never give generic advice. "
                "Respond with valid JSON only — no markdown fences, no preamble, no explanation."
            ))
            user_msg = HumanMessage(content=TARGET_SITE_AUDIT_PROMPT.format(
                target_url         = request.target_url,
                business_type      = request.business_type.value,
                business_goal      = effective_goal,
                business_desc      = getattr(request, 'business_desc', '') or '',
                target_summary     = target_summary,
                competitor_summary = comp_summary,
                audit_section      = audit_section_str,
            ))

        else:
            # ── NEW STRUCTURE MODE ────────────────────────────────────────────
            # STEP 1: Scrape target URL to discover existing endpoints
            logger.info(f"[Step 1] Scraping target URL for structure discovery: {request.target_url}")
            raw_target  = scrape_website(request.target_url)
            target_site = _analyse_site(llm, raw_target, "Target Site")
            output.scraped_target = target_site
            target_summary = _build_site_summary(target_site, "Target Site")

            # Also set scraped_competitors empty (no competitors for new_structure)
            output.scraped_competitors = []

            logger.info("[Steps 2-6] AI designing new structure plan…")
            system_msg = SystemMessage(content=(
                "You are an expert website architect, SEO strategist, and UX designer. "
                "You produce precise, actionable, site-specific JSON-formatted website structure plans. "
                "Base ALL recommendations on the actual scraped data provided — never give generic advice. "
                "Respond with valid JSON only — no markdown fences, no preamble, no explanation."
            ))
            user_msg = HumanMessage(content=NEW_STRUCTURE_PROMPT.format(
                target_url     = request.target_url,
                business_type  = request.business_type.value,
                business_goal  = effective_goal,
                business_desc  = getattr(request, 'business_desc', '') or '',
                target_summary = target_summary,
            ))

        resp           = llm.invoke([system_msg, user_msg])
        plan_data      = _safe_json(resp.content)
        structure_plan = _parse_plan(plan_data)
        output.structure_plan = structure_plan

        # ── STEP 7: Generate PDF ──────────────────────────────────────────────
        logger.info("[Step 7] Building PDF report…")
        pdf_path       = generate_pdf(output, settings.output_dir)
        output.pdf_path = pdf_path
        output.status   = "complete"
        logger.info(f"[Agent] DONE — PDF: {pdf_path}")

    except Exception as e:
        logger.error(f"[Agent] ERROR: {e}", exc_info=True)
        output.status = "error"
        output.error  = str(e)

    return output
