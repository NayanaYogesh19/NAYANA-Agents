import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from recommendation_engine.ai_analyzer import analyze_resolution

router = APIRouter()

# Large pool — each resolution is an independent long-running HTTP call
_executor = ThreadPoolExecutor(max_workers=8)


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


@router.get("/analyze_governance")
async def analyze_governance():
    """
    Run AI-powered governance analysis on every resolution in the current session.
    All calls run concurrently in a thread pool — never times out.
    """
    session_path = "storage/session.json"

    if not os.path.exists(session_path):
        return {
            "status":  "error",
            "message": "No active session. Please upload a notice first.",
        }

    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    resolutions = session.get("resolutions", [])
    if not resolutions:
        return {
            "status":  "error",
            "message": "No resolutions found. Run /extract_resolutions first.",
        }

    # Run all analysis calls concurrently — no timeout
    ai_results = await asyncio.gather(*[
        _run_sync(analyze_resolution, r) for r in resolutions
    ])

    analyzed = []
    for r, ai_result in zip(resolutions, ai_results):
        r["ai_analysis"] = ai_result
        analyzed.append(r)

    session["resolutions"] = analyzed
    session["ai_analyzed"] = True

    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)

    return {
        "status":         "success",
        "company_name":   session.get("company_name"),
        "financial_year": session.get("financial_year"),
        "total_analyzed": len(analyzed),
        "resolutions":    analyzed,
    }
