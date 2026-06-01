from urllib.parse import (

    urlparse,

    parse_qs
)


def extract_events(requests):

    detected_events = []

    # =========================
    # STANDARD EVENT MAP
    # =========================
    standard_events = {

        "page_view": "PageView",

        "view_content": "ViewContent",

        "viewitem": "ViewContent",

        "add_to_cart": "AddToCart",

        "begin_checkout": "BeginCheckout",

        "purchase": "Purchase",

        "generate_lead": "Lead",

        "lead": "Lead",

        "submit_form": "FormSubmit",

        "form_submit": "FormSubmit",

        "social_click": "SocialClick"
    }

    # =========================
    # PROCESS REQUESTS
    # =========================
    for req in requests:

        url = req["url"].lower()

        # =========================
        # META PIXEL EVENTS
        # =========================
        if "facebook.com/tr" in url:

            try:

                parsed_url = urlparse(url)

                query_params = parse_qs(
                    parsed_url.query
                )

                if "ev" in query_params:

                    event_name = (

                        query_params["ev"][0]
                        .lower()
                    )

                    for key, value in (
                        standard_events.items()
                    ):

                        if key in event_name:

                            detected_events.append(
                                value
                            )

            except Exception:

                pass

        # =========================
        # GOOGLE ANALYTICS / GA4
        # =========================
        if "google" in url or "analytics" in url:

            try:

                parsed_url = urlparse(url)

                query_params = parse_qs(
                    parsed_url.query
                )

                # =========================
                # GA4 EVENT PARAM
                # =========================
                if "en" in query_params:

                    event_name = (

                        query_params["en"][0]
                        .lower()
                    )

                    for key, value in (
                        standard_events.items()
                    ):

                        if key in event_name:

                            detected_events.append(
                                value
                            )

                # =========================
                # FALLBACK URL SEARCH
                # =========================
                for key, value in (
                    standard_events.items()
                ):

                    if key in url:

                        detected_events.append(
                            value
                        )

            except Exception:

                pass

        # =========================
        # GTM / DATALAYER EVENTS
        # =========================
        if "gtm" in url:

            for key, value in (
                standard_events.items()
            ):

                if key in url:

                    detected_events.append(
                        value
                    )

    # =========================
    # REMOVE DUPLICATES
    # =========================
    unique_events = list(

        set(detected_events)
    )

    return unique_events