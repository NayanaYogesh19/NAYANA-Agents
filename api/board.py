import os
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter

from pdf_processing.extract_pdf import extract_pdf_text
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH
from pdf_processing.extract_board import (
    extract_board_of_directors,
    extract_attendance_table,
)

router = APIRouter(prefix="/board", tags=["Board of Directors"])

_executor = ThreadPoolExecutor(max_workers=4)


async def _run_sync(fn, *args):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, fn, *args)


def _load_pdf_text_sync() -> tuple:
    """Returns (text, pdf_path, error_msg). Blocking — call via _run_sync."""
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return None, None, "No active session. Please upload a notice first."
    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)
    pdf_path = session.get("pdf_path", "")
    if not os.path.exists(pdf_path):
        return None, None, "Uploaded PDF not found."
    # Use cached PDF text from session if already extracted (avoids re-reading large PDFs)
    cached_text = session.get("_cached_pdf_text", "")
    if cached_text:
        return cached_text, pdf_path, None
    text = extract_pdf_text(pdf_path)
    # Cache it back to session so other endpoints don't re-extract
    try:
        session["_cached_pdf_text"] = text
        with open(session_path, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=4)
    except Exception:
        pass
    return text, pdf_path, None


async def _load_pdf_text():
    return await _run_sync(_load_pdf_text_sync)


def _save_to_session(key: str, value) -> None:
    session_path = SESSION_PATH
    if not os.path.exists(session_path):
        return
    with open(session_path, "r", encoding="utf-8") as f:
        s = json.load(f)
    s[key] = value
    with open(session_path, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=4)


@router.get("/directors")
async def get_directors():
    text, pdf_path, err = await _load_pdf_text()
    if err:
        return {"status": "error", "message": err}

    def _extract(t, p):
        return extract_board_of_directors(t, pdf_path=p)

    directors = await _run_sync(_extract, text, pdf_path)
    _save_to_session("board_of_directors", directors)

    return {
        "status":    "success",
        "total":     len(directors),
        "directors": directors,
    }


@router.get("/attendance")
async def get_attendance():
    text, pdf_path, err = await _load_pdf_text()
    if err:
        return {"status": "error", "message": err}

    attendance = await _run_sync(extract_attendance_table, text)
    _save_to_session("director_attendance", attendance)

    return {
        "status":     "success",
        "total":      len(attendance),
        "attendance": attendance,
    }


@router.get("/full")
async def get_board_full():
    text, pdf_path, err = await _load_pdf_text()
    if err:
        return {"status": "error", "message": err}

    def _extract_full(t, p):
        directors  = extract_board_of_directors(t, pdf_path=p)
        attendance = extract_attendance_table(t)
        att_map = {a["name"].lower(): a for a in attendance}
        for d in directors:
            att = att_map.get(d["name"].lower(), {})
            d["agm_attended"]   = att.get("agm_attended")
            d["board_held"]     = att.get("board_held")
            d["board_attended"] = att.get("board_attended")
            d["board_pct"]      = att.get("board_pct")
        return directors

    directors = await _run_sync(_extract_full, text, pdf_path)
    _save_to_session("board_of_directors", directors)

    return {
        "status":    "success",
        "total":     len(directors),
        "directors": directors,
    }
