"""
Resolution extractor — dynamic, works for any AGM/EGM/Postal Ballot PDF.

Real-world PDFs use several heading styles:
  "Item no. 1 - Adoption of financial statements"
  "ITEM NO. 1"
  "RESOLUTION NO. 1"
  "Agenda Item 1"
  "Item 1."
  "1. To receive, consider and adopt..."   (numbered list, no "Item" prefix)
  "3. Re-appointment of Mr. Varun Berry"   (special business numbered items)

Management recommendation is always derived from the resolution text itself
(board recommends FOR / AGAINST / abstain), never hardcoded.
"""

import re


# ── Agenda item header patterns ───────────────────────────────────────────────

# Pattern 1: Explicit "Item no." / "Resolution no." / "Agenda item" headers
_EXPLICIT_HEADER = re.compile(
    r"(?:^|\n)\s*"
    r"(?:ITEM\s*NO\.?\s*\d+|Item\s+[Nn]o\.?\s*\d+|ITEM\s+\d+|"
    r"RESOLUTION\s+NO\.?\s*\d+|AGENDA\s+ITEM\s*\d+|"
    r"Resolution\s+[Nn]o\.?\s*\d+|Item\s+\d+\s*[\.:\-])",
    re.IGNORECASE | re.MULTILINE,
)

# Pattern 2: Numbered list items ("1. To receive...", "3. Re-appointment of...")
# Only match at start of line, number 1-20, followed by "To " or proper noun or keyword
_NUMBERED_HEADER = re.compile(
    r"(?:^|\n)(\d{1,2})\.\s+"
    r"(?:To\s+|Re-?appointment|Appointment|Adoption|Declaration|Ratification|"
    r"Amendment|Alteration|Issue|Increase|Approval|Authorization|Authority|"
    r"Borrowing|Creation|Mortgage|Revision|Payment|[A-Z])",
    re.MULTILINE,
)

_ORDINARY = re.compile(r"\bORDINARY\s+RESOLUTION\b|\bType of Resolution:\s*Ordinary\b", re.IGNORECASE)
_SPECIAL  = re.compile(r"\bSPECIAL\s+RESOLUTION\b|\bType of Resolution:\s*Special\b",  re.IGNORECASE)

# InGovern report format: "Resolution No. 1: Title"
_INGOVERN_HEADER = re.compile(
    r"(?:^|\n)Resolution\s+No\.?\s*(\d{1,2})\s*[:\-]\s*(.{5,200}?)(?=\n)",
    re.MULTILINE | re.IGNORECASE,
)

# InGovern inline recommendations
_MGMT_REC_RE = re.compile(
    r"Management\s+Recommendation\s*[:\-]\s*(FOR|AGAINST|ABSTAIN)",
    re.IGNORECASE,
)
_INGOVERN_REC_RE = re.compile(
    r"InGovern\s+Recommendation\s*[:\-]\s*(FOR|AGAINST|ABSTAIN|FOR\*)",
    re.IGNORECASE,
)

_BOARD_REC_FOR = re.compile(
    r"(?:board (?:of directors )?recommends?|directors? recommends?|"
    r"board is of the opinion|committee recommends?|"
    r"board recommends? (?:the )?(?:members|shareholders))\s.*?\bfor\b",
    re.IGNORECASE | re.DOTALL,
)
_BOARD_REC_AGAINST = re.compile(
    r"(?:board recommends?|directors? recommends?)\s.*?\bagainst\b",
    re.IGNORECASE | re.DOTALL,
)
_BOARD_REC_ABSTAIN = re.compile(
    r"(?:board recommends?)\s.*?\babstain\b", re.IGNORECASE | re.DOTALL,
)

_ANNEXURE_RE = re.compile(r"\bANNEXURE[\s\-]*[A-Z0-9]*\b", re.IGNORECASE)

_PERSON_RE = re.compile(
    r"(?:Mr\.|Ms\.|Mrs\.|Dr\.|Shri\s+|Smt\.\s+)\s*([A-Z][A-Za-z\s\.\-]{2,60}?)"
    r"(?=\s*[\(,\n]|\s{2}|$)",
)


# ── Resolution type classifier ────────────────────────────────────────────────

