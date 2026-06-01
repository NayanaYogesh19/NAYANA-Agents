from tools.browser_tool import open_website

from tools.tag_detector import (
    detect_tags
)

from tools.network_monitor import (
    handle_request,
    get_tracked_requests
)

from tools.event_validator import (
    extract_events
)

from tools.duplicate_checker import (
    check_duplicates
)

from tools.industry_validator import (
    validate_industry_events
)


def run_tracking_audit(
    website_url,
    industry_type
):

    print("\nStarting Tracking Audit...\n")

    # =========================
    # OPEN WEBSITE
    # =========================
    data = open_website(
        website_url
    )

    # Safety check
    if not data:

        return {

            "website_url": website_url,

            "industry_type": industry_type,

            "detected_tags": [],

            "tracked_requests": [],

            "detected_events": [],

            "duplicate_events": [],

            "industry_validation": {

                "required_events": [],

                "missing_events": []
            }
        }

    page = data["page"]

    html = data["html"]

    # =========================
    # DETECT TAGS
    # =========================
    detected_tags = detect_tags(
        html
    )

    # =========================
    # ATTACH NETWORK MONITOR
    # =========================
    page.on(
        "request",
        handle_request
    )

    # =========================
    # RELOAD PAGE
    # =========================
    try:

        page.reload()

        # Wait for scripts
        page.wait_for_timeout(5000)

    except Exception as e:

        print(
            f"\nPage Reload Warning: {e}"
        )

    # =========================
    # GET TRACKED REQUESTS
    # =========================
    tracked_requests = (
        get_tracked_requests()
    )

    # =========================
    # EXTRACT EVENTS
    # =========================
    detected_events = (
        extract_events(
            tracked_requests
        )
    )

    # =========================
    # DUPLICATE CHECK
    # =========================
    duplicate_events = (
        check_duplicates(
            tracked_requests
        )
    )

    # =========================
    # INDUSTRY VALIDATION
    # =========================
    industry_validation = (
        validate_industry_events(
            detected_events,
            industry_type
        )
    )

    # =========================
    # FINAL AUDIT RESULT
    # =========================
    audit_result = {

        "website_url": website_url,

        "industry_type": industry_type,

        "detected_tags": detected_tags,

        "tracked_requests":
            tracked_requests,

        "detected_events":
            detected_events,

        "duplicate_events":
            duplicate_events,

        "industry_validation":
            industry_validation
    }

    # =========================
    # DEBUG MODE
    # =========================
    # Browser intentionally left open
    # for debugging interactions

    try:

        pass

        data["browser"].close()

        data["playwright"].stop()

    except Exception:

        pass

    print("\nAudit Completed\n")

    return audit_result