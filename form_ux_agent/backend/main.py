"""
main.py
Form & UX Optimisation Agent — FastAPI Backend
Trilliant Digital

Routes:
  GET  /                        → Serve frontend
  GET  /api/accounts            → List all registered accounts
  POST /api/analyse/website     → Run website form analysis
  POST /api/analyse/meta        → Generate Meta instant form spec
  GET  /api/download/{filename} → Download generated PDF / CSV
  GET  /health                  → Health check
"""

import os
import sys
import uuid
from pathlib import Path
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from pydantic import BaseModel, HttpUrl
from dotenv import load_dotenv

load_dotenv()

# ── Add backend to path ───────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent))

from accounts import get_all_accounts, find_account_by_url, find_account_by_name
from modules.scraper import scrape_url
from modules.ux_engine import run_ux_checks, estimate_conversion_loss
from modules.analytics import fetch_ga4_data, get_google_auth_url, exchange_code_for_tokens, _load_tokens
from modules.ai_engine import diagnose_form, generate_meta_form_spec, generate_report_summary, generate_new_form_blueprint
from modules.report_generator import generate_pdf_report, generate_ux_table_csv, generate_new_form_pdf

# ── App Setup ─────────────────────────────────────────────
app = FastAPI(
    title="Form & UX Optimisation Agent",
    description="AI-powered form auditing for B2B & B2C lead generation",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
OUTPUT_DIR = BASE_DIR / "backend" / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))


# ── Request Models ────────────────────────────────────────

class FormDiscoverRequest(BaseModel):
    url: str
    account_name: str = ""


class CreateFormRequest(BaseModel):
    account_name: str
    website_url: str
    business_goal: str = "Lead Generation"
    audience: str = "b2b"
    device_priority: str = "both"
    ga4_property_id: str = ""
    user_description: str = ""


class WebsiteAnalysisRequest(BaseModel):
    account_name: str
    form_url: str
    mode: str = "optimise"          # "create" or "optimise"
    business_goal: str = "Lead Generation"
    audience: str = "b2b"           # "b2b" or "b2c"
    device_priority: str = "both"   # "mobile", "desktop", "both"
    ga4_property_id: str = ""
    user_description: str = ""


class MetaFormRequest(BaseModel):
    account_name: str
    business_goal: str = "Lead Generation"
    audience: str = "b2c"
    # Form type matches Meta Ads Manager options
    form_type: str = "More volume"        # "More volume" | "Higher intent" | "Rich creative"
    flexible_delivery: bool = True
    # Intro card (Meta: Intro screen)
    intro_headline: str = ""
    intro_description: str = ""
    # Questions section (Meta: Questions screen — Contact Information)
    questions_description: str = ""
    contact_fields: list[str] = ["Email", "Full name", "Phone number"]
    custom_questions: list[str] = []
    user_description: str = ""
    # Privacy Policy (Meta: Privacy Policy screen)
    privacy_policy_url: str = ""
    privacy_link_text: str = ""


# ── Routes ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def serve_frontend(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "Form & UX Optimisation Agent", "version": "1.0.0"}


# ── Google OAuth Routes ───────────────────────────────────

@app.get("/auth/google")
async def google_auth_start():
    """Redirect user to Google OAuth consent screen."""
    url = get_google_auth_url()
    return JSONResponse({"auth_url": url, "message": "Open this URL in your browser to connect GA4."})


@app.get("/auth/google/callback")
async def google_auth_callback(request: Request, code: str = None, error: str = None):
    """Handle OAuth callback — exchange code for tokens and store them."""
    if error:
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#fdecea;color:#c0392b">
        <h2>❌ Google Auth Failed</h2><p>{error}</p>
        <a href="/" style="color:#3B0F4E">← Back to Agent</a>
        </body></html>
        """)
    if not code:
        return HTMLResponse("<html><body>No code received.</body></html>", status_code=400)

    try:
        tokens = exchange_code_for_tokens(code)
        if "error" in tokens:
            raise ValueError(tokens.get("error_description", tokens["error"]))
        return HTMLResponse("""
        <html><body style="font-family:sans-serif;padding:40px;background:#e9f7ef;color:#1a7f45;text-align:center">
        <h2>✅ GA4 Connected Successfully!</h2>
        <p>Your Google Analytics account is now linked. Real GA4 data will be used for all future analyses.</p>
        <br><a href="/" style="background:#3B0F4E;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700">
        ← Back to Agent</a>
        </body></html>
        """)
    except Exception as e:
        return HTMLResponse(f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#fdecea;color:#c0392b">
        <h2>❌ Token Exchange Failed</h2><p>{str(e)}</p>
        <a href="/" style="color:#3B0F4E">← Back to Agent</a>
        </body></html>
        """, status_code=400)


