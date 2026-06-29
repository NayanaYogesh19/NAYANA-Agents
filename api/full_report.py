"""
Step 6: Structured report generation
Step 10: Download report (PDF / HTML)

GET  /full_report/generate   — build structured JSON report + save to session
GET  /full_report/download   — download as PDF (WeasyPrint) or HTML fallback
GET  /full_report/view       — return report JSON for frontend rendering
"""

import os
import json
import asyncio
from datetime import date
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from report_generator.generate_pdf import generate_pdf_report
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH

router = APIRouter(prefix="/full_report", tags=["Full Report"])

REPORTS_DIR = REPORTS_DIR

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _load_session() -> tuple[dict | None, str | None]:
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return None, "No active session."
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f), None


def _save_session(session: dict) -> None:
    os.makedirs("storage", exist_ok=True)
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4, ensure_ascii=False)


def _build_structured_report(session: dict) -> dict:
    resolutions = session.get("resolutions", [])
    meta        = session.get("notice_metadata", {})

    summary_table = []
    for r in resolutions:
        comm    = r.get("ingovern_commentary", {})
        rec_obj = r.get("recommendation", {})
        rec_val = rec_obj.get("recommendation", "FOR") if isinstance(rec_obj, dict) else "FOR"

        summary_table.append({
            "resolution_number":         r.get("resolution_number"),
            "title":                     r.get("title", r.get("resolution_type", "")),
            "resolution_type":           r.get("resolution_type", ""),
            "ordinary_resolution":       r.get("ordinary_resolution", False),
            "special_resolution":        r.get("special_resolution", False),
            "management_recommendation": comm.get("management_recommendation", "FOR"),
            "ingovern_recommendation":   comm.get("ingovern_recommendation", rec_val),
            "confidence":                comm.get("confidence", rec_obj.get("confidence", "Medium") if isinstance(rec_obj, dict) else "Medium"),
            "risk_flags":                r.get("risk_flags", []),
            "director_name":             r.get("director_name", ""),
        })

    detail_sections = []
    for r in resolutions:
        comm    = r.get("ingovern_commentary", {})
        ai_anal = r.get("ai_analysis", {})
        detail_sections.append({
            "resolution_number":         r.get("resolution_number"),
            "title":                     r.get("title", r.get("resolution_type", "")),
            "resolution_type":           r.get("resolution_type", ""),
            "ordinary_resolution":       r.get("ordinary_resolution", False),
            "special_resolution":        r.get("special_resolution", False),
            "director_name":             r.get("director_name", ""),
            "board_recommendation":      r.get("board_recommendation", ""),
            "annexures":                 r.get("annexures", []),
            "management_recommendation": comm.get("management_recommendation", "FOR"),
            "ingovern_recommendation":   comm.get("ingovern_recommendation", "FOR"),
            "confidence":                comm.get("confidence", "Medium"),
            "introduction":              comm.get("introduction", ""),
            "summary_paragraphs":        comm.get("summary_paragraphs", []),
            "ingovern_commentary":       comm.get("ingovern_commentary", []),
            "governance_concerns":       comm.get("governance_concerns", []),
            "closing_recommendation":    comm.get("closing_recommendation", ""),
            "key_facts":                 comm.get("key_facts", {}),
            "risk_flags":                r.get("risk_flags", []),
            "ai_analysis":               ai_anal,
            "precedents":                r.get("precedents", []),
        })

    return {
        "report_date":        date.today().isoformat(),
        "company_name":       session.get("company_name", meta.get("company_name", "")),
        "financial_year":     session.get("financial_year", ""),
        "notice_metadata":    meta,
        "board_of_directors": session.get("board_of_directors", []),
        "approved_by":        session.get("approved_by", ""),
        "analyst_comments":   session.get("comments", ""),
        "summary_table":      summary_table,
        "resolution_details": detail_sections,
        "total_resolutions":  len(resolutions),
        "status":             session.get("status", ""),
    }


