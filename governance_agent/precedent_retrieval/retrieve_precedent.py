import os
import json

APPROVED_FOLDER = "storage/approved"


def _search_local(
    resolution_type: str = None,
    recommendation:  str = None,
    director_name:   str = None,
    ordinary:        bool = None,
    special:         bool = None,
) -> list:
    """
    Search approved JSON files stored in storage/approved/.
    All filter parameters are optional.
    """
    results = []

    if not os.path.exists(APPROVED_FOLDER):
        return results

    for filename in os.listdir(APPROVED_FOLDER):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(APPROVED_FOLDER, filename)

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        company_name   = data.get("company_name", "")
        financial_year = data.get("financial_year", "")

        for r in data.get("resolutions", []):

            # Filter: resolution_type
            if resolution_type and r.get("resolution_type") != resolution_type:
                continue

            # Filter: recommendation (from nested recommendation dict)
            rec_obj = r.get("recommendation", {})
            rec_val = rec_obj.get("recommendation", "") if isinstance(rec_obj, dict) else ""
            if recommendation and rec_val != recommendation:
                continue

            # Filter: director_name
            if director_name:
                if director_name.lower() not in r.get("resolution_text", "").lower():
                    continue

            # Filter: ordinary / special
            gf = r.get("governance_factors", {})
            if ordinary is not None:
                if bool(gf.get("ordinary_resolution")) != ordinary:
                    continue
            if special is not None:
                if bool(gf.get("special_resolution")) != special:
                    continue

            results.append({
                "source":           "local",
                "company_name":     company_name,
                "financial_year":   financial_year,
                "resolution_type":  r.get("resolution_type", ""),
                "recommendation":   rec_val,
                "confidence":       rec_obj.get("confidence", "") if isinstance(rec_obj, dict) else "",
                "governance_evaluation": r.get("governance_evaluation", {}),
                "governance_factors":    gf,
            })

    return results


def _search_supabase(
    resolution_type: str = None,
    recommendation:  str = None,
    director_name:   str = None,
    ordinary:        bool = None,
    special:         bool = None,
) -> list:
    """
    Search Supabase `resolutions` table via search_history module.
    Returns [] gracefully when Supabase is not configured.
    """
    try:
        from database.search_history import search_history_supabase
        rows = search_history_supabase(
            resolution_type=resolution_type,
            recommendation=recommendation,
            director_name=director_name,
            ordinary=ordinary,
            special=special,
        )
        for row in rows:
            row["source"] = "supabase"
        return rows
    except Exception:
        return []


def _deduplicate(results: list) -> list:
    """
    Remove near-duplicate entries (same company + financial_year + type).
    Local entries take priority over Supabase duplicates.
    """
    seen = set()
    deduped = []
    for r in results:
        key = (
            r.get("company_name", "").lower(),
            r.get("financial_year", ""),
            r.get("resolution_type", ""),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


# ── Public API ──────────────────────────────────────────────────────────────

def get_precedents(
    resolution_type: str,
    recommendation:  str = None,
    director_name:   str = None,
    ordinary:        bool = None,
    special:         bool = None,
) -> list:
    """
    Return combined historical precedents for a given resolution_type.

    Search order: local approved JSON  →  Supabase.
    Results are deduplicated by (company, financial_year, resolution_type).

    This is the primary function called by the analysis pipeline.
    """
    local_results = _search_local(
        resolution_type=resolution_type,
        recommendation=recommendation,
        director_name=director_name,
        ordinary=ordinary,
        special=special,
    )

    supabase_results = _search_supabase(
        resolution_type=resolution_type,
        recommendation=recommendation,
        director_name=director_name,
        ordinary=ordinary,
        special=special,
    )

    combined = local_results + supabase_results
    return _deduplicate(combined)


def search_precedents(
    resolution_type: str = None,
    recommendation:  str = None,
    director_name:   str = None,
    ordinary:        bool = None,
    special:         bool = None,
) -> list:
    """
    Free-form precedent search with all optional filters.
    Exposed via the /search_history API endpoint.
    """
    local_results = _search_local(
        resolution_type=resolution_type,
        recommendation=recommendation,
        director_name=director_name,
        ordinary=ordinary,
        special=special,
    )

    supabase_results = _search_supabase(
        resolution_type=resolution_type,
        recommendation=recommendation,
        director_name=director_name,
        ordinary=ordinary,
        special=special,
    )

    combined = local_results + supabase_results
    return _deduplicate(combined)
