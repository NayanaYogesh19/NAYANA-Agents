"""
Board of Directors extractor — dynamic, works for any company's AGM/EGM/InGovern PDF.

Handles formats after text normalization:

Format A — Corporate governance table (Directors + DIN + Attendance columns):
  "Mr. Nusli N. Wadia, Chairman  00015731  7  Yes  3  Nil  4,500"

Format B — Profile-card narrative:
  "Date of appointment: DD MMM YYYY"

Format C — Annexure brief profile blocks:
  "Name of Director: Helene Auriol Potier"

Format D — Resolution text with inline DIN:
  "Mr. Salil Parekh (DIN: 01876159) ... CEO and MD"

Format E — InGovern report structured table (pdfplumber table extraction):
  Columns: S.No | Name | Years as Director | Date of Appointment | Chairman | MD |
           Executive | Non-Executive | Independent | Audit | NRC | Stakeholder
  Checkmarks: "✓" or "c" (chairman) or "vc" (vice-chairman) in cells
"""

import re


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


_TITLE_PREFIX_RE = re.compile(
    r"\b(?:Mr|Ms|Mrs|Dr|Shri|Smt|Prof)\.?\s+", re.IGNORECASE
)

_ROLE_PATTERNS = {
    "chairman":      re.compile(r"\bchairman\b(?!\s*(?:of\s+(?:audit|nomination|stakeholder|csr|risk)|/\s*Membership))", re.I),
    "md_ceo":        re.compile(r"\bmanaging director\b|\bchief executive officer\b|\bmd & ceo\b|\bmd&ceo\b|\bvice-chairman and managing\b", re.I),
    "executive":     re.compile(r"\bexecutive director\b|\bwhole-time director\b|\bwholetime director\b", re.I),
    "non_executive": re.compile(r"\bnon.executive\b", re.I),
    "independent":   re.compile(r"\bindependent director\b|\bindependent directors\b|\blind\b", re.I),
    "promoter":      re.compile(r"\bpromoter\b", re.I),
}

_COMMITTEE_PATTERNS = {
    "audit":                   re.compile(r"\baudit committee\b", re.I),
    "nomination_remuneration": re.compile(r"\bnomination and remuneration\b|\bnrc\b", re.I),
    "stakeholder":             re.compile(r"\bstakeholders? relationship\b|\bgrievance\b", re.I),
    "risk":                    re.compile(r"\brisk management\b", re.I),
    "csr":                     re.compile(r"\bcsr\b|\bcorporate social responsibility\b", re.I),
}

# Words that disqualify a string from being a director name
_NAME_NOISE_RE = re.compile(
    r"\b(?:is hereby|pursuant|resolved|approval|accorded|be and|hereby|"
    r"appointment of|re-?appointment|reappointment|approval|committee|"
    r"infosys|annual report|notice|board of directors|resolution|"
    r"financial|statement|company|pursuant|section|act)\b",
    re.IGNORECASE,
)

_DIN_RE = re.compile(r"\b(\d{8})\b")


def _classify_role(title_text: str) -> dict:
    roles = {k: False for k in _ROLE_PATTERNS}
    for key, pat in _ROLE_PATTERNS.items():
        if pat.search(title_text):
            roles[key] = True
    if roles["chairman"]:
        roles["chairman"] = "Chairman"
    return roles


def _classify_committees(text: str) -> dict:
    comms = {k: False for k in _COMMITTEE_PATTERNS}
    for key, pat in _COMMITTEE_PATTERNS.items():
        if pat.search(text):
            comms[key] = True
    return comms


def _is_valid_name(name: str) -> bool:
    """Return True if the string looks like a real person name."""
    if not name or len(name) < 4 or len(name) > 80:
        return False
    if _NAME_NOISE_RE.search(name):
        return False
    words = name.split()
    if len(words) > 7:
        return False
    # Must start with capital letter
    if not re.match(r"[A-Z]", name):
        return False
    return True


def _name_key(name: str) -> str:
    """Normalise name for deduplication."""
    n = _TITLE_PREFIX_RE.sub("", name).strip().lower()
    return re.sub(r"\s+", " ", n)