@app.get("/auth/google/status")
async def google_auth_status():
    """Check if GA4 is connected."""
    tokens = _load_tokens()
    connected = bool(tokens.get("access_token") or tokens.get("refresh_token"))
    return {
        "connected": connected,
        "message": "GA4 connected — real data will be used." if connected else "GA4 not connected — using illustrative data.",
    }


@app.get("/api/accounts")
async def list_accounts():
    """Return all registered accounts for the frontend dropdown."""
    accounts = get_all_accounts()
    return {"accounts": accounts, "count": len(accounts)}


@app.post("/api/discover/forms")
async def discover_forms(req: FormDiscoverRequest):
    """
    Crawl a website and return every form found across all pages.
    Strategy:
      1. Scrape the given URL
      2. If no forms found, crawl internal links (prioritising contact/quote/enquiry pages)
      3. Return all forms found with their source page URL
    """
    from modules.scraper import crawl_site_for_forms
    try:
        form_summaries = crawl_site_for_forms(req.url)
    except Exception as e:
        raise HTTPException(400, f"Could not crawl site: {str(e)}")

    return {
        "status": "ok",
        "base_url": req.url,
        "forms_found": len(form_summaries),
        "forms": form_summaries,
    }


@app.post("/api/create/form")
async def create_new_form(req: CreateFormRequest):
    """
    Create new form pipeline:
    1. Validate account
    2. Scrape website for content (not forms — we want page text/structure)
    3. AI generates complete form blueprint based on site content
    4. Generate downloadable PDF blueprint
    """
    account = find_account_by_name(req.account_name)
    if not account:
        raise HTTPException(404, f"Account '{req.account_name}' not found.")

    # Scrape homepage + key pages to understand the business
    scrape_result = scrape_url(req.website_url)
    page_title = scrape_result.get("page_title", req.account_name)

    # Build a content summary from the scraped HTML snippet
    raw_snippet = scrape_result.get("raw_snippet", "")
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(raw_snippet, "html.parser")
    # Extract visible text — headings, paragraphs, nav items
    text_parts = []
    for tag in soup.find_all(["h1", "h2", "h3", "p", "li", "span"]):
        t = tag.get_text(strip=True)
        if t and len(t) > 15:
            text_parts.append(t)
    site_content_summary = " | ".join(text_parts[:40]) or f"{page_title} — {req.website_url}"

    # Generate form blueprint via AI
    blueprint = generate_new_form_blueprint(
        account_name=req.account_name,
        website_url=req.website_url,
        page_title=page_title,
        site_content_summary=site_content_summary,
        business_goal=req.business_goal,
        audience=req.audience,
        device_priority=req.device_priority,
        user_description=req.user_description,
    )

    # Generate downloadable PDF
    run_id = str(uuid.uuid4())[:8]
    safe_name = req.account_name.replace(" ", "_").lower()
    pdf_filename = f"new_form_blueprint_{safe_name}_{date.today()}_{run_id}.pdf"
    pdf_path = generate_new_form_pdf(
        account_name=req.account_name,
        website_url=req.website_url,
        business_goal=req.business_goal,
        audience=req.audience,
        blueprint=blueprint,
        filename=pdf_filename,
    )

    return {
        "status": "success",
        "account": account,
        "mode": "create",
        "website_url": req.website_url,
        "page_title": page_title,
        "blueprint": blueprint,
        "downloads": {
            "pdf_blueprint": f"/api/download/{pdf_filename}",
        },
    }


