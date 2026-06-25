"""
Notice metadata extractor — fully dynamic, works for any company/notice PDF.

Handles the real-world PDF text extracted by pypdf, which often has:
- Multi-line table rows (key on one line, value on next)
- Inline prose: "will be held on Monday, 28 August 2023 at 3:30 P.M. IST"
- Non-breaking spaces / tabs (normalized by extract_pdf.py)
- ISIN in formats: INE009A01021, ISIN- INE216A01030, "ISIN Code for Indian equity shares:"
- E-voting period in prose: "commences on Friday, 25 August 2023 (9:00 A.M. IST) and ends on..."
"""

import re

_MONTHS = (
    "January|February|March|April|May|June|July|"
    "August|September|October|November|December"
)
_DAYS = "Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday"
_DATE_PAT = (
    rf"(?:{_DAYS},? )?\d{{1,2}} (?:{_MONTHS}),? \d{{4}}"    # "Monday, 28 August 2023" or "28 August 2023"
    rf"|(?:{_MONTHS}) \d{{1,2}},? \d{{4}}"                  # "August 28, 2023"
    rf"|\d{{1,2}}[/\-]\d{{1,2}}[/\-]\d{{2,4}}"              # "28/08/2023"
)
_TIME_PAT = r"\d{1,2}[:.]\d{2}\s*(?:A\.?\s*\.?\s*M\.?|P\.?\s*\.?\s*M\.?)\s*(?:IST)?"


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _first(pattern: str, text: str, flags=re.IGNORECASE) -> str:
    m = re.search(pattern, text, flags)
    return _clean(m.group(1)) if m else ""


# ── Company name ──────────────────────────────────────────────────────────────

def extract_company_name(text: str) -> str:
    # Strategy 1: "for and on behalf of <Company>" or "on behalf of <Company>"
    for pat in [
        r"(?:[Ff]or and on behalf of|[Oo]n behalf of)\s+([\w\s\.\&\-]+?(?:Limited|Ltd\.?))",
    ]:
        for m in re.finditer(pat, text[:40000], re.IGNORECASE):
            name = _clean(m.group(1)).rstrip(".,;:").strip()
            if 5 < len(name) < 120:
                return name

    # Strategy 2: "Notice of the Nth AGM of <Company>"
    m = re.search(
        r"[Nn]otice of the \w+ (?:Annual General Meeting|AGM|EGM) (?:of )?"
        r"([\w\s\.\&\-]+?(?:Limited|Ltd\.?))",
        text[:15000], re.IGNORECASE,
    )
    if m:
        name = _clean(m.group(1))
        if 5 < len(name) < 120:
            return name

    # Strategy 3: "CIN: LXXXXXX ... <Company> Limited" — notice footer
    m = re.search(
        r"CIN\s*[:\-]?\s*[A-Z]\d{5}[A-Z]{2}\d{4}[A-Z]{3}\d{6}\s*([\w\s\.\&\-]+?(?:Limited|Ltd\.?))",
        text, re.IGNORECASE,
    )
    if m:
        name = _clean(m.group(1))
        if 5 < len(name) < 120:
            return name

    # Strategy 4: Scan first 80 lines for a standalone company name line
    for line in text.splitlines()[:80]:
        line = line.strip()
        if not line:
            continue
        up = line.upper()
        if any(kw in up for kw in ["LIMITED", " LTD", "CORPORATION"]):
            cleaned = re.sub(r"page\s*\|.*$", "", line, flags=re.IGNORECASE).strip()
            # Strip leading "For " prefix
            cleaned = re.sub(r"^[Ff]or (?:and on behalf of )?", "", cleaned).strip()
            cleaned = re.sub(r"^[Oo]n behalf of ", "", cleaned).strip()
            if (5 < len(cleaned) < 120 and
                    not re.search(
                        r"\b(?:BSE|NSE|NYSE|Stock Exchange|SEBI|pursuant|Listed|listing|"
                        r"National|Corporate|Securities)\b",
                        cleaned, re.I)):
                return _clean(cleaned)

    return ""


# ── ISIN ──────────────────────────────────────────────────────────────────────