# ── Format A: DIN-based governance table ──────────────────────────────────────
# e.g. "Mr. Nusli N. Wadia, Chairman  00015731  7  Yes  3  Nil  4,500"
# Names may span multiple lines due to PDF column layout

_GOVERNANCE_TABLE_RE = re.compile(
    r"(?:Details of Directors,? their Attendance"
    r"|Name of the Director\s+Director\s+Identification"
    r"|Name of the Director\s+Director\s*\nIdentification"
    r"|Details of Directors.*?Director\s+Identification)",
    re.IGNORECASE | re.DOTALL,
)

_APPT_DATE_RE = re.compile(
    r"(?:appointed|appointment|w\.?e\.?f\.?|with effect from|effect from|from)\s+"
    r"((?:\d{1,2}(?:st|nd|rd|th)?\s+)?(?:January|February|March|April|May|June|July|"
    r"August|September|October|November|December)\s+\d{1,2},?\s*\d{4}"
    r"|\d{1,2}[/\-]\d{2,4})",
    re.IGNORECASE,
)

# Known non-name patterns to skip when walking lines before a DIN
_SKIP_LINE_RE = re.compile(
    r"^(?:[A-Z\s]{8,}$"
    r"|[\d\s\.\-\%,]+$"                    # pure numbers/data
    r"|\d{8}\s+[\d\w\s\-,\.]+$"            # attendance row: "00015731 7 Yes 3 Nil 4,500"
    r"|No\.|AGM|Board|Name of|Director Identification"
    r"|Attendance|Committee|Chairmanship|Membership|Directorships|Equity|Shares held"
    r"|Promoter and Non|Executive Directors|Independent Directors|Category|Meetings"
    r"|Annual|Page|Corporate|Overview|Statutory|Financial|Report"
    # Role-only lines (may have trailing * ** or numbers)
    r"|(?:Chairman|Managing Director|Executive Director|Independent Director"
    r"|Non.Executive|Chief Executive|Chief Financial|Vice.Chairman|Whole.Time"
    r"|Non.Independent|and Chief|Officer)[^A-Z\n]*$"
    r"|\d+\s*$"
    r")",
    re.IGNORECASE,
)


