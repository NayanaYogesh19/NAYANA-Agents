import json

from database.supabase_client import get_client


def save_report(
    company_id: str,
    status: str,
    approved_by: str,
    comments: str,
    report_json: list,
) -> str | None:
    """
    Insert or upsert a governance report into the `reports` table.

    Returns the row `id` (uuid string) on success, None otherwise.

    Table DDL (run once in Supabase SQL editor):

        create table if not exists reports (
            id           uuid primary key default gen_random_uuid(),
            company_id   uuid references companies(id),
            status       text,
            approved_by  text,
            comments     text,
            report_json  jsonb,
            created_at   timestamptz default now()
        );
    """
    client = get_client()
    if client is None:
        return None

    try:
        response = (
            client.table("reports")
            .insert(
                {
                    "company_id":  company_id,
                    "status":      status,
                    "approved_by": approved_by,
                    "comments":    comments,
                    "report_json": json.dumps(report_json),
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