def extract_isin(text: str) -> str:
    # "ISIN Code for Indian equity shares: INE009A01021"
    m = re.search(r"ISIN [Cc]ode for [Ii]ndian equity shares?\s*[:\-]?\s*([A-Z]{2}[A-Z0-9]{10})", text)
    if m:
        return _clean(m.group(1))

    # "ISIN- INE216A01030" or "ISIN: INE..." or "ISIN - INE..."
    m = re.search(r"\bISIN\s*[-:]?\s*([A-Z]{2}[A-Z0-9]{10})\b", text, re.IGNORECASE)
    if m:
        return _clean(m.group(1))

    # Search entire text for bare INE/US pattern (Indian/ADR equity)
    for m in re.finditer(r"\b(INE[A-Z0-9]{9})\b", text):
        return _clean(m.group(1))

    # US ISIN (Wipro NYSE: WIT has US ISIN too)
    m = re.search(r"\b(US[A-Z0-9]{10})\b", text)
    if m:
        return _clean(m.group(1))

    return ""


# ── Notice type ───────────────────────────────────────────────────────────────

def extract_notice_type(text: str) -> str:
    upper = text[:5000].upper()
    if "POSTAL BALLOT" in upper:
        return "Postal Ballot"
    if "EXTRAORDINARY GENERAL MEETING" in upper or " EGM" in upper:
        return "EGM"
    if "ANNUAL GENERAL MEETING" in upper or " AGM" in upper:
        return "AGM"
    return "AGM"


# ── Meeting date & time ───────────────────────────────────────────────────────

def extract_meeting_datetime(text: str) -> dict:
    """
    Extract meeting date and time using multiple strategies.
    Handles both table-style (key: value) and prose-style PDFs.
    """

    def _parse(raw: str) -> dict:
        """Split raw string into date and time."""
        raw = _clean(raw)
        time_m = re.search(_TIME_PAT, raw, re.IGNORECASE)
        date_m = re.search(_DATE_PAT, raw, re.IGNORECASE)
        return {
            "date": _clean(date_m.group(0)) if date_m else "",
            "time": _clean(time_m.group(0)) if time_m else "",
        }

    # Strategy 1: "Time and date of AGM" table cell — value inline
    m = re.search(
        r"(?:Time and date|Date and time) of (?:AGM|EGM|Meeting)\s*[:\-]?\s*(.{10,160})",
        text, re.IGNORECASE,
    )
    if m:
        r = _parse(m.group(1))
        if r["date"]:
            return r

    # Strategy 2: Same key but value on NEXT line
    m = re.search(
        r"(?:Time and date|Date and time) of (?:AGM|EGM|Meeting)\s*[:\-]?\s*\n\s*(.{10,160})",
        text, re.IGNORECASE,
    )
    if m:
        r = _parse(m.group(1))
        if r["date"]:
            return r

    # Strategy 3: "Meeting Date and time: ..."
    m = re.search(r"Meeting Date and time\s*[:\-]\s*(.{10,160})", text, re.IGNORECASE)
    if m:
        r = _parse(m.group(1))
        if r["date"]:
            return r

    # Strategy 4: "AGM/EGM will be held on ..." — allow newlines in both the match and the captured group
    m = re.search(
        r"(?:AGM|EGM|Annual General Meeting|General Meeting)[\s\S]{0,60}?will\s+be\s+held\s+on\s+([\s\S]{10,300}?)(?:through|via|at the|The venue|\n\n)",
        text, re.IGNORECASE,
    )
    if m:
        r = _parse(m.group(1))
        if r["date"]:
            return r

    # Strategy 5: "Notice is hereby given that ... will be held on ..."
    m = re.search(
        r"[Nn]otice is hereby given[\s\S]{0,300}?will\s+be\s+held\s+on\s+([\s\S]{10,300}?)(?:through|via|to transact|\n\n)",
        text, re.IGNORECASE,
    )
    if m:
        r = _parse(m.group(1))
        if r["date"]:
            return r

    # Strategy 6: Day-of-week + date + time near AGM context
    # handles "Monday, 28 August 2023 at 3:30 P .M. IST" (day-first format)
    for dm in re.finditer(
        rf"(?:{_DAYS}),? (?:\d{{1,2}} (?:{_MONTHS})|(?:{_MONTHS}) \d{{1,2}},?) \d{{4}}",
        text[:20000], re.IGNORECASE,
    ):
        ctx_before = text[max(0, dm.start() - 400): dm.start()]
        if re.search(r"AGM|EGM|General Meeting|Annual Meeting", ctx_before, re.IGNORECASE):
            raw = text[dm.start(): dm.start() + 100]
            r = _parse(raw)
            if r["date"]:
                return r

    # Strategy 7: time + date on same line near AGM context
    m = re.search(
        rf"({_TIME_PAT})[,\s]+(?:\w+,? )?({_DATE_PAT})",
        text[:20000], re.IGNORECASE,
    )
    if m:
        ctx_before = text[max(0, m.start() - 400): m.start()]
        if re.search(r"AGM|EGM|[Gg]eneral|[Gg]lance", ctx_before, re.IGNORECASE):
            return {"date": _clean(m.group(2)), "time": _clean(m.group(1))}

    return {"date": "", "time": ""}