def _extract_tabular_directors(text: str) -> list[dict]:
    """
    Extract from DIN-based governance/remuneration table.
    Handles multi-line names by joining lines before the DIN.

    Typical row formats:
      "Mr. Nusli N. Wadia, Chairman  00015731  7  Yes  3  Nil  4,500"
      "Mr. Nusli N. Wadia,\nChairman\n00015731 7 Yes..."
      "Nandan M. Nilekani (2) 00041245 Non-executive Chairman ..."
    """
    # Find governance table section
    sec_m = _GOVERNANCE_TABLE_RE.search(text)
    if not sec_m:
        sec_m = re.search(
            r"(?:Promoter|Executive|Independent) Directors?\s*\n",
            text, re.IGNORECASE,
        )
    if not sec_m:
        return []

    section = text[sec_m.start(): sec_m.start() + 20000]
    directors = []
    seen_dins = set()

    for din_m in _DIN_RE.finditer(section):
        din = din_m.group(1)
        if din in seen_dins:
            continue

        # ── Strategy A: name on same line as DIN (inline row) ──
        # e.g. "Mr. Avijit Deb 00047233 7 Yes Nil Nil Nil"
        line_start = section.rfind("\n", 0, din_m.start()) + 1
        same_line = section[line_start: din_m.start()].strip()
        same_line = re.sub(r"\s*\(\d+\)\s*$", "", same_line).strip()
        # Strip trailing data values like "7 Yes 4 Member-4 16,202"
        same_line_clean = re.sub(r"\s+\d[\d,\.]*\s*$", "", same_line).strip()

        inline_name = ""
        if same_line_clean and len(same_line_clean) > 3:
            # Looks like a name if it starts with title or capital word
            if re.match(r"^(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+[A-Z]", same_line_clean, re.I) or \
               re.match(r"^[A-Z][a-z]+ [A-Z]", same_line_clean):
                # Strip trailing role suffix
                candidate = re.sub(
                    r",?\s*(?:Chairman|Managing Director|Executive Director|Independent Director|"
                    r"Non.Executive|Vice.Chairman|CFO|CEO|COO|CTO|Secretary|Officer).*$",
                    "", same_line_clean, flags=re.I,
                ).strip()
                if _is_valid_name(candidate):
                    inline_name = candidate

        # ── Strategy B: name on lines before DIN (multi-line cell) ──
        before_text = section[max(0, din_m.start() - 500): line_start]
        before_lines = [ln.strip() for ln in before_text.split("\n") if ln.strip()]

        # name_parts stored in natural order (insert at front when walking backwards)
        name_parts = []
        for lb in reversed(before_lines):
            if _SKIP_LINE_RE.match(lb):
                if name_parts:
                    break
                continue
            lb_clean = re.sub(r"\s*\(\d+\)\s*$", "", lb).strip()
            lb_clean = lb_clean.rstrip(",").strip()
            if "," in lb_clean:
                before_comma = lb_clean.split(",")[0].strip()
                if re.match(r"^(?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+[A-Z]", before_comma, re.I) or \
                   re.match(r"^[A-Z][a-z]+ [A-Z]", before_comma):
                    lb_clean = before_comma
            if not lb_clean or len(lb_clean) < 2:
                if name_parts:
                    break
                continue
            if name_parts and re.match(r"^[\d\s]+$", lb_clean):
                break
            if re.match(
                r"^(?:Chairman|Managing Director|Executive Director|Independent Director|"
                r"Non.Executive|Chief Executive|Chief Financial|Vice.Chairman|"
                r"Whole.Time|Non.Independent|Promoter|Director)[^A-Z]*$",
                lb_clean, re.I,
            ):
                if name_parts:
                    break
                continue
            # Insert at front to keep natural order
            name_parts.insert(0, lb_clean)
            combined = " ".join(name_parts)
            wc = len(combined.split())
            if wc >= 2 and not combined.rstrip().endswith("-"):
                if wc >= 4:
                    break

        # Build multiline_name — parts already in natural order
        multiline_name = ""
        if name_parts:
            joined = []
            for part in name_parts:
                if joined and joined[-1].endswith("-"):
                    joined[-1] = joined[-1] + part
                else:
                    joined.append(part)
            multiline_name = _clean(" ".join(joined))
            multiline_name = re.sub(r"\s*\(\d+\)\s*$", "", multiline_name).strip()
            multiline_name = re.sub(
                r",?\s*(?:Chairman|Managing Director|Executive Director|Independent Director|"
                r"Non.Executive|Vice.Chairman|CFO|CEO|COO|CTO|Secretary|Officer).*$",
                "", multiline_name, flags=re.I,
            ).strip()

        # Prefer inline name; fall back to multiline
        name = inline_name or multiline_name
        if not name:
            continue
        # Final cleanup
        name = re.sub(r"\s*\(\d+\)\s*$", "", name).strip()
        name = re.sub(r"^(?:Nil|Yes|No|\d[\d,\.]*)\s+", "", name, flags=re.I).strip()

        if not _is_valid_name(name) or name in {d["name"] for d in directors}:
            continue

        # ── Title: from lines after DIN or same DIN line ──
        after_text = section[din_m.end(): din_m.end() + 500]
        # DIN line itself may contain title: "00015731 7 Yes ... Non-executive Chairman"
        din_line_rest = after_text.split("\n")[0] if after_text else ""
        title = ""
        if re.search(r"director|chairman|officer|ceo|md\b|cfo|secretary|vice|executive|independent", din_line_rest, re.I):
            # Extract the role words from the line
            role_m = re.search(
                r"((?:Non.Executive|Non.Independent|Executive|Independent|Managing|"
                r"Chief|Whole.Time|Chairman|Vice.Chairman)[^\d\n]{0,100})",
                din_line_rest, re.I,
            )
            if role_m:
                title = _clean(role_m.group(1)[:100])
        if not title:
            for la in after_text.split("\n")[1:5]:
                la = la.strip()
                if re.search(r"director|chairman|officer|ceo|md\b|cfo|secretary|vice|executive", la, re.I):
                    title = _clean(la[:100])
                    break

        ctx_start = max(0, din_m.start() - 200)
        ctx = section[ctx_start: din_m.end() + 2000]
        appt_m = _APPT_DATE_RE.search(ctx)
        appt_date = _clean(appt_m.group(1)) if appt_m else ""

        # Determine role from: title, section category header, or before/after context
        # Find the nearest category header before this DIN in the section
        cat_header = ""
        for hdr in re.finditer(
            r"(?:Promoter and Non.Executive Directors|Executive Directors|"
            r"Independent Directors|Non.Executive Directors|Non.Independent Directors|"
            r"Key Managerial Personnel)",
            before_text, re.IGNORECASE,
        ):
            cat_header = hdr.group(0)  # last match = closest header

        # Build role context from name + explicit title + category header only
        # Do NOT include after_text (attendance data rows may contain "Chairman" column header)
        role_ctx = f"{name} {title} {cat_header}"
        roles = _classify_role(role_ctx)
        comms = _classify_committees(ctx)

        seen_dins.add(din)
        directors.append({
            "s_no":                len(directors) + 1,
            "name":                name,
            "din":                 din,
            "years_as_director":   "",
            "date_of_appointment": appt_date,
            "title":               title,
            **roles,
            **comms,
            "other_companies":     "0",
        })

    return directors


