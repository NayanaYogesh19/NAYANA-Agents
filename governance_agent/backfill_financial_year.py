"""Run once to backfill financial_year for existing recommendation_report rows."""
from datetime import datetime
from database.supabase_client import get_client

def derive_fy(meeting_date_iso):
    if not meeting_date_iso:
        return None
    try:
        dt = datetime.fromisoformat(meeting_date_iso)
        year, month = dt.year, dt.month
        if month >= 4:
            return f"{year}-{str(year + 1)[2:]}"
        else:
            return f"{year - 1}-{str(year)[2:]}"
    except Exception:
        return None

client = get_client()
rows = client.table("recommendation_report").select("id, meeting_date").execute().data
print(f"Backfilling {len(rows)} rows...")
for row in rows:
    fy = derive_fy(row["meeting_date"])
    client.table("recommendation_report").update({"financial_year": fy}).eq("id", row["id"]).execute()
    print(f"  {row['id'][:8]}... -> {fy}")
print("Done.")