# ── Meeting venue ─────────────────────────────────────────────────────────────

def extract_meeting_venue(text: str) -> str:
    # "Mode:" field in info table
    m = re.search(r"[Mm]ode\s*[:\-]\s*(.{10,200}?)(?:\n|$)", text)
    if m:
        val = _clean(m.group(1))
        if any(kw in val.lower() for kw in ["video", "virtual", "vc", "oavm"]):
            return val

    m = re.search(r"[Mm]eeting [Vv]enue\s*[:\-]\s*(.{5,300}?)(?:\n|$)", text)
    if m:
        return _clean(m.group(1))

    m = re.search(r"[Vv]enue\s*[:\-]\s*(.{5,200}?)(?:\n|$)", text)
    if m:
        return _clean(m.group(1))

    # "through video conferencing" — capture only up to end of that phrase
    m = re.search(
        r"((?:through\s+)?(?:Video Conferencing\s*(?:\(['\"]?VC['\"]?\))?|"
        r"VC\s*/\s*(?:Other\s+)?Audio\s+Visual\s+Means))",
        text, re.IGNORECASE,
    )
    if m:
        return _clean(m.group(0)[:150])

    m = re.search(r"((?:Video Conference|Virtual Meeting|OAVM)[^\n]{0,80})", text, re.IGNORECASE)
    if m:
        return _clean(m.group(1)[:150])

    return ""


# ── E-voting ──────────────────────────────────────────────────────────────────

def _evoting_block(text: str) -> str:
    """Find the e-voting section — prefer the procedural section near 'commences on'."""
    # Look for "E-voting period commences" or "remote E-voting period" — that's the procedural block
    m = re.search(r"[Ee]-?[Vv]oting period commences", text)
    if m:
        return text[max(0, m.start() - 500): m.start() + 3000]
    # Fallback: first e-voting mention
    m = re.search(r"[Ee]-?[Vv]oting", text)
    return text[m.start(): m.start() + 3000] if m else ""


def extract_evoting_agency(text: str) -> str:
    block = _evoting_block(text) or text
    for pattern in [
        r"\b(NSDL)\b",
        r"\b(CDSL)\b",
        r"\b(KFintech|KFin Technologies?)\b",
        r"\b(Link Intime(?:\s+India\s+Pvt\.?\s+Ltd\.?)?)\b",
        r"\b(Karvy Fintech)\b",
    ]:
        m = re.search(pattern, block, re.IGNORECASE)
        if m:
            return _clean(m.group(1)).upper()
    # "E-voting system of NSDL" pattern
    m = re.search(r"[Ee]-?[Vv]oting (?:system|website|platform) of ([\w\s]+?)(?:\.|,|\n|$)", text)
    if m:
        agency = _clean(m.group(1)).strip()
        if len(agency) < 50:
            return agency
    return ""


def _extract_evoting_datetime(text: str, keyword: str) -> str:
    """
    Extract a date+time around a keyword like "commences on" or "ends on".
    Handles the case where date is on the next line after a day-of-week.
    Returns formatted string like "25 August 2023 (9:00 A.M. IST)".
    """
    pat = re.compile(
        keyword + r"\s+(.{0,300}?)(?:During|Members|cut.off|\.(?:\s|$))",
        re.IGNORECASE | re.DOTALL,
    )
    m = pat.search(text)
    if not m:
        return ""
    raw = _clean(m.group(1))
    # Find date and time within raw
    date_m = re.search(_DATE_PAT, raw, re.IGNORECASE)
    time_m = re.search(_TIME_PAT, raw, re.IGNORECASE)
    parts = []
    if date_m:
        parts.append(_clean(date_m.group(0)))
    if time_m:
        parts.append(f"({_clean(time_m.group(0))})")
    return " ".join(parts) if parts else raw[:80]