# ── Format B: Profile-card narrative ──────────────────────────────────────────
# "Date of appointment: January 02, 2018"
# "Tenure on Board: 5.6 years"

_PROFILE_SECTION_RE = re.compile(
    r"(?:Board of Directors|Composition of (?:the )?Board|Board Composition)",
    re.IGNORECASE,
)

_DATE_APPT_RE = re.compile(
    r"[Dd]ate of (?:first )?[Aa]ppointment\s*[:\-]?\s*"
    r"((?:January|February|March|April|May|June|July|August|September|October|November|December)"
    r"\s+\d{1,2},?\s+\d{4}|\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})",
    re.IGNORECASE,
)

_TENURE_RE = re.compile(r"[Tt]enure on [Bb]oard\s*[:\-]?\s*([\d\.]+\s+years?)", re.IGNORECASE)

_TITLE_LINE_RE = re.compile(
    r"^((?:Chairman|Chief|Managing|Executive|Independent|Non.Executive|Non.Independent|"
    r"Lead|Whole.Time|Additional|Nominee|Promoter)[^\n]{0,150})$",
    re.MULTILINE | re.IGNORECASE,
)


def _extract_profile_directors(text: str) -> list[dict]:
    """Extract from profile-card style narrative."""
    m = _PROFILE_SECTION_RE.search(text)
    search_text = text[m.start(): m.start() + 60000] if m else text

    directors = []
    seen = set()

    for da_m in _DATE_APPT_RE.finditer(search_text):
        appt_date = _clean(da_m.group(1))
        ctx_start = max(0, da_m.start() - 600)
        ctx = search_text[ctx_start: da_m.end() + 1000]

        name = ""
        lines = ctx.split("\n")
        for ln in reversed(lines[:-5]):
            ln = ln.strip()
            if not ln or len(ln) < 4 or len(ln) > 80:
                continue
            if re.match(r"^[\d\s\.\-]+$", ln):
                continue
            if re.match(r"^(?:Read full|Infosys|Date|Tenure|Age|Committee|Member|Chairperson|Areas|Board)", ln, re.I):
                continue
            words = ln.split()
            if len(words) >= 1 and re.match(r"[A-Z][a-z]+", words[0]):
                name = _clean(ln)
                break

        if not name or name in seen or not _is_valid_name(name):
            continue

        title = ""
        m_title = _TITLE_LINE_RE.search(ctx)
        if m_title:
            title = _clean(m_title.group(1))

        tenure_m = _TENURE_RE.search(ctx)
        tenure = _clean(tenure_m.group(1)) if tenure_m else ""

        comms = _classify_committees(ctx)
        roles = _classify_role(f"{name} {title} {ctx[:300]}")

        seen.add(name)
        directors.append({
            "s_no":                len(directors) + 1,
            "name":                name,
            "din":                 "",
            "years_as_director":   tenure,
            "date_of_appointment": appt_date,
            "title":               title,
            **roles,
            **comms,
            "other_companies":     "0",
        })

    return directors