def _classify(text: str) -> str:
    lower = text.lower()
    # "receive, consider and adopt" is the standard phrase for financial statement adoption
    if ("adopt" in lower or "adoption" in lower) and (
        "financial statement" in lower or "annual report" in lower
        or "audited" in lower or "balance sheet" in lower
    ):
        return "Adoption of Financial Statements"
    if "receive, consider and adopt" in lower:
        return "Adoption of Financial Statements"
    if "dividend" in lower:
        return "Dividend"
    # Check structural amendments BEFORE director checks (amendment blocks may mention nominee directors)
    if "alteration" in lower and "article" in lower:
        return "Articles Amendment"
    if "alteration" in lower and "memorandum" in lower:
        return "MOA Amendment"
    if "amendment" in lower and "article" in lower:
        return "Articles Amendment"
    if "amendment" in lower and "memorandum" in lower:
        return "MOA Amendment"
    if "re-appointment" in lower or "reappointment" in lower:
        if "retire by rotation" in lower:
            return "Director Reappointment (Rotation)"
        if "independent" in lower:
            return "Independent Director Reappointment"
        if "auditor" in lower:
            return "Auditor Reappointment"
        if "managing director" in lower or "executive director" in lower:
            return "Managing Director Reappointment"
        return "Director Reappointment"
    if "appointment" in lower:
        if "independent" in lower:
            return "Independent Director Appointment"
        if "auditor" in lower:
            return "Auditor Appointment"
        if "director" in lower:
            return "Director Appointment"
        return "Appointment"
    if "related party" in lower or " rpt " in lower:
        return "Related Party Transaction"
    if "borrow" in lower or "borrowing" in lower:
        return "Borrowing Powers"
    if "esop" in lower or "employee stock" in lower or "employee benefit" in lower:
        return "ESOP / Employee Benefits"
    if "remuneration" in lower and ("managing director" in lower or "whole-time" in lower or "executive director" in lower):
        return "Managerial Remuneration"
    if "remuneration" in lower and "cost auditor" in lower:
        return "Cost Auditor Remuneration"
    if "remuneration" in lower:
        return "Remuneration"
    if "merger" in lower or "amalgamation" in lower or "scheme" in lower:
        return "Merger / Amalgamation"
    if "buyback" in lower or "buy-back" in lower or "buy back" in lower:
        return "Buyback"
    if "issue" in lower and ("shares" in lower or "securities" in lower or "rights" in lower):
        return "Capital Raise / Issue"
    if "csr" in lower or "corporate social" in lower:
        return "CSR"
    if "auditor" in lower:
        return "Auditor"
    if "director" in lower:
        return "Director"
    return "Other"


def _extract_director_name(text: str) -> str:
    _STOP = {"in", "as", "at", "by", "of", "to", "for", "and", "the", "set", "who"}
    for match in _PERSON_RE.finditer(text):
        raw = match.group(1).strip().rstrip("*,;.")
        tokens = raw.split()
        if 2 <= len(tokens) <= 6 and tokens[-1].lower() not in _STOP:
            return raw
    return ""


def _extract_board_recommendation(block: str) -> str:
    """Derive management recommendation from resolution text."""
    # InGovern report format: "Management Recommendation : FOR"
    m = _MGMT_REC_RE.search(block)
    if m:
        return m.group(1).upper()
    if _BOARD_REC_AGAINST.search(block):
        return "AGAINST"
    if _BOARD_REC_ABSTAIN.search(block):
        return "ABSTAIN"
    if _BOARD_REC_FOR.search(block):
        return "FOR"
    if re.search(r"board (?:of directors )?recommends?", block, re.IGNORECASE):
        return "FOR"
    return ""


def _extract_ingovern_recommendation(block: str) -> str:
    """Extract InGovern's own recommendation from report format."""
    m = _INGOVERN_REC_RE.search(block)
    if m:
        return m.group(1).upper()
    return ""


def _extract_annexures(text: str) -> list:
    found = _ANNEXURE_RE.findall(text)
    seen, result = set(), []
    for a in found:
        key = a.upper().strip()
        if key not in seen:
            seen.add(key)
            result.append(a.strip())
    return result


def _extract_title(block: str, number: int = None) -> str:
    """Extract human-readable title from a resolution block."""
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    for line in lines[:8]:
        # Remove explicit item/resolution header prefix
        cleaned = re.sub(
            r"^(?:ITEM\s*NO\.?\s*\d+|Item\s+[Nn]o\.?\s*\d+|ITEM\s+\d+|"
            r"RESOLUTION\s+NO\.?\s*\d+|AGENDA\s+ITEM\s*\d+|"
            r"Item\s+\d+\s*[\.:\-])\s*[:\-]?\s*",
            "", line, flags=re.IGNORECASE,
        ).strip()
        # Remove numbered list prefix "3. " or "3 "
        if number is not None:
            cleaned = re.sub(rf"^{number}\.\s*", "", cleaned).strip()
        if len(cleaned) > 8:
            # Stop at "To consider and if thought fit" — that's preamble not title
            if re.match(r"^To consider", cleaned, re.I):
                continue
            return cleaned[:200].rstrip("-").strip()
    return lines[0][:200] if lines else "Unnamed Resolution"


