import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from pdf_processing.extract_pdf import extract_pdf_text
from resolution_extractor.extract_resolutions import extract_resolutions

from policy_retrieval.retrieve_policy import get_policy
from precedent_retrieval.retrieve_precedent import get_precedents

from recommendation_engine.recommend import generate_recommendation
from report_generator.generate_report import generate_report

from recommendation_engine.governance_factor import extract_governance_factors
from recommendation_engine.risk_flags import detect_risks
from recommendation_engine.evaluate import evaluate_governance

router = APIRouter()

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _load_cached_text(pdf_path: str, session_path: str = "storage/session.json") -> str:
    """Return cached PDF text from session if available, else extract and cache it."""
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        cached = session.get("_cached_pdf_text", "")
        if cached:
            return cached
    except Exception:
        pass
    text = extract_pdf_text(pdf_path)
    try:
        with open(session_path, "r", encoding="utf-8") as f:
            session = json.load(f)
        session["_cached_pdf_text"] = text
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=4)
    except Exception:
        pass
    return text


def _extract_all_resolutions(pdf_path: str) -> tuple[list, list]:
    """Blocking: extract text, resolutions, enrich each one. Returns (resolutions, report)."""
    text = _load_cached_text(pdf_path)
    resolutions = extract_resolutions(text)

    for r in resolutions:
        r["policy"]      = get_policy(r["resolution_type"])
        r["precedents"]  = get_precedents(r["resolution_type"])
        r["recommendation"] = generate_recommendation(r)
        factors          = extract_governance_factors(r)
        risks            = detect_risks(r)
        result           = evaluate_governance(factors, r["policy"], r["precedents"], risks)
        r["governance_factors"]    = factors
        r["risk_flags"]            = risks
        r["governance_evaluation"] = result

    report = generate_report(resolutions)
    return resolutions, report


@router.get("/extract_resolutions")
async def resolution_agent():
    session_path = "storage/session.json"

    if not os.path.exists(session_path):
        return {"status": "error", "message": "No active session found. Please upload a notice first."}

    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    pdf_path = session.get("pdf_path", "")

    if not os.path.exists(pdf_path):
        return {"status": "error", "message": "Uploaded PDF not found."}

    resolutions, report = await _run_sync(_extract_all_resolutions, pdf_path)

    session["resolutions"] = resolutions
    session["report"]      = report
    session["status"]      = "report_generated"

    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)

    return {
        "status":            "success",
        "company_name":      session.get("company_name", ""),
        "financial_year":    session.get("financial_year", ""),
        "filename":          os.path.basename(pdf_path),
        "total_resolutions": len(resolutions),
        "resolutions":       resolutions,
        "report":            report,
    }