# ── Format C: Annexure brief profile blocks ───────────────────────────────────

_ANNEXURE_NAME_RE  = re.compile(r"[Nn]ame of (?:the )?[Dd]irector\s*[:\-]\s*(.{4,80}?)(?:\n|$)")
_ANNEXURE_APPT_RE  = re.compile(r"[Dd]ate of [Aa]ppointment\s*[:\-]\s*(.{5,60}?)(?:\n|$)")
_ANNEXURE_DIN_RE   = re.compile(r"DIN\s*[:\-]\s*(\d{6,8})")
_ANNEXURE_CAT_RE   = re.compile(r"[Cc]ategory\s*[:\-]\s*(.{5,150}?)(?:\n|$)")


def _extract_annexure_directors(text: str) -> list[dict]:
    """Extract from structured annexure blocks."""
    directors = []
    seen = set()

    for name_m in _ANNEXURE_NAME_RE.finditer(text):
        name = _clean(name_m.group(1))
        if not name or name in seen or len(name) < 3:
            continue

        ctx = text[name_m.start(): name_m.start() + 1500]

        appt_m = _ANNEXURE_APPT_RE.search(ctx)
        din_m  = _ANNEXURE_DIN_RE.search(ctx)
        cat_m  = _ANNEXURE_CAT_RE.search(ctx)

        appt_date = _clean(appt_m.group(1)) if appt_m else ""
        din        = din_m.group(1) if din_m else ""
        category   = _clean(cat_m.group(1)) if cat_m else ""

        roles = _classify_role(f"{name} {category}")
        comms = _classify_committees(ctx)

        seen.add(name)
        directors.append({
            "s_no":                len(directors) + 1,
            "name":                name,
            "din":                 din,
            "years_as_director":   "",
            "date_of_appointment": appt_date,
            "title":               category,
            **roles,
            **comms,
            "other_companies":     "0",
        })

    return directors


# ── Format D: Resolution text with inline DIN ─────────────────────────────────

_RES_DIR_RE = re.compile(
    r"((?:Mr|Ms|Mrs|Dr|Shri|Smt)\.?\s+)?([A-Z][a-zA-Z\s\.\-]{4,60}?)"
    r"\s+\(DIN\s*:\s*(\d{6,8})\)"
    r"([^\n]{0,300})",
    re.IGNORECASE,
)

_RES_NAME_NOISE_RE = re.compile(
    r"\b(?:is hereby|pursuant|resolved|approval|accorded|be and|hereby|"
    r"Appointment of|Re-?appointment|Reappointment|Approval|"
    r"Infosys|Annual Report|Notice|Board of Directors|Committee)\b",
    re.IGNORECASE,
)