def extract_evoting_start(text: str) -> str:
    # Strategy A: "Commences at 9 AM IST on Saturday, July 8, 2023 and ends at..."
    m = re.search(
        r"[Cc]ommences?\s+(?:at\s+)?(.{5,100}?)\s+and\s+ends?",
        text, re.IGNORECASE,
    )
    if m:
        raw = _clean(m.group(1))
        time_m = re.search(_TIME_PAT, raw, re.IGNORECASE)
        date_m = re.search(_DATE_PAT, raw, re.IGNORECASE)
        parts = []
        if date_m:
            parts.append(_clean(date_m.group(0)))
        if time_m:
            parts.append(f"({_clean(time_m.group(0))})")
        if parts:
            return " ".join(parts)
        if raw:
            return raw[:80]

    # Strategy B: "E-voting period commences on ..."
    result = _extract_evoting_datetime(text, r"[Ee]-?[Vv]oting period commences on")
    if result:
        return result
    result = _extract_evoting_datetime(text, r"remote [Ee]-?[Vv]oting period commences on")
    if result:
        return result
    for pat in [
        r"[Ee]-?[Vv]oting start (?:time and )?date\s*[:\-]?\s*(.{5,120}?)(?:\n|$)",
        r"[Ee]-?[Vv]oting (?:period )?(?:from|start)\s*[:\-]?\s*(.{5,80}?)(?:\n|$)",
        r"[Ee]-?[Vv]oting (?:commenc|open|begin)\w* (?:date|from|on)?\s*[:\-]?\s*(.{5,80}?)(?:\n|$)",
    ]:
        v = _first(pat, text)
        if v:
            return v
    return ""


def extract_evoting_end(text: str) -> str:
    # Strategy A: "...and ends at 5 PM IST on Tuesday, July 11, 2023"
    m = re.search(
        r"and\s+ends?\s+(?:at\s+)?(.{5,100}?)(?:\n|\.|$)",
        text, re.IGNORECASE,
    )
    if m:
        raw = _clean(m.group(1))
        time_m = re.search(_TIME_PAT, raw, re.IGNORECASE)
        date_m = re.search(_DATE_PAT, raw, re.IGNORECASE)
        parts = []
        if date_m:
            parts.append(_clean(date_m.group(0)))
        if time_m:
            parts.append(f"({_clean(time_m.group(0))})")
        if parts:
            return " ".join(parts)

    # Strategy B: "ends on Sunday, 27 August 2023 (5:00 P.M. IST)"
    result = _extract_evoting_datetime(text, r"ends on")
    if result:
        return result
    for pat in [
        r"[Ee]-?[Vv]oting end (?:time and )?date\s*[:\-]?\s*(.{5,100}?)(?:\n|$)",
        r"[Ee]-?[Vv]oting (?:end|clos|conclud)\w* (?:date|till|until|on)?\s*[:\-]?\s*(.{5,80}?)(?:\n|$)",
    ]:
        v = _first(pat, text)
        if v:
            return v
    return ""


def extract_evoting_details(text: str) -> str:
    agency = extract_evoting_agency(text)
    start  = extract_evoting_start(text)
    end    = extract_evoting_end(text)
    parts  = [p for p in [
        agency,
        f"Start: {start}" if start else "",
        f"End: {end}" if end else "",
    ] if p]
    return " | ".join(parts)


def extract_evoting_result_date(text: str) -> str:
    _DATE_RE = (
        r"(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)\s+\d{4}"
        r"|\w+,\s+\w+\s+\d{1,2},\s+\d{4}"
        r"|\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    )
    for pat in [
        r"[Ee]-?[Vv]oting [Rr]esult [Dd]ate\s*[:\-]\s*" + _DATE_RE,
        r"[Dd]eclaration of [Rr]esult\s*[:\-]?\s*" + _DATE_RE,
        r"[Rr]esults? (?:shall be )?(?:declared|announced) (?:on|by)?\s*" + _DATE_RE,
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return _clean(m.group(1))
    return ""


# ── Main entry ────────────────────────────────────────────────────────────────

def extract_notice_metadata(text: str) -> dict:
    """Parse all cover-page metadata from raw PDF text. Never raises."""
    try:
        dt = extract_meeting_datetime(text)
        return {
            "company_name":        extract_company_name(text),
            "isin":                extract_isin(text),
            "notice_type":         extract_notice_type(text),
            "meeting_date":        dt["date"],
            "meeting_time":        dt["time"],
            "meeting_venue":       extract_meeting_venue(text),
            "evoting_agency":      extract_evoting_agency(text),
            "evoting_start":       extract_evoting_start(text),
            "evoting_end":         extract_evoting_end(text),
            "evoting_details":     extract_evoting_details(text),
            "evoting_result_date": extract_evoting_result_date(text),
        }
    except Exception:
        return {
            "company_name": "", "isin": "", "notice_type": "AGM",
            "meeting_date": "", "meeting_time": "", "meeting_venue": "",
            "evoting_agency": "", "evoting_start": "", "evoting_end": "",
            "evoting_details": "", "evoting_result_date": "",
        }