# ── Cover-page summary table (InGovern pre-printed recs) ─────────────────────

_COVER_REC_RE = re.compile(
    r"(\d{1,2})\s+(.{10,200}?)\s+(Ordinary|Special)\s+(For\s*\*?|Against|FOR\s*\*?|AGAINST|FOR\*)",
    re.IGNORECASE | re.DOTALL,
)


def extract_cover_recommendations(text: str) -> dict:
    """Parse the cover-page proposals table for pre-printed InGovern recommendations."""
    cover = text[:5000]
    recs = {}
    for m in _COVER_REC_RE.finditer(cover):
        num = int(m.group(1))
        raw = m.group(4).strip().upper().replace(" ", "")
        if "AGAINST" in raw:
            rec = "AGAINST"
        elif "*" in raw:
            rec = "FOR*"
        else:
            rec = "FOR"
        recs[num] = rec
    return recs


# ── Block splitter ────────────────────────────────────────────────────────────

def _earliest_match_start(text: str, patterns: list) -> int | None:
    """Return the start offset of whichever pattern matches earliest in text, or None."""
    positions = []
    for pat in patterns:
        m = re.search(pat, text, re.MULTILINE)
        if m:
            positions.append(m.start())
    return min(positions) if positions else None


def _find_notice_start(text: str) -> int:
    """Find the start of the actual AGM/EGM notice (agenda) section."""
    pos = _earliest_match_start(text, [
        r"(?:^|\n)NOTICE IS HEREBY GIVEN",
        r"(?:^|\n)Notice is hereby given",
        r"(?:^|\n)ORDINARY BUSINESS\s*:",
        r"(?:^|\n)SPECIAL BUSINESS\s*:",
    ])
    return pos if pos is not None else 0


def _find_notice_end(text: str, start: int) -> int:
    """
    Find the end of the agenda section so we don't parse NOTES/Annexure items.
    The notice ends at whichever of "NOTES:" / "By Order of the Board" /
    "For and on behalf of the Board" / "Explanatory Statement" occurs FIRST
    after the agenda start — not whichever pattern is listed first.
    """
    search_text = text[start:]
    pos = _earliest_match_start(search_text, [
        r"(?:^|\n)By Order of the Board",
        r"(?:^|\n)For and on behalf of the Board",
        r"(?:^|\n)NOTES\s*:",
        r"(?:^|\n)Notes\s*:",
        r"(?:^|\n)Explanatory\s+Statement",
    ])
    return start + pos if pos is not None else len(text)


def _split_into_blocks(text: str) -> list:
    """
    Split PDF text into agenda-item blocks.
    Handles:
      - "Resolution No. X: Title" (InGovern report format)
      - "Item No. X" / "ITEM NO. X" style
      - Plain numbered "1. To receive..." style
    Returns list of (header_line, block_text, resolution_number).
    """
    # Try InGovern report format first ("Resolution No. 1: ...")
    ingovern_matches = list(_INGOVERN_HEADER.finditer(text))
    if ingovern_matches and len(ingovern_matches) >= 2:
        return _split_by_ingovern(text, ingovern_matches)

    notice_start = _find_notice_start(text)
    notice_end   = _find_notice_end(text, notice_start)
    notice_text  = text[notice_start:notice_end]

    # Try explicit headers (Item No. X style)
    explicit_matches = list(_EXPLICIT_HEADER.finditer(notice_text))
    if explicit_matches and len(explicit_matches) >= 2:
        return _split_by_matches(notice_text, explicit_matches)

    # Fall back to numbered list style
    numbered_matches = list(_NUMBERED_HEADER.finditer(notice_text))
    if numbered_matches:
        return _split_by_numbered(notice_text, numbered_matches)

    # Final fallback: try explicit in full text
    explicit_matches = list(_EXPLICIT_HEADER.finditer(text))
    if explicit_matches:
        return _split_by_matches(text, explicit_matches)

    return []


def _split_by_ingovern(text: str, matches: list) -> list:
    """Split InGovern report by 'Resolution No. X: Title' headers."""
    blocks = []
    for i, m in enumerate(matches):
        num   = int(m.group(1))
        title = m.group(2).strip()
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append((title, block, num))
    return blocks


def _split_by_matches(text: str, matches: list) -> list:
    """Split text into blocks using regex match positions."""
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        header = m.group(0).strip()
        if block:
            blocks.append((header, block, None))
    return blocks


def _split_by_numbered(text: str, matches: list) -> list:
    """Split text using numbered-list matches, extract number from group(1)."""
    blocks = []
    for i, m in enumerate(matches):
        num   = int(m.group(1))
        start = m.start()
        end   = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        if block:
            blocks.append((m.group(0).strip(), block, num))
    return blocks