def _extract_resolution_directors(text: str) -> list[dict]:
    """Extract directors mentioned in resolution text with DIN."""
    directors = []
    seen_dins = set()

    for m in _RES_DIR_RE.finditer(text):
        prefix   = (m.group(1) or "").strip()
        raw_name = _clean(m.group(2).strip())
        din      = m.group(3)
        desc     = m.group(4)

        name = _clean((prefix + " " + raw_name).strip()) if prefix else raw_name

        if din in seen_dins or not name or len(name) < 4:
            continue
        if _RES_NAME_NOISE_RE.search(name):
            continue
        if len(name.split()) > 6:
            continue
        if not re.match(r"^[A-Z]", name):
            continue
        # Must have title prefix OR two capitalised words
        if not prefix and not re.match(r"^[A-Z][a-z]+ [A-Z]", name):
            continue

        ctx_start = max(0, m.start() - 200)
        ctx = text[ctx_start: m.end() + 800]

        appt_m = re.search(
            r"(?:effect from|appointed (?:w\.?e\.?f\.?|on|from|with effect from))\s+"
            r"((?:\d{1,2}(?:st|nd|rd|th)?\s+)?(?:January|February|March|April|May|June|July|"
            r"August|September|October|November|December)\s+\d{1,2},?\s*\d{4}"
            r"|\d{1,2}[/\-]\d{2,4})",
            ctx, re.IGNORECASE,
        )
        appt_date = _clean(appt_m.group(1)) if appt_m else ""

        roles = _classify_role(f"{name} {desc}")
        comms = _classify_committees(ctx)

        seen_dins.add(din)
        directors.append({
            "s_no":                len(directors) + 1,
            "name":                name,
            "din":                 din,
            "years_as_director":   "",
            "date_of_appointment": appt_date,
            "title":               _clean(desc[:100]),
            **roles,
            **comms,
            "other_companies":     "0",
        })

    return directors


# ── Format E: InGovern/structured table extracted via pdfplumber ──────────────
# Table has columns like: S.No | Name | Years as Director | Date of Appointment |
#   Chairman | MD | Executive | Non-Executive | Independent | Audit | NRC | Stakeholder
# Cells contain "✓", "c" (chairman), "vc" (vice-chairman) or empty

_BOD_TABLE_HEADER_KEYWORDS = {
    "name", "years as director", "years", "date of appointment", "appointment",
    "chairman", "md", "executive", "non-executive", "non - executive",
    "independent", "audit", "risk", "stakeholder", "nomination", "nrc", "s no", "s.no",
}

_COMMITTEE_COL_KEYWORDS = {
    "audit", "risk", "stakeholder", "nomination", "nrc", "board governance",
    "compliance", "remuneration",
}

_STATUS_COL_KEYWORDS = {
    "chairman", "md", "executive", "non-executive", "non - executive", "independent",
}

_CHECKMARK_VALUES = {"✓", "✗", "v", "x", "•", "√", "y", "yes"}
_CHAIRMAN_VALUES  = {"c", "c ", " c"}
_VC_VALUES        = {"vc", "v.c", "vc "}


def _is_checkmark(val: str) -> bool:
    v = val.strip().lower()
    return v in _CHECKMARK_VALUES or v == "✓"


def _is_chairman_mark(val: str) -> bool:
    return val.strip().lower() in _CHAIRMAN_VALUES


def _is_vc_mark(val: str) -> bool:
    return val.strip().lower() in _VC_VALUES


def _col_type(header: str) -> str:
    """Return canonical column type from header text."""
    h = header.lower().strip()
    if any(k in h for k in ["s no", "s.no", "sl", "sr"]):
        return "sno"
    if "name" in h:
        return "name"
    if "years" in h:
        return "years"
    if "date" in h and "appoint" in h:
        return "date_of_appointment"
    if h in {"chairman", "chair"}:
        return "chairman"
    if h == "md" or "managing director" in h:
        return "md"
    if "non" in h and "exec" in h:
        return "non_executive"
    if "exec" in h:
        return "executive"
    if "independent" in h:
        return "independent"
    if "audit" in h:
        return "audit"
    if "risk" in h or "compliance" in h:
        return "risk"
    if "stakeholder" in h or "grievance" in h:
        return "stakeholder"
    if "nomination" in h or "nrc" in h or "remuneration" in h or "governance" in h:
        return "nomination_remuneration"
    if "csr" in h or "corporate social" in h:
        return "csr"
    return "other"


def _is_board_table(headers: list) -> bool:
    """Return True if this table looks like a board of directors table."""
    if not headers:
        return False
    joined = " ".join(str(h).lower() for h in headers)
    matches = sum(1 for kw in _BOD_TABLE_HEADER_KEYWORDS if kw in joined)
    return matches >= 3


