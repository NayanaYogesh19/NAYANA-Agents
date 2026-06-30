import asyncio
import sys

from tools.browser_tool import open_website
from tools.tag_detector import detect_tags
from tools.network_monitor import handle_request, get_tracked_requests
from tools.event_validator import extract_events
from tools.duplicate_checker import check_duplicates
from tools.industry_validator import validate_industry_events
from tools.interaction_engine import interact_with_website


def _run_full_audit(website_url, industry_type, result_queue):

    # Windows: set ProactorEventLoop before anything async
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(
            asyncio.WindowsProactorEventLoopPolicy()
        )

    print("\nStarting Tracking Audit...\n")

    data = open_website(website_url)

    if not data:
        result_queue.put({
            "website_url": website_url,
            "industry_type": industry_type,
            "detected_tags": [],
            "tracked_requests": [],
            "detected_events": [],
            "duplicate_events": [],
            "industry_validation": {
                "required_events": [],
                "missing_events": []
            },
            "interaction_logs": []
        })
        return

    page = data["page"]
    html = data["html"]

    detected_tags = detect_tags(html)

    page.on("request", handle_request)

    try:
        page.reload()
        page.wait_for_timeout(5000)
    except Exception as e:
        print(f"\nPage Reload Warning: {e}")

    tracked_requests = get_tracked_requests()
    detected_events = extract_events(tracked_requests)
    duplicate_events = check_duplicates(tracked_requests)
    industry_validation = validate_industry_events(
        detected_events, industry_type
    )

    # Interaction journey
    interaction_logs = interact_with_website(page, website_url)

    try:
        data["browser"].close()
        data["playwright"].stop()
    except Exception:
        pass

    print("\nAudit Completed\n")

    result_queue.put({
        "website_url": website_url,
        "industry_type": industry_type,
        "detected_tags": detected_tags,
        "tracked_requests": tracked_requests,
        "detected_events": detected_events,
        "duplicate_events": duplicate_events,
        "industry_validation": industry_validation,
        "interaction_logs": interaction_logs
    })
