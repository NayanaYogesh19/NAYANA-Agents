from fastapi import APIRouter

from ga4.auth import get_credentials

from ga4.schemas import ReportRequest

from ga4.service import get_ga4_metrics

router = APIRouter()


@router.post("/custom-report")

async def custom_report(

    request: ReportRequest
):

    creds = get_credentials()

    report = get_ga4_metrics(

        creds=creds,

        property_id=request.property_id,

        dimensions=request.dimensions,

        metrics=request.metrics,

        start_date=request.start_date,

        end_date=request.end_date,

        limit=request.limit,
    )

    return {
        "report": report
    }

