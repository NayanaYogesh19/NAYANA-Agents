import multiprocessing

multiprocessing.freeze_support()

from fastapi import FastAPI, Form

from fastapi.responses import (
    HTMLResponse,
    FileResponse
)

from services.audit_service import (
    run_tracking_audit
)

from services.journey_service import (
    build_customer_journey
)

from services.pdf_service import (
    generate_pdf_report
)

app = FastAPI()


# =========================
# HOME PAGE
# =========================
@app.get("/", response_class=HTMLResponse)
def home():

    return """

    <html>

    <head>

        <title>
            Tracking Audit Platform
        </title>

        <link
            href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            rel="stylesheet"
        >

    </head>

    <body class="bg-light">

        <div class="container mt-5">

            <div class="card shadow p-5">

                <h1 class="mb-4 text-primary">
                    Tracking Tags Hygiene Agent
                </h1>

                <form action="/audit" method="post">

                    <div class="mb-3">

                        <label class="form-label">
                            Website URL
                        </label>

                        <input
                            type="text"
                            name="website_url"
                            class="form-control"
                            placeholder="https://example.com"
                            required
                        >

                    </div>

                    <div class="mb-4">

                        <label class="form-label">
                            Industry Type
                        </label>

                        <select
                            name="industry_type"
                            class="form-select"
                        >

                            <option value="b2b">
                                B2B
                            </option>

                            <option value="b2c">
                                B2C
                            </option>

                        </select>

                    </div>

                    <button
                        type="submit"
                        class="btn btn-primary"
                    >
                        Run Audit
                    </button>

                </form>

            </div>

        </div>

    </body>

    </html>
    """


# =========================
# AUDIT DASHBOARD
# =========================
@app.post("/audit", response_class=HTMLResponse)
def audit(

    website_url: str = Form(...),

    industry_type: str = Form(...)
):

    # =========================
    # RUN TRACKING AUDIT
    # =========================
    result = run_tracking_audit(

        website_url,

        industry_type
    )

    # =========================
    # SAFE AUDIT FAILURE
    # =========================
    if not result:

        return """

        <html>

        <head>

            <title>
                Audit Failed
            </title>

            <link
                href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
                rel="stylesheet"
            >

        </head>

        <body class="bg-light">

            <div class="container mt-5">

                <div class="alert alert-danger">

                    <h2>
                        Tracking Audit Failed
                    </h2>

                    <hr>

                    <p>
                        Unable to audit website.
                    </p>

                    <a
                        href="/"
                        class="btn btn-primary"
                    >
                        Try Again
                    </a>

                </div>

            </div>

        </body>

        </html>
        """

    # =========================
    # BUILD CUSTOMER JOURNEY
    # =========================
    customer_journey = (

        build_customer_journey(

            result["interaction_logs"],

            result["detected_events"]
        )
    )

    # =========================
    # GENERATE PDF REPORT
    # =========================
    generate_pdf_report(

        result,

        customer_journey
    )

    # =========================
    # TRACKING SCORE
    # =========================
    total_required = len(

        result["industry_validation"][
            "required_events"
        ]
    )

    missing = len(

        result["industry_validation"][
            "missing_events"
        ]
    )

    if total_required == 0:

        tracking_score = 0

    else:

        tracking_score = int(

            (
                (total_required - missing)
                /
                total_required
            ) * 100
        )

    # =========================
    # HTML LISTS
    # =========================
    detected_tags_html = "".join(

        f"<li>{tag}</li>"

        for tag in result[
            "detected_tags"
        ]
    )

    detected_events_html = "".join(

        f"<li>{event}</li>"

        for event in result[
            "detected_events"
        ]
    )

    duplicate_html = "".join(

        f"<li>{dup['platform']} fired {dup['count']} times</li>"

        for dup in result[
            "duplicate_events"
        ]
    )

    missing_events_html = "".join(

        f"<li>{event}</li>"

        for event in result[
            "industry_validation"
        ]["missing_events"]
    )

    journey_html = "".join(

        f"<li>{step}</li>"

        for step in customer_journey
    )

    # =========================
    # DASHBOARD HTML
    # =========================
    return f"""

    <html>

    <head>

        <title>
            Tracking Dashboard
        </title>

        <link
            href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
            rel="stylesheet"
        >

    </head>

    <body class="bg-light">

        <div class="container mt-5">

            <h1 class="mb-4 text-primary">
                Tracking Audit Dashboard
            </h1>

      

            <!-- CARDS -->
            <div class="row">

                <div class="col-md-3">

                    <div class="card shadow p-3">

                        <h5>
                            Detected Tags
                        </h5>

                        <h2>
                            {len(result['detected_tags'])}
                        </h2>

                    </div>

                </div>

                <div class="col-md-3">

                    <div class="card shadow p-3">

                        <h5>
                            Events Fired
                        </h5>

                        <h2>
                            {len(result['detected_events'])}
                        </h2>

                    </div>

                </div>

                <div class="col-md-3">

                    <div class="card shadow p-3">

                        <h5>
                            Missing Events
                        </h5>

                        <h2>
                            {len(result['industry_validation']['missing_events'])}
                        </h2>

                    </div>

                </div>

                <div class="col-md-3">

                    <div class="card shadow p-3">

                        <h5>
                            Duplicate Tags
                        </h5>

                        <h2>
                            {len(result['duplicate_events'])}
                        </h2>

                    </div>

                </div>

            </div>

            <br>

            <!-- DETAILS -->
            <div class="row">

                <div class="col-md-6">

                    <div class="card shadow p-3 mb-4">

                        <h4>
                            Detected Tags
                        </h4>

                        <ul>
                            {detected_tags_html}
                        </ul>

                    </div>

                </div>

                <div class="col-md-6">

                    <div class="card shadow p-3 mb-4">

                        <h4>
                            Detected Events
                        </h4>

                        <ul>
                            {detected_events_html}
                        </ul>

                    </div>

                </div>

            </div>

            <!-- MISSING + DUPLICATES -->
            <div class="row">

                <div class="col-md-6">

                    <div class="card shadow p-3 mb-4">

                        <h4>
                            Missing Events
                        </h4>

                        <ul>
                            {missing_events_html}
                        </ul>

                    </div>

                </div>

                <div class="col-md-6">

                    <div class="card shadow p-3 mb-4">

                        <h4>
                            Duplicate Tracking
                        </h4>

                        <ul>
                            {duplicate_html}
                        </ul>

                    </div>

                </div>

            </div>

            <!-- CUSTOMER JOURNEY -->
            <div class="card shadow p-4 mb-4">

                <h3 class="text-success">
                    Automation-Based Website Interaction Journey
                </h3>

                <ul>
                    {journey_html}
                </ul>

            </div>

            <!-- BUTTONS -->
            <div class="mb-5">

                <a
                    href="/download-report"
                    class="btn btn-success me-3"
                >
                    Download PDF Report
                </a>

                <a
                    href="/"
                    class="btn btn-secondary"
                >
                    Start New Audit
                </a>

            </div>

        </div>

    </body>

    </html>
    """


# =========================
# DOWNLOAD PDF ROUTE
# =========================
@app.get("/download-report")
def download_report():

    path = (
        "reports/tracking_audit_report.pdf"
    )

    return FileResponse(

        path,

        media_type="application/pdf",

        filename="tracking_audit_report.pdf"
    )