# ── Explanatory statement extractor ──────────────────────────────────────────

def _extract_explanation(block: str) -> str:
    m = re.search(
        r"(?:Explanation|Explanatory Statement|Statement pursuant|Rationale)[:\s]*(.{20,3000})",
        block, re.IGNORECASE | re.DOTALL,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:2000]
    return ""


def extract_explanatory_statements(full_text: str) -> dict[int, str]:
    """
    Extract per-item explanatory statements from the formal
    'Explanatory Statement pursuant to Section 102' section of the notice.
    Returns {item_number: explanation_text}.
    """
    # Find the explanatory statement section
    expl_start = -1
    for pat in [
        r"Explanatory\s+Statement\s+pursuant\s+to\s+Section\s+102",
        r"EXPLANATORY\s+STATEMENT",
        r"Statement\s+pursuant\s+to\s+Section\s+102",
    ]:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            expl_start = m.start()
            break

    if expl_start < 0:
        return {}

    expl_text = full_text[expl_start:]

    # Split by "Item No. X:" markers
    item_pat = re.compile(
        r"(?:^|\n)\s*(?:ITEM|Item)\s+No\.?\s*(\d{1,2})\s*[:\-]",
        re.MULTILINE,
    )
    item_matches = list(item_pat.finditer(expl_text))
    if not item_matches:
        return {}

    result = {}
    for i, m in enumerate(item_matches):
        num   = int(m.group(1))
        start = m.end()
        end   = item_matches[i + 1].start() if i + 1 < len(item_matches) else len(expl_text)
        chunk = expl_text[start:end].strip()
        # Trim boilerplate "The Board recommends..." tail
        tail = re.search(
            r"The Board (?:of Directors )?recommends?.{0,200}for approval",
            chunk, re.IGNORECASE | re.DOTALL,
        )
        if tail:
            chunk = chunk[:tail.end()]
        result[num] = re.sub(r"\s+", " ", chunk).strip()[:5000]

    return result


# ── Main extractor ────────────────────────────────────────────────────────────

def extract_resolutions(text: str) -> list:
    """
    Parse a governance notice and return structured resolution objects.
    Works dynamically for AGM, EGM, Postal Ballot of any Indian listed company.
    """
    blocks = _split_into_blocks(text)
    cover_recs = extract_cover_recommendations(text)
    explanatory_map = extract_explanatory_statements(text)

    if not blocks:
        return [{
            "resolution_number":          1,
            "title":                      "Unstructured Notice",
            "resolution_type":            _classify(text),
            "ordinary_resolution":        bool(_ORDINARY.search(text)),
            "special_resolution":         bool(_SPECIAL.search(text)),
            "director_name":              _extract_director_name(text),
            "management_recommendation":  _extract_board_recommendation(text) or "FOR",
            "board_recommendation":       "",
            "annexures":                  _extract_annexures(text),
            "resolution_text":            text.strip()[:8000],
            "explanation":                explanatory_map.get(1, ""),
            "cover_ingovern_rec":         cover_recs.get(1, ""),
        }]

    results = []
    seen_titles: set[str] = set()
    res_num = 0

    for header, block, block_num in blocks:
        # For InGovern report blocks the header IS the title (already extracted)
        # For other formats, derive title from block text
        if header and len(header) > 8 and not re.match(
            r"^(?:ITEM\s*NO|Item\s+[Nn]o|RESOLUTION\s+NO|AGENDA\s+ITEM|\d+\.\s)",
            header, re.IGNORECASE,
        ):
            title = header.strip()[:200]
        else:
            title = _extract_title(block, number=block_num)

        # Normalise title for dedup
        title_key = re.sub(r"\s+", " ", title.lower().strip())[:80]
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)

        res_num += 1
        actual_num = block_num if block_num is not None else res_num
        mgmt_rec      = _extract_board_recommendation(block)
        ingovern_rec  = _extract_ingovern_recommendation(block)

        # Explanatory statement: prefer the dedicated section, fall back to inline
        expl = explanatory_map.get(actual_num, "") or _extract_explanation(block)

        results.append({
            "resolution_number":          res_num,
            "title":                      title,
            "resolution_type":            _classify(block),
            "ordinary_resolution":        bool(_ORDINARY.search(block)),
            "special_resolution":         bool(_SPECIAL.search(block)),
            "director_name":              _extract_director_name(block),
            "management_recommendation":  mgmt_rec or "FOR",
            "board_recommendation":       mgmt_rec,
            "ingovern_recommendation":    ingovern_rec,
            "annexures":                  _extract_annexures(block),
            "resolution_text":            block[:6000],
            "explanation":                expl,
            "cover_ingovern_rec":         cover_recs.get(actual_num, "") or ingovern_rec,
        })

    return results