def _extract_ingovern_table_directors(pdf_path: str) -> list:
    """
    Extract directors from a structured InGovern-style board table using pdfplumber.
    Handles ✓, c, vc checkmarks in status/committee columns.
    Works for any company — purely column-header driven.
    Only scans first 20 pages to avoid hanging on large PDFs.
    """
    try:
        from pdf_processing.extract_pdf import extract_pdf_tables
    except Exception:
        return []

    tables = extract_pdf_tables(pdf_path, max_pages=20)
    directors = []
    seen = set()

    for tbl in tables:
        raw = tbl.get("raw", [])
        if len(raw) < 3:
            continue

        # Find the header row — may be row 0 or row 1 if row 0 is a merged super-header
        header_row_idx = None
        col_map = {}  # col_index → col_type

        for row_idx in range(min(3, len(raw))):
            row = raw[row_idx]
            if _is_board_table(row):
                header_row_idx = row_idx
                for ci, cell in enumerate(row):
                    ct = _col_type(str(cell))
                    if ct != "other":
                        col_map[ci] = ct
                break

        if header_row_idx is None or "name" not in col_map.values():
            continue

        name_col = next((ci for ci, ct in col_map.items() if ct == "name"), None)
        if name_col is None:
            continue

        for row in raw[header_row_idx + 1:]:
            if not row or len(row) <= name_col:
                continue

            name_raw = str(row[name_col]).strip()
            if not name_raw or len(name_raw) < 3:
                continue
            if re.match(r"^[\d\.\s]+$", name_raw):
                continue
            # Skip header-like rows repeated inside table
            if any(kw in name_raw.lower() for kw in ["name", "director", "member", "chairman", "status"]):
                continue

            name = _clean(name_raw)
            if not _is_valid_name(name):
                continue
            nk = _name_key(name)
            if nk in seen:
                continue

            # Extract fields from mapped columns
            def get(ct):
                for ci, c in col_map.items():
                    if c == ct and ci < len(row):
                        return str(row[ci]).strip()
                return ""

            years_raw = get("years")
            # years may be like "55" or "5 5" (split across sub-columns) — take first number
            years_m = re.search(r"\d+", years_raw)
            years = years_m.group(0) if years_m else ""

            date_raw = get("date_of_appointment")
            # date may be just a year like "1968" or "2015"
            date_of_appointment = _clean(date_raw) if date_raw else ""

            # Status columns — check for checkmarks / c / vc
            def is_marked(ct):
                v = get(ct)
                return bool(v and (_is_checkmark(v) or _is_chairman_mark(v) or _is_vc_mark(v)))

            def mark_level(ct):
                v = get(ct)
                if not v:
                    return False
                if _is_chairman_mark(v):
                    return "Chairman"
                if _is_vc_mark(v):
                    return "Vice Chairman"
                if _is_checkmark(v):
                    return True
                return False

            chairman_val = mark_level("chairman")
            md_val       = is_marked("md")
            exec_val     = is_marked("executive")
            nonexec_val  = is_marked("non_executive")
            indep_val    = is_marked("independent")

            audit_val    = mark_level("audit")
            risk_val     = mark_level("risk")
            nrc_val      = mark_level("nomination_remuneration")
            stake_val    = mark_level("stakeholder")
            csr_val      = mark_level("csr")

            seen.add(nk)
            directors.append({
                "s_no":                len(directors) + 1,
                "name":                name,
                "din":                 "",
                "years_as_director":   f"{years} years" if years else "",
                "date_of_appointment": date_of_appointment,
                "title":               "",
                "chairman":            chairman_val,
                "md_ceo":              md_val,
                "executive":           exec_val,
                "non_executive":       nonexec_val,
                "independent":         indep_val,
                "promoter":            False,
                "audit":               audit_val,
                "nomination_remuneration": nrc_val,
                "stakeholder":         stake_val,
                "risk":                risk_val,
                "csr":                 csr_val,
                "other_companies":     "0",
            })

    return directors


# ── Tenure from appointment date ──────────────────────────────────────────────

