"""
One-time seed script: parse all past InGovern PDF reports and load them into
the Supabase knowledge base (rag_resolutions + writing_style_examples).

Usage:
    python scripts/seed_knowledge_base.py

Re-runs are safe: a flag file (storage/seed_done.flag) prevents re-processing
already-seeded PDFs.  Delete the flag to force a full re-seed.

PDF layout expected (per page after the cover):
    Resolution No. X: <title>
    Type of Resolution: Ordinary | Special
    Management Recommendation : FOR | AGAINST | ABSTAIN
    InGovern Recommendation : FOR | FOR* | AGAINST
    <body text — paragraphs, numbered observations, closing sentence>
"""

import os
import re
import sys
import json
import time

# ── Bootstrap path so we can import project modules ──────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import pdfplumber
from database.rag_store import store_resolution_rag, store_style_example

# ── Constants ─────────────────────────────────────────────────────────────────

PAST_REPORTS_DIR = os.path.join("storage", "past_reports")
FLAG_FILE        = os.path.join("storage", "seed_done.flag")
PROCESSED_LOG    = os.path.join("storage", "seed_processed.json")

# Map filename keywords → industry (best-effort)
INDUSTRY_MAP = {
    "WIPRO": "Technology", "INFY": "Technology", "LTIM": "Technology",
    "HDFCBANK": "Banking", "HINDUNILVR": "FMCG", "ASIANPAINT": "Paints",
    "EICHERMOT": "Automobile", "RELIANCE": "Conglomerate", "RIL": "Conglomerate",
    "TATACONSUM": "FMCG", "ZOMATO": "Technology", "NYKAA": "Retail",
    "LUPIN": "Pharma", "MRF": "Tyres", "PAYTM": "Fintech",
    "SIEMENS": "Engineering", "ESCORTS": "Engineering",
    "TV18BRDCST": "Media", "NETWORK18": "Media", "ZEEL": "Media",
    "SANGHIIND": "Cement", "SANGHIND": "Cement", "UFLEX": "Packaging",
    "MCDOWELL": "Beverages",
}

