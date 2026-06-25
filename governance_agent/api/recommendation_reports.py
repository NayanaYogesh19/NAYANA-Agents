from fastapi import APIRouter
from database.supabase_client import get_client

router = APIRouter()


@router.get("/recommendation_reports")
def list_recommendation_reports():
    client = get_client()
    if client is None:
        return {"status": "error", "message": "Supabase not connected"}

    result = (
        client.table("recommendation_report")
        .select(
            'id, company_name, isin_number, '
            '"2022-23", "2022-23_date", '
            '"2023-24", "2023-24_date", '
            '"2024-25", "2024-25_date"'
        )
        .order("company_name", desc=False)
        .execute()
    )
    return {"status": "success", "total": len(result.data), "reports": result.data}
