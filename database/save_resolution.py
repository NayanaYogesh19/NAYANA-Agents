import json

from database.supabase_client import get_client


def save_resolution(
    report_id: str,
    resolution_number: int,
    resolution_type: str,
    recommendation: str,
    confidence: str,
    governance_json: dict,
) -> str | None:
    """
    Insert one resolution record into the `resolutions` table.

    Returns the row `id` on success, None otherwise.

    Table DDL (run once in Supabase SQL editor):

        create table if not exists resolutions (
            id                uuid primary key default gen_random_uuid(),
            report_id         uuid references reports(id),
            resolution_number int,
            resolution_type   text,
            recommendation    text,
            confidence        text,
            governance_json   jsonb,
            created_at        timestamptz default now()
        );
    """
    client = get_client()
    if client is None:
        return None

    try:
        response = (
            client.table("resolutions")
            .insert(
                {
                    "report_id":         report_id,
                    "resolution_number": resolution_number,
                    "resolution_type":   resolution_type,
                    "recommendation":    recommendation,
                    "confidence":        confidence,
                    "governance_json":   json.dumps(governance_json),
                }
            )
            .execute()
        )

        rows = response.data
        if rows:
            return rows[0].get("id")

    except Exception:
        pass

    return None