# Canonical resolution type classifier (keyword → type)
RES_TYPE_KEYWORDS = [
    ("Director Reappointment",   ["re-appoint", "reappoint", "retiring by rotation"]),
    ("Director Appointment",     ["appoint.*director", "appointment.*director"]),
    ("Auditor Appointment",      ["appoint.*auditor", "ratif.*auditor", "statutory auditor"]),
    ("Remuneration",             ["remuneration", "commission", "managerial remuneration", "salary"]),
    ("ESOP",                     ["esop", "esos", "employee stock", "stock option", "psu", "rsu"]),
    ("Related Party Transaction",["related party", "rpt", "material related"]),
    ("Borrowing",                ["borrow", "issue.*debenture", "ncd", "bonds"]),
    ("Capital Raise",            ["issue.*shares", "preferential allotment", "qip", "rights issue"]),
    ("Dividend",                 ["dividend", "interim dividend"]),
    ("Financial Statements",     ["financial statement", "accounts", "balance sheet"]),
    ("Charter Amendment",        ["memorandum", "articles of association", "alteration"]),
    ("Buyback",                  ["buyback", "buy-back"]),
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _classify_resolution_type(title: str) -> str:
    t = title.lower()
    for rtype, keywords in RES_TYPE_KEYWORDS:
        for kw in keywords:
            if re.search(kw, t):
                return rtype
    return "Other"


def _normalise_rec(raw: str) -> str:
    r = raw.strip().upper()
    if "AGAINST" in r:
        return "AGAINST"
    if "*" in r or "FOR*" in r:
        return "FOR*"
    if "FOR" in r:
        return "FOR"
    if "ABSTAIN" in r:
        return "ABSTAIN"
    return "FOR"


def _parse_filename(filename: str) -> dict:
    """
    Extract ticker, notice_type, date, and FY from filename like:
      WIPRO AGM 18072024 InGovern Vote Recommendations.pdf
    """
    base = os.path.splitext(filename)[0]
    # Remove trailing boilerplate
    base = re.sub(r"InGovern Vote Recommendations.*", "", base, flags=re.IGNORECASE).strip()
    parts = base.split()
    ticker       = parts[0] if parts else "UNKNOWN"
    notice_type  = parts[1].upper() if len(parts) > 1 else "AGM"
    if notice_type not in ("AGM", "EGM", "PB"):
        notice_type = "AGM"
    if notice_type == "PB":
        notice_type = "Postal Ballot"
    industry = next((v for k, v in INDUSTRY_MAP.items() if k in ticker.upper()), "Other")
    return {"ticker": ticker, "notice_type": notice_type, "industry": industry}


def _extract_fy_from_path(filepath: str) -> str:
    """Extract FY from parent folder name like 'FY 24-25 Recos'."""
    parent = os.path.basename(os.path.dirname(filepath))
    m = re.search(r"(\d{2})-(\d{2})", parent)
    if m:
        return f"20{m.group(1)}-{m.group(2)}"
    return "Unknown"


def _extract_company_name_from_pdf(pages_text: list[str]) -> str:
    """Page 1 has the company name in ALLCAPS before 'VOTE RECOMMENDATIONS'."""
    cover = pages_text[0] if pages_text else ""
    for line in cover.splitlines():
        line = line.strip()
        if line and line.isupper() and len(line) > 5 and "INGOVERN" not in line and "VOTE" not in line:
            return line.title()
    return "Unknown"


def _split_into_resolution_blocks(pages_text: list[str]) -> list[str]:
    """
    Concatenate all page text (skipping cover + board pages) then split on
    'Resolution No. X:' boundaries.
    """
    full_text = "\n".join(pages_text)
    # Split on resolution headers
    parts = re.split(r"(?=Resolution No\.\s*\d+\s*:)", full_text, flags=re.IGNORECASE)
    blocks = [p.strip() for p in parts if re.match(r"Resolution No\.", p.strip(), re.IGNORECASE)]
    return blocks


def _parse_resolution_block(block: str) -> dict | None:
    """
    Parse a single resolution block into structured dict.
    Returns None if the block is malformed.
    """
    # Title
    title_m = re.match(r"Resolution No\.\s*(\d+)\s*:\s*(.+)", block, re.IGNORECASE)
    if not title_m:
        return None
    res_no = int(title_m.group(1))
    title  = title_m.group(2).strip().replace("\n", " ")

    # Type
    type_m = re.search(r"Type of Resolution\s*:\s*(Ordinary|Special)", block, re.IGNORECASE)
    res_type_raw = type_m.group(1).strip() if type_m else "Ordinary"

    # Management rec
    mgmt_m = re.search(r"Management Recommendation\s*:\s*(FOR\*?|AGAINST|ABSTAIN)", block, re.IGNORECASE)
    mgmt_rec = _normalise_rec(mgmt_m.group(1)) if mgmt_m else "FOR"

    # InGovern rec
    ig_m = re.search(r"InGovern Recommendation\s*:\s*(FOR\*?|AGAINST|ABSTAIN)", block, re.IGNORECASE)
    ig_rec = _normalise_rec(ig_m.group(1)) if ig_m else "FOR"

    # Body text — everything after the header lines
    header_end = 0
    for pat in [
        r"InGovern Recommendation\s*:\s*\S+",
        r"Management Recommendation\s*:\s*\S+",
        r"Type of Resolution\s*:\s*\S+",
    ]:
        m = re.search(pat, block, re.IGNORECASE)
        if m:
            header_end = max(header_end, m.end())

    body = block[header_end:].strip() if header_end else block
    # Strip page footers
    body = re.sub(r"InGovern \d{4}-\d{4}\s*Pag e \| \d+", "", body)
    body = re.sub(r"www\.ingovern\.com.*", "", body)
    body = body.strip()

    # Numbered concerns
    concerns = re.findall(r"(?:^|\n)\s*(\d+\)\s*.+?)(?=\n\s*\d+\)|\Z)", body, re.DOTALL)
    concerns = [c.strip().replace("\n", " ") for c in concerns]

    # Closing recommendation sentence (last sentence mentioning vote)
    closing_m = re.search(
        r"((?:we recommend|shareholders (?:are )?(?:therefore )?recommended)[^.]+\.)",
        body, re.IGNORECASE | re.DOTALL
    )
    closing = closing_m.group(1).strip().replace("\n", " ") if closing_m else ""

    return {
        "resolution_number":         res_no,
        "title":                     title,
        "resolution_type_raw":       res_type_raw,
        "management_recommendation": mgmt_rec,
        "ingovern_recommendation":   ig_rec,
        "resolution_type":           _classify_resolution_type(title),
        "body_text":                 body[:6000],
        "governance_concerns":       concerns,
        "closing_recommendation":    closing,
    }


def _extract_text_from_pdf(pdf_path: str) -> list[str]:
    """Return list of page texts, replacing encoding errors with '?'."""
    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                # Sanitise — replace non-ASCII chars that cause encode errors
                text = text.encode("ascii", "replace").decode("ascii")
                pages.append(text)
    except Exception as e:
        print(f"    [WARN] Could not open PDF: {e}")
    return pages


# ── Main ingestion loop ───────────────────────────────────────────────────────

def seed():
    # Load already-processed list
    processed = set()
    if os.path.exists(PROCESSED_LOG):
        with open(PROCESSED_LOG, "r") as f:
            processed = set(json.load(f))

    # Collect all PDFs
    pdf_files = []
    for root, _, files in os.walk(PAST_REPORTS_DIR):
        for fname in files:
            if fname.lower().endswith(".pdf"):
                pdf_files.append(os.path.join(root, fname))

    print(f"Found {len(pdf_files)} PDFs. Already processed: {len(processed)}.")

    total_resolutions = 0
    total_style       = 0
    newly_processed   = []

    for pdf_path in pdf_files:
        rel_path = os.path.relpath(pdf_path, PAST_REPORTS_DIR)
        if rel_path in processed:
            continue

        fname    = os.path.basename(pdf_path)
        meta     = _parse_filename(fname)
        fy       = _extract_fy_from_path(pdf_path)
        print(f"\nProcessing: {fname}")
        print(f"  Ticker={meta['ticker']}  NoticeType={meta['notice_type']}  FY={fy}  Industry={meta['industry']}")

        pages_text   = _extract_text_from_pdf(pdf_path)
        if not pages_text:
            print("  [SKIP] No text extracted.")
            continue

        company_name = _extract_company_name_from_pdf(pages_text)
        print(f"  Company: {company_name}")

        blocks = _split_into_resolution_blocks(pages_text)
        print(f"  Resolution blocks found: {len(blocks)}")

        for block in blocks:
            res = _parse_resolution_block(block)
            if not res:
                continue

            # Build commentary dict for RAG store
            commentary = {
                "ingovern_recommendation": res["ingovern_recommendation"],
                "management_recommendation": res["management_recommendation"],
                "governance_concerns":       res["governance_concerns"],
                "closing_recommendation":    res["closing_recommendation"],
                "body_text":                 res["body_text"],
            }

            # Store in rag_resolutions
            ok_rag = store_resolution_rag(
                company_name   = company_name,
                financial_year = fy,
                notice_type    = meta["notice_type"],
                industry       = meta["industry"],
                resolution     = {
                    "resolution_type":  res["resolution_type"],
                    "title":            res["title"],
                    "resolution_text":  res["body_text"],
                    "resolution_number": res["resolution_number"],
                },
                commentary     = commentary,
            )

            # Store in writing_style_examples — only the full body as a style exemplar
            if res["body_text"].strip():
                ok_style = store_style_example(
                    resolution_type = res["resolution_type"],
                    ingovern_rec    = res["ingovern_recommendation"],
                    example_text    = res["body_text"],
                )
                if ok_style:
                    total_style += 1

            if ok_rag:
                total_resolutions += 1

            print(f"    Res {res['resolution_number']}: {res['resolution_type']} | {res['ingovern_recommendation']} | RAG={'OK' if ok_rag else 'FAIL'}")

            # Rate-limit embedding calls
            time.sleep(0.3)

        newly_processed.append(rel_path)

    # Persist processed list
    all_processed = list(processed) + newly_processed
    with open(PROCESSED_LOG, "w") as f:
        json.dump(all_processed, f, indent=2)

    # Write flag if all done
    with open(FLAG_FILE, "w") as f:
        f.write(f"Seeded {total_resolutions} resolutions, {total_style} style examples.\n")

    print(f"\n=== SEED COMPLETE ===")
    print(f"Resolutions stored in rag_resolutions : {total_resolutions}")
    print(f"Style examples stored                 : {total_style}")
    print(f"PDFs processed this run               : {len(newly_processed)}")


if __name__ == "__main__":
    seed()
