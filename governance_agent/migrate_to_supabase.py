"""
migrate_to_supabase.py  —  one-shot loader for the InGovern knowledge base.

WHAT IT DOES
  1. Ensures the three Storage buckets exist (policy-guidelines, notices, agent-reports).
  2. Walks storage/approved/*.json  -> companies, reports, resolutions, rag_resolutions.
  3. Walks storage/notices/*.pdf     -> uploads to the 'notices' bucket.
  4. Walks storage/policies/**/*.pdf -> uploads to 'policy-guidelines' + policy_documents row.
     (Folder name under storage/policies/ is treated as the company_name;
      put company-agnostic policies directly in storage/policies/_global/.)

PREREQUISITES
  - Run supabase_schema.sql in the Supabase SQL Editor first.
  - .env already has SUPABASE_URL + SUPABASE_KEY (you said it does).
  - IMPORTANT: use the SERVICE ROLE key, not the anon/publishable key, when
    running migrations — the anon key is blocked by Row Level Security from
    inserting. Put it in .env temporarily as SUPABASE_KEY, run this, then
    switch back to the publishable key for the running app.

RUN
  cd InGovern_Agent
  python migrate_to_supabase.py            # migrate everything
  python migrate_to_supabase.py --dry-run  # show what WOULD happen, change nothing
"""

import os
import sys
import json

from database.supabase_client import get_client
from database.save_company    import save_company
from database.save_report     import save_report
from database.save_resolution import save_resolution
from database.rag_store       import store_resolution_rag

DRY = "--dry-run" in sys.argv

APPROVED_DIR = "storage/approved"
NOTICES_DIR  = "storage/notices"
POLICIES_DIR = "storage/policies"          # create this folder; drop policy PDFs here

BUCKETS = ["policy-guidelines", "notices", "agent-reports"]


# ── helpers ──────────────────────────────────────────────────────────────────

def log(msg):
    print(("[dry-run] " if DRY else "") + msg)


def ensure_buckets(client):
    """Create each bucket if it doesn't already exist (private)."""
    try:
        existing = {b.name for b in client.storage.list_buckets()}
    except Exception:
        existing = set()
    for name in BUCKETS:
        if name in existing:
            log(f"bucket ok: {name}")
            continue
        if DRY:
            log(f"would create bucket: {name}")
            continue
        try:
            client.storage.create_bucket(name, options={"public": False})
            log(f"created bucket: {name}")
        except Exception as e:
            log(f"bucket create skipped ({name}): {e}")


def upload_file(client, bucket, local_path, dest_path, content_type="application/pdf"):
    """Upload one file to a bucket, overwriting if it exists."""
    if DRY:
        log(f"would upload {local_path} -> {bucket}/{dest_path}")
        return True
    try:
        with open(local_path, "rb") as f:
            data = f.read()
        client.storage.from_(bucket).upload(
            dest_path,
            data,
            {"content-type": content_type, "upsert": "true"},
        )
        log(f"uploaded {bucket}/{dest_path}")
        return True
    except Exception as e:
        log(f"upload FAILED {bucket}/{dest_path}: {e}")
        return False


# ── 1. records: approved JSONs -> tables ─────────────────────────────────────

def migrate_records(client):
    if not os.path.isdir(APPROVED_DIR):
        log(f"no {APPROVED_DIR}/ — skipping records")
        return
    files = sorted(f for f in os.listdir(APPROVED_DIR) if f.endswith(".json"))
    log(f"--- records: {len(files)} approved file(s) ---")

    for fname in files:
        try:
            with open(os.path.join(APPROVED_DIR, fname), encoding="utf-8") as f:
                d = json.load(f)
        except Exception as e:
            log(f"skip {fname}: {e}")
            continue

        company = d.get("company_name", "Unknown")
        fy      = d.get("financial_year", "")
        notice  = (d.get("notice_metadata") or {}).get("notice_type", "AGM")

        if DRY:
            log(f"would migrate {company} {fy} ({len(d.get('resolutions', []))} resolutions)")
            continue

        company_id = save_company(company, fy)
        if not company_id:
            log(f"  ! company insert failed for {company} — check service-role key & schema")
            continue

        report_id = save_report(
            company_id  = company_id,
            status      = d.get("status", "approved"),
            approved_by = d.get("approved_by", ""),
            comments    = d.get("comments", ""),
            report_json = d.get("report", []),
        )
        if not report_id:
            log(f"  ! report insert failed for {company}")
            continue

        n = 0
        for r in d.get("resolutions", []):
            rec = r.get("recommendation", {})
            if isinstance(rec, str):
                rec = {"recommendation": rec}
            save_resolution(
                report_id         = report_id,
                resolution_number = r.get("resolution_number", 0),
                resolution_type   = r.get("resolution_type", ""),
                recommendation    = rec.get("recommendation", ""),
                confidence        = rec.get("confidence", ""),
                governance_json   = r.get("governance_evaluation", {}) or {},
            )
            # also seed the RAG store so semantic search has history to match on
            store_resolution_rag(
                company_name   = company,
                financial_year = fy,
                notice_type    = notice,
                industry       = d.get("industry", ""),
                resolution     = r,
                commentary     = r.get("ingovern_commentary", {}) or {},
            )
            n += 1
        log(f"  migrated {company} {fy}: 1 report, {n} resolutions")


# ── 2. notice PDFs -> 'notices' bucket ───────────────────────────────────────

def migrate_notices(client):
    if not os.path.isdir(NOTICES_DIR):
        log(f"no {NOTICES_DIR}/ — skipping notices")
        return
    files = [f for f in os.listdir(NOTICES_DIR) if f.lower().endswith(".pdf")]
    log(f"--- notices: {len(files)} pdf(s) ---")
    for f in files:
        upload_file(client, "notices", os.path.join(NOTICES_DIR, f), f)


# ── 3. policy PDFs -> 'policy-guidelines' bucket + policy_documents table ─────

def migrate_policies(client):
    if not os.path.isdir(POLICIES_DIR):
        log(f"no {POLICIES_DIR}/ — create it and drop policy PDFs there "
            f"(one subfolder per company; use _global for shared policies)")
        return
    count = 0
    for root, _dirs, files in os.walk(POLICIES_DIR):
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            local = os.path.join(root, fn)
            rel   = os.path.relpath(local, POLICIES_DIR).replace("\\", "/")
            company = rel.split("/")[0]
            company = None if company in ("_global", ".") else company

            if upload_file(client, "policy-guidelines", local, rel):
                if not DRY:
                    try:
                        client.table("policy_documents").upsert(
                            {
                                "company_name": company,
                                "policy_type":  os.path.splitext(fn)[0],
                                "title":        fn,
                                "storage_path": rel,
                                "file_size":    os.path.getsize(local),
                            },
                            on_conflict="storage_path",
                        ).execute()
                    except Exception as e:
                        log(f"  metadata row failed for {rel}: {e}")
                count += 1
    log(f"--- policies: {count} pdf(s) processed ---")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    client = get_client()
    if client is None:
        print("ERROR: Supabase client is None. Check SUPABASE_URL / SUPABASE_KEY in .env.")
        sys.exit(1)

    print("Connected to Supabase." + ("  (DRY RUN — no writes)" if DRY else ""))
    ensure_buckets(client)
    migrate_records(client)
    migrate_notices(client)
    migrate_policies(client)
    print("\nDone.")


if __name__ == "__main__":
    main()