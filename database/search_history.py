from database.supabase_client import get_client


def search_history_supabase(
    resolution_type: str = None,
    recommendation:  str = None,
    director_name:   str = None,
    ordinary:        bool = None,
    special:         bool = None,
    limit:           int = 20,
) -> list:
    """
    Query the Supabase `resolutions` table for historical governance cases.

    All parameters are optional — pass only the ones you want to filter on.
    Returns a list of dicts with keys:
        company_name, financial_year, resolution_type,
        recommendation, confidence, governance_json
    Returns [] when Supabase is not configured or on any error.
    """
    client = get_client()
    if client is None:
        return []

    try:
        query = (
            client.table("resolutions")
            .select(
                "resolution_type, recommendation, confidence, governance_json, "
                "reports(status, company_id, companies(company_name, financial_year))"
            )
            .limit(limit)
        )

        if resolution_type:
            query = query.eq("resolution_type", resolution_type)

        if recommendation:
            query = query.eq("recommendation", recommendation)

        response = query.execute()
        rows = response.data or []

        results = []
        for row in rows:
            report  = row.get("reports") or {}
            company = report.get("companies") or {}

            gov = row.get("governance_json") or {}
            if isinstance(gov, str):
                import json
                try:
                    gov = json.loads(gov)
                except Exception:
                    gov = {}

            # Optional director/ordinary/special filter on governance_json payload
            if director_name:
                if director_name.lower() not in str(gov).lower():
                    continue

            if ordinary is not None:
                if bool(gov.get("ordinary_resolution")) != ordinary:
                    continue

            if special is not None:
                if bool(gov.get("special_resolution")) != special:
                    continue

            results.append({
                "company_name":     company.get("company_name", ""),
                "financial_year":   company.get("financial_year", ""),
                "resolution_type":  row.get("resolution_type", ""),
                "recommendation":   row.get("recommendation", ""),
                "confidence":       row.get("confidence", ""),
                "governance_json":  gov,
            })

        return results

    except Exception:
        return []
