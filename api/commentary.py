import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Query

from recommendation_engine.ingovern_commentary import generate_ingovern_commentary
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH

router = APIRouter(tags=["Commentary"])

# Large pool — commentary calls are long-running HTTP requests to OpenRouter
_executor = ThreadPoolExecutor(max_workers=8)


def _load_session():
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return None, "No active session. Please upload a notice first."
    with open(session_path, "r", encoding="utf-8") as f:
        return json.load(f), None


def _save_session(session: dict) -> None:
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _store_rag_background(session, notice_type):
    """Fire-and-forget RAG store — runs in thread, never blocks the response."""
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


@router.get("/generate_commentary")
async def generate_commentary(
    resolution_number: int = Query(None, description="Specific resolution number (omit for all)")
):
    """
    Generate InGovern-style governance commentary for resolutions.
    Runs AI calls in a thread pool — never times out.
    """
    session, err = _load_session()
    if err:
        return {"status": "error", "message": err}

    resolutions = session.get("resolutions", [])
    if not resolutions:
        return {"status": "error", "message": "No resolutions found. Run /extract_resolutions first."}

    board_directors = session.get("board_of_directors", [])

    # Filter if specific resolution requested
    if resolution_number is not None:
        target = [r for r in resolutions if r.get("resolution_number") == resolution_number]
        if not target:
            return {"status": "error", "message": f"Resolution {resolution_number} not found."}
        work_list = target
    else:
        work_list = resolutions

    notice_type    = session.get("notice_metadata", {}).get("notice_type", "AGM")
    company_name   = session.get("company_name", "")
    financial_year = session.get("financial_year", "")

    # Run all commentary calls concurrently in thread pool — no timeout
    def _gen(r):
        return generate_ingovern_commentary(
            r, board_directors,
            notice_type=notice_type,
            company_name=company_name,
            financial_year=financial_year,
        )

    async def _generate_one(r):
        return await _run_sync(_gen, r)

    commentaries = await asyncio.gather(*[_generate_one(r) for r in work_list])

    results = []
    for r, commentary in zip(work_list, commentaries):
        r["ingovern_commentary"] = commentary
        results.append({
            "resolution_number":   r.get("resolution_number"),
            "resolution_type":     r.get("resolution_type"),
            "ingovern_commentary": commentary,
        })

    # Merge back into full session resolutions list
    updated_map = {r.get("resolution_number"): r for r in work_list}
    for orig in session["resolutions"]:
        num = orig.get("resolution_number")
        if num in updated_map:
            orig["ingovern_commentary"] = updated_map[num].get("ingovern_commentary")

    _save_session(session)

    # RAG store runs in background — does not delay the response
    asyncio.get_event_loop().run_in_executor(
        _executor, _store_rag_background, dict(session), notice_type
    )

    return {
        "status":          "success",
        "company_name":    session.get("company_name"),
        "financial_year":  session.get("financial_year"),
        "total_processed": len(results),
        "commentaries":    results,
    }
