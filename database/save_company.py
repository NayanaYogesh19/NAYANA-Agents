from database.supabase_client import get_client


def save_company(company_name: str, financial_year: str) -> str | None:
    """
    Upsert a company record into the `companies` table.

    Returns the row `id` (uuid string) on success, None on failure or when
    Supabase is not configured.

    Table DDL (run once in Supabase SQL editor):

        create table if not exists companies (
            id            uuid primary key default gen_random_uuid(),
            company_name  text not null,
            financial_year text not null,
            created_at    timestamptz default now(),
            unique (company_name, financial_year)
        );
    """
    client = get_client()
    if client is None:
        return None

    try:
        response = (
            client.table("companies")
            .upsert(
                {
                    "company_name":   company_name,
                    "financial_year": financial_year,
                },
                on_conflict="company_name,financial_year",
            )
            .execute()
        )

        rows = response.data
        if rows:
            return rows[0].get("id")

    except Exception:
        pass

    return None
