"""
populate_recommendation_report.py

Reads ALL PDFs from Supabase Storage bucket 'recommendation-reports'
(root + subfolders FY 22-23 Recos, FY 23-24 Recos, FY 24-25 Recos),
extracts ISIN, company name, and meeting date PER YEAR from each PDF,
then populates the recommendation_report table.

One row per company. Each year has its own PDF URL column and meeting date column.

RUN:
  python populate_recommendation_report.py            # populate all
  python populate_recommendation_report.py --dry-run  # preview only
"""

import os
import re
import sys
import tempfile

import pdfplumber
import requests

from database.supabase_client import get_client

DRY    = "--dry-run" in sys.argv
BUCKET = "recommendation-reports"

FOLDER_TO_FY = {
    "FY 22-23 Recos": "2022-23",
    "FY 23-24 Recos": "2023-24",
    "FY 24-25 Recos": "2024-25",
}
VALID_FYS = ["2022-23", "2023-24", "2024-25"]


def log(msg):
    print(("[dry-run] " if DRY else "") + msg)


def get_public_url(client, path):
    return client.storage.from_(BUCKET).get_public_url(path)


def list_all_files(client):
    """Returns list of {path, filename, financial_year}"""
    files = []
    # Root level
    try:
        for f in client.storage.from_(BUCKET).list():
            if f.get("id") is None:
                continue
            if not f["name"].lower().endswith(".pdf"):
                continue
            fy = guess_fy_from_filename(f["name"])
            files.append({"path": f["name"], "filename": f["name"], "financial_year": fy})
    except Exception as e:
        log(f"Error listing root: {e}")

    # Subfolders — FY from folder name takes priority
    for folder, fy in FOLDER_TO_FY.items():
        try:
            for f in client.storage.from_(BUCKET).list(folder):
                if f.get("id") is None:
                    continue
                if not f["name"].lower().endswith(".pdf"):
                    continue
                path = f"{folder}/{f['name']}"
                files.append({"path": path, "filename": f["name"], "financial_year": fy})
        except Exception as e:
            log(f"Error listing {folder}: {e}")

    return files


def guess_fy_from_filename(filename):
    m = re.search(r"\b(\d{2})(\d{2})(\d{4})\b", filename)
    if m:
        month = int(m.group(2))
        year  = int(m.group(3))
        if month >= 4:
            return f"{year}-{str(year + 1)[2:]}"
        else:
            return f"{year - 1}-{str(year)[2:]}"
    return None


def ticker_from_filename(filename):
    parts = filename.strip().split()
    return parts[0].upper() if parts else filename.upper()


SKIP_PREFIXES = (
    "corporate", "vote", "shareholder", "ingovern", "advisory",
    "proxy", "registered", "cin", "tel", "email", "www", "page",
    "confidential", "for", "to", "the", "this",
)


def extract_company_name(text):
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    for line in lines:
        if (len(line) >= 8 and line == line.upper()
                and not line.lower().startswith(SKIP_PREFIXES)
                and not re.match(r"^[\d\W]+$", line)):
            return line
    for line in lines:
        if len(line) > 5 and not line.lower().startswith(SKIP_PREFIXES):
            return line
    return lines[0] if lines else None


def extract_isin(text):
    m = re.search(r"ISIN[:\s]+([A-Z]{2}[A-Z0-9]{10})", text)
    return m.group(1).strip() if m else ""


