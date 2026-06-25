from reportlab.platypus import (

    SimpleDocTemplate,

    Paragraph,

    Spacer
)

from reportlab.lib.styles import (
    getSampleStyleSheet
)

from reportlab.lib.pagesizes import (
    letter
)


def generate_pdf_report(

    audit_result,

    customer_journey
):

    # =========================
    # PDF FILE PATH
    # =========================
    file_path = (
        "reports/tracking_audit_report.pdf"
    )

    # =========================
    # CREATE PDF DOC
    # =========================
    doc = SimpleDocTemplate(

        file_path,

        pagesize=letter
    )

    styles = getSampleStyleSheet()

    elements = []

    # =========================
    # TITLE
    # =========================
    title = Paragraph(

        "Tracking Audit Report",

        styles["Title"]
    )

    elements.append(title)

    elements.append(
        Spacer(1, 25)
    )

    # =========================
    # WEBSITE DETAILS
    # =========================
    website = Paragraph(

        f"""
        <b>Website:</b>
        {audit_result['website_url']}
        """,

        styles["BodyText"]
    )

    industry = Paragraph(

        f"""
        <b>Industry Type:</b>
        {audit_result['industry_type'].upper()}
        """,

        styles["BodyText"]
    )

    elements.append(website)

    elements.append(
        Spacer(1, 10)
    )

    elements.append(industry)

    elements.append(
        Spacer(1, 25)
    )

    # =========================
    # DETECTED TAGS
    # =========================
    tags_title = Paragraph(

        "<b>Detected Tags</b>",

        styles["Heading2"]
    )

    elements.append(tags_title)

    detected_tags = audit_result[
        "detected_tags"
    ]

    if detected_tags:

        for tag in detected_tags:

            elements.append(

                Paragraph(
                    f"• {tag}",
                    styles["BodyText"]
                )
            )

    else:

        elements.append(

            Paragraph(
                "• No tags detected",
                styles["BodyText"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # DETECTED EVENTS
    # =========================
    events_title = Paragraph(

        "<b>Detected Events</b>",

        styles["Heading2"]
    )

    elements.append(events_title)

    detected_events = audit_result[
        "detected_events"
    ]

    if detected_events:

        for event in detected_events:

            elements.append(

                Paragraph(
                    f"• {event}",
                    styles["BodyText"]
                )
            )

    else:

        elements.append(

            Paragraph(
                "• No events detected",
                styles["BodyText"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # MISSING EVENTS
    # =========================
    missing_title = Paragraph(

        "<b>Missing Events</b>",

        styles["Heading2"]
    )

    elements.append(missing_title)

    missing_events = audit_result[
        "industry_validation"
    ]["missing_events"]

    if missing_events:

        for event in missing_events:

            elements.append(

                Paragraph(
                    f"• {event}",
                    styles["BodyText"]
                )
            )

    else:

        elements.append(

            Paragraph(
                "• No missing events",
                styles["BodyText"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # DUPLICATE TRACKING
    # =========================
    duplicate_title = Paragraph(

        "<b>Duplicate Tracking</b>",

        styles["Heading2"]
    )

    elements.append(duplicate_title)

    duplicates = audit_result[
        "duplicate_events"
    ]

    if duplicates:

        for dup in duplicates:

            elements.append(

                Paragraph(

                    f"• {dup['platform']} fired {dup['count']} times",

                    styles["BodyText"]
                )
            )

    else:

        elements.append(

            Paragraph(
                "• No duplicate tracking detected",
                styles["BodyText"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # CUSTOMER JOURNEY
    # =========================
    journey_title = Paragraph(

        "<b>Automation-Based Website Interaction Journey</b>",

        styles["Heading2"]
    )

    elements.append(journey_title)

    if customer_journey:

        for step in customer_journey:

            elements.append(

                Paragraph(
                    f"• {step}",
                    styles["BodyText"]
                )
            )

    else:

        elements.append(

            Paragraph(
                "• No interaction journey captured",
                styles["BodyText"]
            )
        )

    elements.append(
        Spacer(1, 20)
    )

    # =========================
    # BUILD PDF
    # =========================
    doc.build(elements)

    print(
        "\nPDF Report Generated"
    )

    return file_path