@app.post("/api/analyse/website")
async def analyse_website_form(req: WebsiteAnalysisRequest):
    """
    Full website form analysis pipeline:
    1. Validate account + URL match
    2. Scrape form
    3. Run UX checks
    4. Fetch analytics
    5. AI diagnosis
    6. Generate PDF + CSV
    """
    # ── Step 1: Validate account ──────────────────────────
    account = find_account_by_name(req.account_name)
    if not account:
        raise HTTPException(404, f"Account '{req.account_name}' not found in accounts database.")

    if req.mode == "optimise":
        url_match = find_account_by_url(req.form_url)
        if not url_match:
            raise HTTPException(400, (
                f"The URL '{req.form_url}' does not match any registered account. "
                "Please use a URL belonging to a registered account, or register this account first."
            ))

    # ── Step 2: Scrape ────────────────────────────────────
    scrape_result = scrape_url(req.form_url)
    if scrape_result.get("error"):
        raise HTTPException(400, f"Could not scrape URL: {scrape_result['error']}")

    forms = scrape_result.get("forms", [])
    if not forms and req.mode == "optimise":
        raise HTTPException(404, "No forms detected on this page. Please check the URL points to a page with a form.")

    # If no forms found in create mode, use empty form stub
    primary_form = forms[0] if forms else {"fields": [], "cta": {}, "field_count": 0, "has_trust_signals": False, "has_gdpr_consent": False, "error_messages": []}

    # ── Step 3: UX Analysis ───────────────────────────────
    ux_results = run_ux_checks(primary_form, req.audience, req.device_priority)
    conversion_loss = estimate_conversion_loss(
        ux_results["ux_score"],
        primary_form.get("field_count", 0),
        req.audience,
    )

    # ── Step 4: Analytics ─────────────────────────────────
    ga4_id = req.ga4_property_id or account.get("ga4_property_id", "")
    analytics = fetch_ga4_data(ga4_id, form_fields=primary_form.get("fields", []))

    # ── Step 5: AI Diagnosis ──────────────────────────────
    diagnosis = diagnose_form(
        primary_form,
        ux_results,
        analytics,
        req.audience,
        req.business_goal,
        user_description=req.user_description,
    )
    report_summary = generate_report_summary(
        diagnosis, ux_results, conversion_loss, req.audience, req.business_goal
    )

    # ── Step 6: Generate Outputs ──────────────────────────
    run_id = str(uuid.uuid4())[:8]
    safe_name = req.account_name.replace(" ", "_").lower()
    pdf_filename = f"form_audit_{safe_name}_{date.today()}_{run_id}.pdf"
    csv_filename = f"ux_table_{safe_name}_{date.today()}_{run_id}.csv"

    pdf_path = generate_pdf_report(
        account_name=req.account_name,
        url=req.form_url,
        audience=req.audience,
        business_goal=req.business_goal,
        ux_results=ux_results,
        diagnosis=diagnosis,
        conversion_loss=conversion_loss,
        analytics=analytics,
        report_summary=report_summary,
        filename=pdf_filename,
    )
    csv_path = generate_ux_table_csv(ux_results, diagnosis, filename=csv_filename)

    return {
        "status": "success",
        "account": account,
        "mode": req.mode,
        "url_audited": req.form_url,
        "page_title": scrape_result.get("page_title", ""),
        "forms_found": len(forms),
        "ux_results": ux_results,
        "conversion_loss": conversion_loss,
        "analytics": analytics,
        "diagnosis": diagnosis,
        "report_summary": report_summary,
        "downloads": {
            "pdf_brief": f"/api/download/{pdf_filename}",
            "ux_table_csv": f"/api/download/{csv_filename}",
        },
    }


@app.post("/api/analyse/meta")
async def generate_meta_form(req: MetaFormRequest):  # noqa: F811
    """
    Generate a complete Meta instant form specification.
    Validates account exists in the spreadsheet.
    """
    account = find_account_by_name(req.account_name)
    if not account:
        raise HTTPException(404, f"Account '{req.account_name}' not found.")

    meta_spec = generate_meta_form_spec(
        account_name=req.account_name,
        business_goal=req.business_goal,
        audience=req.audience,
        form_type=req.form_type,
        flexible_delivery=req.flexible_delivery,
        intro_headline=req.intro_headline,
        intro_description=req.intro_description,
        questions_description=req.questions_description,
        contact_fields=req.contact_fields,
        custom_questions=req.custom_questions,
        user_description=req.user_description,
        website_url=account.get("website_url", ""),
        privacy_policy_url=req.privacy_policy_url or account.get("website_url", "").rstrip("/") + "/privacy",
        privacy_link_text=req.privacy_link_text or f"Visit {req.account_name}'s Privacy Policy.",
    )

    # Generate downloadable PDF for Meta spec
    run_id = str(uuid.uuid4())[:8]
    safe_name = req.account_name.replace(" ", "_").lower()
    meta_pdf_filename = f"meta_form_spec_{safe_name}_{date.today()}_{run_id}.pdf"
    from modules.report_generator import generate_meta_form_pdf
    generate_meta_form_pdf(
        account_name=req.account_name,
        business_goal=req.business_goal,
        audience=req.audience,
        meta_spec=meta_spec,
        filename=meta_pdf_filename,
    )

    return {
        "status": "success",
        "account": account,
        "platform": "Meta (Facebook & Instagram)",
        "audience": req.audience.upper(),
        "meta_form_spec": meta_spec,
        "implementation_steps": [
            "1. Go to Meta Ads Manager → Lead ads → Create form",
            "2. Set Form type as shown in spec (Higher intent for B2B, More volume for B2C)",
            "3. Add Intro card — choose from the 5 headline options provided",
            "4. Add Questions section using the generated field list",
            "5. Add Privacy Policy link from the spec",
            "6. Configure Thank-you screen — choose from the 5 options per element",
            "7. Set up CRM webhook using Zapier or native Meta integration",
        ],
        "downloads": {
            "meta_spec_pdf": f"/api/download/{meta_pdf_filename}",
        },
    }


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Serve generated PDF or CSV files."""
    # Security: only allow files from the output directory
    filepath = OUTPUT_DIR / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(404, "File not found or has expired.")
    # Prevent path traversal
    try:
        filepath.resolve().relative_to(OUTPUT_DIR.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied.")

    media_type = "application/pdf" if filename.endswith(".pdf") else "text/csv"
    return FileResponse(str(filepath), media_type=media_type, filename=filename)