def parse_meeting_date(raw):
    """
    Parse meeting date from raw string.
    Handles single dates and ranges (takes start date only).
    Returns ISO string with IST offset.
    """
    if not raw:
        return None
    from datetime import datetime
    try:
        # For ranges like "Dec 24, 2023 ... to Jan 22, 2024", take start only
        part = re.split(r"\bto\b", raw, flags=re.IGNORECASE)[0].strip()

        cleaned = re.sub(r",?\s*\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b,?", "", part)
        cleaned = re.sub(r"\bP\.M\.\b", "PM", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bA\.M\.\b", "AM", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(\d{1,2})\.(\d{2})\s*(AM|PM)", r"\1:\2 \3", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(\d{1,2})\.(\d{2})\b", r"\1:\2", cleaned)
        cleaned = re.sub(r"\bIST\b", "+05:30", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip().strip(",").strip()

        for fmt in (
            "%B %d, %Y, %I:%M %p +05:30",
            "%B %d, %Y %I:%M %p +05:30",
            "%B %d, %Y, %H:%M +05:30",
            "%B %d, %Y %H:%M +05:30",
        ):
            try:
                return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%dT%H:%M:%S+05:30")
            except ValueError:
                continue

        # Fallback: date only
        date_only = re.search(r"([A-Za-z]+ \d{1,2},?\s*\d{4})", part)
        if date_only:
            try:
                s = date_only.group(1).strip().replace(",", "")
                return datetime.strptime(s, "%B %d %Y").strftime("%Y-%m-%dT00:00:00+05:30")
            except ValueError:
                pass
    except Exception:
        pass
    return None


def date_from_filename(filename):
    m = re.search(r"\b(\d{2})(\d{2})(\d{4})\b", filename)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{month}-{day}T00:00:00+05:30"
    return None


def extract_from_pdf_url(url):
    """Download PDF and extract company_name, isin, meeting_date from page 1."""
    try:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return None
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name
        try:
            with pdfplumber.open(tmp_path) as pdf:
                page1 = pdf.pages[0].extract_text() or ""

            company = extract_company_name(page1)
            isin    = extract_isin(page1)

            date_match = re.search(
                r"Meeting\s+date\s*[&and]+\s*time\s*[:\-]\s*([^\n]+)",
                page1, re.IGNORECASE
            )
            meeting_date_raw = date_match.group(1).strip() if date_match else None
            meeting_date     = parse_meeting_date(meeting_date_raw)

            return {"company_name": company, "isin": isin, "meeting_date": meeting_date}
        finally:
            os.unlink(tmp_path)
    except Exception:
        return None


def normalize(name):
    return name.upper().strip()


def main():
    client = get_client()
    if client is None:
        print("ERROR: Supabase client is None.")
        sys.exit(1)

    print("Connected to Supabase." + ("  (DRY RUN)" if DRY else ""))

    all_files = list_all_files(client)
    log(f"\nFound {len(all_files)} PDF(s) in bucket")

    # Group by ticker -> {fy -> [url, ...]}
    # Each ticker also stores per-fy meeting date and company info
    grouped = {}

    for f in all_files:
        fy = f["financial_year"]
        if fy not in VALID_FYS:
            log(f"SKIP (no valid FY): {f['filename']}")
            continue
        ticker = ticker_from_filename(f["filename"])
        url    = get_public_url(client, f["path"])

        if ticker not in grouped:
            grouped[ticker] = {
                "company_name": ticker,
                "isin":         "",
                "filename":     f["filename"],
                "years": {
                    "2022-23": {"urls": [], "meeting_date": None},
                    "2023-24": {"urls": [], "meeting_date": None},
                    "2024-25": {"urls": [], "meeting_date": None},
                }
            }
        grouped[ticker]["years"][fy]["urls"].append(url)

    log(f"Unique companies: {len(grouped)}")

    if DRY:
        for ticker, data in sorted(grouped.items()):
            for fy in VALID_FYS:
                urls = data["years"][fy]["urls"]
                if urls:
                    log(f"  {ticker} | {fy} | {len(urls)} report(s)")
        print(f"\nDry run complete. {len(grouped)} companies found.")
        return

    # Extract ISIN + per-year meeting date from each PDF
    print("\nExtracting data from PDFs (this takes a few minutes)...")
    total_pdfs = sum(len(data["years"][fy]["urls"]) for data in grouped.values() for fy in VALID_FYS)
    done = 0

    for ticker, data in sorted(grouped.items()):
        # Extract ISIN + company name from first available PDF
        isin_fetched = False

        for fy in VALID_FYS:
            urls = data["years"][fy]["urls"]
            if not urls:
                continue

            # Extract from first PDF of this year
            info = extract_from_pdf_url(urls[0])
            done += 1
            print(f"  [{done}/{total_pdfs}] {ticker} {fy}", end=" ")

            if info:
                # Set company name + ISIN once from first successful extraction
                if not isin_fetched:
                    if info["company_name"]:
                        data["company_name"] = info["company_name"]
                    if info["isin"]:
                        data["isin"] = info["isin"]
                    isin_fetched = True

                # Store meeting date for this specific year
                if info["meeting_date"]:
                    data["years"][fy]["meeting_date"] = info["meeting_date"]
                    print(f"-> {info['meeting_date']}")
                else:
                    # Fallback: use filename date
                    data["years"][fy]["meeting_date"] = date_from_filename(data["filename"])
                    print(f"-> (from filename) {data['years'][fy]['meeting_date']}")
            else:
                data["years"][fy]["meeting_date"] = date_from_filename(data["filename"])
                print(f"-> (fallback) {data['years'][fy]['meeting_date']}")

    # Write to table
    print("\nWriting to Supabase table...")

    # Load existing to avoid duplicates
    existing = {}
    try:
        rows = client.table("recommendation_report").select("id,company_name").execute().data
        for row in rows:
            existing[normalize(row["company_name"])] = row["id"]
    except Exception as e:
        log(f"Could not load existing rows: {e}")

    success = 0
    failed  = 0

    for ticker, data in sorted(grouped.items()):
        try:
            company = data["company_name"] or ticker
            row = {
                "company_name": company,
                "isin_number":  data["isin"] or "",
            }

            for fy in VALID_FYS:
                urls         = data["years"][fy]["urls"]
                meeting_date = data["years"][fy]["meeting_date"]
                if urls:
                    row[fy]              = "\n".join(urls)
                    row[f"{fy}_date"]    = meeting_date

            existing_id = existing.get(normalize(company))
            if existing_id:
                client.table("recommendation_report").update(row).eq("id", existing_id).execute()
                log(f"UPDATED: {company}")
            else:
                client.table("recommendation_report").insert(row).execute()
                log(f"INSERTED: {company}")
            success += 1
        except Exception as e:
            log(f"FAILED {ticker}: {e}")
            failed += 1

    print(f"\nDone. Inserted/Updated: {success}  |  Failed: {failed}")


if __name__ == "__main__":
    main()