def _compute_tenure(appt_date: str) -> str:
    """Compute approximate years on board from appointment date string."""
    if not appt_date:
        return ""
    # Extract year
    m = re.search(r"\b(19|20)\d{2}\b", appt_date)
    if not m:
        return ""
    try:
        from datetime import date
        year = int(m.group(0))
        # Try to get month too
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
        }
        month = 1
        for abbr, num in months.items():
            if abbr in appt_date.lower():
                month = num
                break
        today = date.today()
        appt = date(year, month, 1)
        delta = today - appt
        years = round(delta.days / 365.25, 1)
        return f"{years} years"
    except Exception:
        return ""


# ── Merge & deduplicate ───────────────────────────────────────────────────────

def _merge_directors(lists: list[list[dict]]) -> list[dict]:
    """Merge multiple director lists, deduplicating by name similarity."""
    merged: dict[str, dict] = {}

    for lst in lists:
        for d in lst:
            key = _name_key(d["name"])
            if not key or len(key) < 3:
                continue
            if key in merged:
                existing = merged[key]
                for field in ["din", "years_as_director", "date_of_appointment", "title"]:
                    if not existing.get(field) and d.get(field):
                        existing[field] = d[field]
                for field in ["chairman", "md_ceo", "executive", "non_executive",
                               "independent", "promoter", "audit", "nomination_remuneration",
                               "stakeholder", "risk", "csr"]:
                    if d.get(field) and not existing.get(field):
                        existing[field] = d[field]
            else:
                merged[key] = dict(d)

    result = list(merged.values())
    for i, d in enumerate(result, 1):
        d["s_no"] = i
        # Compute tenure if missing
        if not d.get("years_as_director") and d.get("date_of_appointment"):
            d["years_as_director"] = _compute_tenure(d["date_of_appointment"])
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def extract_board_of_directors(text: str, pdf_path: str = "") -> list:
    """
    Extract board of directors from any AGM/EGM/InGovern PDF.
    Tries multiple extraction strategies and merges results.
    Never raises, never hardcodes company-specific values.
    """
    try:
        # Format E: structured table extraction (InGovern report / any clean table PDF)
        ingovern_dirs = _extract_ingovern_table_directors(pdf_path) if pdf_path else []

        profile_dirs    = _extract_profile_directors(text)
        annexure_dirs   = _extract_annexure_directors(text)
        resolution_dirs = _extract_resolution_directors(text)
        tabular_dirs    = _extract_tabular_directors(text)

        # Priority: ingovern table > profile > annexure > resolution > tabular
        merged = _merge_directors([ingovern_dirs, profile_dirs, annexure_dirs, resolution_dirs, tabular_dirs])

        # Filter out clearly wrong entries
        merged = [
            d for d in merged
            if len(d["name"]) > 3
            and _is_valid_name(d["name"])
            and not re.match(r"^(?:Board|Committee|Company|Annual|Report|Note|The )", d["name"], re.I)
        ]

        return merged
    except Exception:
        return []


def extract_attendance_table(text: str) -> list[dict]:
    """Parse director attendance table if present."""
    try:
        m = re.search(r"[Aa]ttendance of [Dd]irectors?", text, re.IGNORECASE)
        if not m:
            return []

        section = text[m.start(): m.start() + 5000]
        results = []
        row_pat = re.compile(
            r"((?:Mr\.|Ms\.|Mrs\.|Dr\.|Shri |Smt )?[A-Z][a-zA-Z\s\.\-]{4,50?})"
            r"\s+(Yes|No)\s+(\d+)\s+(\d+)\s+(\d+)%?",
            re.IGNORECASE,
        )
        seen = set()
        for rm in row_pat.finditer(section):
            name = _clean(rm.group(1))
            if name in seen:
                continue
            seen.add(name)
            results.append({
                "name":           name,
                "agm_attended":   rm.group(2).strip().lower() == "yes",
                "board_held":     int(rm.group(3)),
                "board_attended": int(rm.group(4)),
                "board_pct":      int(rm.group(5)),
            })
        return results
    except Exception:
        return []