def _store_rag_background(session, notice_type):
    """Fire-and-forget RAG store — never blocks the response."""
    try:
        from database.rag_store import store_resolution_rag
        for r in session.get("resolutions", []):
            comm = r.get("ingovern_commentary", {})
            if comm:
                try:
                    store_resolution_rag(
                        company_name   = session.get("company_name", ""),
                        financial_year = session.get("financial_year", ""),
                        notice_type    = notice_type,
                        industry       = session.get("industry", ""),
                        resolution     = r,
                        commentary     = comm,
                    )
                except Exception:
                    pass
    except Exception:
        pass


# ── Step 6: Generate ──────────────────────────────────────────────────────────

@router.get("/generate")
async def generate_structured_report():
    session, err = _load_session()
    if err:
        return {"status": "error", "message": err}

    if not session.get("resolutions"):
        return {"status": "error", "message": "No resolutions found. Run /extract_resolutions first."}

    # Run blocking report-build in thread pool
    structured = await _run_sync(_build_structured_report, session)
    session["structured_report"] = structured

    # Save JSON to storage/reports/
    os.makedirs(REPORTS_DIR, exist_ok=True)
    company   = session.get("company_name", "Company").replace(" ", "_")
    fy        = session.get("financial_year", "FY").replace(" ", "_")
    json_path = os.path.join(REPORTS_DIR, f"{company}_{fy}_report.json")

    def _write_report():
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=2, ensure_ascii=False)

    await _run_sync(_write_report)
    _save_session(session)

    # RAG store in background — never delays the response
    notice_type = session.get("notice_metadata", {}).get("notice_type", "AGM")
    asyncio.get_event_loop().run_in_executor(
        _executor, _store_rag_background, dict(session), notice_type
    )

    return {
        "status":   "success",
        "message":  f"Report generated and saved to {json_path}",
        "saved_to": os.path.abspath(json_path),
        "report":   structured,
    }


# ── Step 10: Download PDF ─────────────────────────────────────────────────────

@router.get("/download")
async def download_report():
    session, err = _load_session()
    if err:
        return JSONResponse({"status": "error", "message": err})

    if not session.get("resolutions"):
        return JSONResponse({"status": "error", "message": "No resolutions. Run /extract_resolutions first."})

    structured = await _run_sync(_build_structured_report, session)
    session["structured_report"] = structured
    _save_session(session)

    # WeasyPrint/Jinja2 rendering runs in thread pool — no timeout
    result = await _run_sync(generate_pdf_report, session)

    if result["status"] == "error":
        return JSONResponse({"status": "error", "message": result["message"]})

    if result["status"] == "html_only":
        return HTMLResponse(
            content=result["html_content"],
            status_code=200,
            headers={
                "Content-Type":        "text/html; charset=utf-8",
                "Content-Disposition": f'attachment; filename="{result["filename"]}"',
            },
        )

    filepath = result["filepath"]
    if not os.path.exists(filepath):
        rel = os.path.join(REPORTS_DIR, result["filename"])
        if os.path.exists(rel):
            filepath = rel
        else:
            return JSONResponse({
                "status":  "error",
                "message": f"PDF not found at {filepath}. Try /full_report/view for JSON.",
            })

    return FileResponse(
        path       = filepath,
        media_type = "application/pdf",
        filename   = result["filename"],
        headers    = {"Content-Disposition": f'attachment; filename="{result["filename"]}"'},
    )


# ── View report JSON ──────────────────────────────────────────────────────────

@router.get("/view")
async def view_report():
    session, err = _load_session()
    if err:
        return {"status": "error", "message": err}

    structured = session.get("structured_report")
    if not structured:
        if session.get("resolutions"):
            structured = await _run_sync(_build_structured_report, session)
        else:
            return {"status": "error", "message": "No report yet. Run /full_report/generate first."}

    return {"status": "success", "report": structured}
