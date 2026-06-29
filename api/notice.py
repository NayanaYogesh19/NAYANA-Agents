import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from pdf_processing.extract_pdf import extract_pdf_text
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH
from pdf_processing.extract_metadata import (
    extract_notice_metadata,
    extract_company_name,
    extract_isin,
    extract_notice_type,
    extract_meeting_datetime,
    extract_meeting_venue,
    extract_evoting_details,
    extract_evoting_result_date,
)

router = APIRouter(prefix="/notice", tags=["Notice Metadata"])

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(fn, *args):
    """Run a blocking function in a thread pool so it doesn't block the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _load_session_and_text() -> tuple[dict | None, str | None, str | None]:
    """Load session + extract PDF text (sync, runs in thread). Returns (session, text, error_msg)."""
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return None, None, "No active session. Please upload a notice first."
    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)
    pdf_path = session.get("pdf_path", "")
    if not os.path.exists(pdf_path):
        return session, None, "Uploaded PDF not found."
    # Use cached text to avoid re-reading large PDFs on every endpoint call
    cached_text = session.get("_cached_pdf_text", "")
    if cached_text:
        return session, cached_text, None
    text = extract_pdf_text(pdf_path)
    try:
        session["_cached_pdf_text"] = text
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=4)
    except Exception:
        pass
    return session, text, None


async def _get_session_text():
    """Async wrapper — extracts PDF text without blocking."""
    return await _run_sync(_load_session_and_text)


def _save_to_session(key: str, value) -> None:
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return
    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)
    session[key] = value
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=4)


# ── 2a: Full metadata (one call for everything) ──────────────────────────────

@router.get("/metadata")
async def get_notice_metadata():
    """
    Extract all cover-page metadata from the uploaded PDF:
    company name, ISIN, notice type, meeting date/time, venue,
    e-voting details, e-voting result date.
    """
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}

    metadata = await _run_sync(extract_notice_metadata, text)
    _save_to_session("notice_metadata", metadata)

    return {"status": "success", **metadata}


# ── 2b: Individual field endpoints ───────────────────────────────────────────

@router.get("/company_name")
async def get_company_name():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_company_name, text)
    return {"status": "success", "company_name": value}


@router.get("/isin")
async def get_isin():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_isin, text)
    return {"status": "success", "isin": value}


@router.get("/notice_type")
async def get_notice_type():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_notice_type, text)
    return {"status": "success", "notice_type": value}


@router.get("/meeting_datetime")
async def get_meeting_datetime():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    dt = await _run_sync(extract_meeting_datetime, text)
    return {"status": "success", "meeting_date": dt["date"], "meeting_time": dt["time"]}


@router.get("/meeting_venue")
async def get_meeting_venue():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_meeting_venue, text)
    return {"status": "success", "meeting_venue": value}


@router.get("/evoting_details")
async def get_evoting_details():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_evoting_details, text)
    return {"status": "success", "evoting_details": value}


@router.get("/evoting_result_date")
async def get_evoting_result_date():
    session, text, err = await _get_session_text()
    if err:
        return {"status": "error", "message": err}
    value = await _run_sync(extract_evoting_result_date, text)
    return {"status": "success", "evoting_result_date": value}
