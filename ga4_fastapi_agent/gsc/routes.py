from fastapi import APIRouter

from ga4.auth import get_credentials
from gsc.schemas import PerformanceRequest
from gsc.service import get_search_console_data
from gsc.schemas import SitemapRequest
from gsc.service import get_sitemaps
from gsc.schemas import URLRequest
from gsc.service import get_https_report
from gsc.service import get_breadcrumbs_report
from gsc.service import get_pages_report
from gsc.service import get_videos_report

from gsc.service import (
    get_core_web_vitals
)

router = APIRouter()


@router.post("/performance/queries")
async def queries(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["query"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "queries": data
    }


@router.post("/performance/pages")
async def pages(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["page"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "pages": data
    }


@router.post("/performance/countries")
async def countries(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["country"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "countries": data
    }


@router.post("/performance/devices")
async def devices(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["device"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "devices": data
    }


@router.post("/performance/search-appearance")
async def search_appearance(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["searchAppearance"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "search_appearance": data
    }


@router.post("/performance/days")
async def days(request: PerformanceRequest):

    creds = get_credentials()

    data = get_search_console_data(
        creds,
        request.site_url,
        ["date"],
        request.start_date,
        request.end_date,
        request.row_limit
    )

    return {
        "days": data
    }

@router.post(
    "/indexing/pages-report"
)
async def pages_report(
    request: SitemapRequest
):

    creds = get_credentials()

    data = get_pages_report(
        creds,
        request.site_url
    )

    return {
        "pages_report": data
    }

@router.post("/indexing/videos-report")
async def videos_report(
    request: SitemapRequest
):

    creds = get_credentials()

    data = get_videos_report(
        creds,
        request.site_url
    )

    return {
        "videos_report": data
    }

@router.post("/indexing/sitemaps")
async def sitemaps(
    request: SitemapRequest
):

    creds = get_credentials()

    data = get_sitemaps(
        creds,
        request.site_url
    )

    return {
        "sitemaps": data
    }


@router.post("/experience/core-web-vitals")
async def core_web_vitals(
    request: URLRequest
):

    data = get_core_web_vitals(
        request.url
    )

    return {
        "core_web_vitals": data
    }


@router.post("/experience/https")
async def https_report(
    request: PerformanceRequest
):

    creds = get_credentials()

    data = get_https_report(
        creds,
        request.site_url
    )

    return {
        "https": data
    }




@router.post("/enhancements/breadcrumbs-report")
async def breadcrumbs_report(
    request: PerformanceRequest
):

    creds = get_credentials()

    data = get_breadcrumbs_report(
        creds,
        request.site_url
    )

    return {
        "breadcrumbs_report": data
    }

