// ==========================================
// API BASE URL
// ==========================================

const API_BASE =
    "http://127.0.0.1:8000";

console.log("frontend/scripts.js loaded");

// ==========================================
// DOM ELEMENTS
// ==========================================

const moduleSelect =
    document.getElementById(
        "module"
    );

const reportSelect =
    document.getElementById(
        "report"
    );

const dynamicInputs =
    document.getElementById(
        "dynamicInputs"
    );

const resetBtn =
    document.getElementById(
        "resetBtn"
    );


// ==========================================
// GA4 REPORTS
// ==========================================

const ga4Reports = {

    "Traffic Acquisition": {
        type: "ga4"
    },

    "User Acquisition": {
        type: "ga4"
    },

    "Landing Pages": {
        type: "ga4"
    },

    "Pages & Screens": {
        type: "ga4"
    },

    "Events": {
        type: "ga4"
    },

    "Country Report": {
        type: "ga4"
    },

    "City Report": {
        type: "ga4"
    },

    "Device Report": {
        type: "ga4"
    },

    "Browser Report": {
        type: "ga4"
    },

    "Operating System Report": {
        type: "ga4"
    },

    "Source / Medium Report": {
        type: "ga4"
    },

    "Campaign Report": {
        type: "ga4"
    },

    "New vs Returning Users": {
        type: "ga4"
    },

    "Daily Trend Report": {
        type: "ga4"
    },

    "Custom Report": {
        type: "ga4"
    }

};


// ==========================================
// GSC REPORTS
// ==========================================

const gscReports = {

    "Queries": {
        type: "gsc"
    },

    "Pages": {
        type: "gsc"
    },

    "Countries": {
        type: "gsc"
    },

    "Devices": {
        type: "gsc"
    },

    "Search Appearance": {
        type: "gsc"
    },

    "Days": {
        type: "gsc"
    },

    "Pages Coverage": {
        type: "gsc"
    },

    "Videos Coverage": {
        type: "gsc"
    },

    "Sitemaps": {
        type: "gsc"
    },

    "HTTPS Report": {
        type: "gsc"
    },

    "Core Web Vitals": {
        type: "gsc"
    },

    "Breadcrumb Report": {
        type: "gsc"
    }

};


// ==========================================
// MODULE CHANGE
// ==========================================

moduleSelect.addEventListener(
    "change",
    populateReports
);

function populateReports() {

    reportSelect.innerHTML = `
        <option value="">
            Select Report
        </option>
    `;

    dynamicInputs.innerHTML = "";

    const module =
        moduleSelect.value;

    let reports = {};

    if (
        module === "ga4"
    ) {
        reports =
            ga4Reports;
    }

    if (
        module === "gsc"
    ) {
        reports =
            gscReports;
    }

    Object.keys(reports)
        .forEach(report => {

            const option =
                document.createElement(
                    "option"
                );

            option.value =
                report;

            option.textContent =
                report;

            reportSelect.appendChild(
                option
            );

        });
}


// ==========================================
// REPORT CHANGE
// ==========================================

reportSelect.addEventListener(
    "change",
    generateInputs
);

function generateInputs() {

    dynamicInputs.innerHTML = "";

    const module =
        moduleSelect.value;

    const report =
        reportSelect.value;

    if (!report) return;

    // ----------------------------------
    // GA4 INPUTS
    // ----------------------------------

    if (
        module === "ga4"
    ) {

        dynamicInputs.innerHTML = `

            <div class="form-group">

                <label>
                    Property ID
                </label>

                <input
                    id="propertyId"
                    type="text"
                    value="255658156"
                >

            </div>

            <div class="form-group">

                <label>
                    Start Date
                </label>

               <input
                  id="startDate"
                  type="date"
               >

            </div>

            <div class="form-group">

                <label>
                    End Date
                </label>

               <input
                 id="endDate"
                 type="date"
              >

            </div>

            <div class="form-group">

                <label>
                    Limit
                </label>

                <input
                    id="limit"
                    type="number"
                    value="100"
                >

            </div>

        `;

    }

    // ----------------------------------
    // GSC INPUTS
    // ----------------------------------

    if (
        module === "gsc"
    ) {

        if (
            report ===
            "Core Web Vitals"
        ) {

            dynamicInputs.innerHTML = `

                <div class="form-group">

                    <label>
                        Website URL
                    </label>

                    <input
                        id="url"
                        type="text"
                        value="https://trilliantdigital.com"
                    >

                </div>

            `;

        }

        else {

            dynamicInputs.innerHTML = `

                <div class="form-group">

                    <label>
                        Site URL
                    </label>

                    <input
                        id="siteUrl"
                        type="text"
                        value="trilliantdigital.com"
                    >

                </div>

                <div class="form-group">

                    <label>
                        Start Date
                    </label>

                    <input
                        id="startDate"
                        type="date"
                    >

                </div>

                <div class="form-group">

                    <label>
                        End Date
                    </label>

                    <input
                        id="endDate"
                        type="date"
                    >

                </div>

                <div class="form-group">

                    <label>
                        Row Limit
                    </label>

                    <input
                        id="rowLimit"
                        type="number"
                        value="50"
                    >

                </div>

            `;

        }

    }

}


// ==========================================
// START OVER
// ==========================================

resetBtn.addEventListener(
    "click",
    resetApplication
);

function resetApplication() {

    moduleSelect.value = "";

    reportSelect.innerHTML = `
        <option value="">
            Select Report
        </option>
    `;

    dynamicInputs.innerHTML = "";

    document.getElementById(
        "reportOutput"
    ).innerHTML = `
        <div class="placeholder">
            Select a report and click
            <strong>
                Run Report
            </strong>
        </div>
    `;

}


// ==========================================
// RUN REPORT BUTTON
// ==========================================

const runBtn =
    document.getElementById(
        "runBtn"
    );

const loadingSection =
    document.getElementById(
        "loadingSection"
    );

runBtn.addEventListener(
    "click",
    runReport
);


// ==========================================
// MAIN RUN REPORT FUNCTION
// ==========================================

async function runReport() {

    const module =
        moduleSelect.value;

    const report =
        reportSelect.value;

    if (!module) {

        alert(
            "Please select a module"
        );

        return;
    }

    if (!report) {

        alert(
            "Please select a report"
        );

        return;
    }

    loadingSection.style.display =
        "block";

    try {

        let endpoint = "";

        let payload = {};

        // =====================================
        // GA4
        // =====================================

        if (
            module === "ga4"
        ) {

            endpoint =
                "/ga4/custom-report";

            payload =
                buildGA4Payload(
                    report
                );

        }

        // =====================================
        // GSC
        // =====================================

        if (
            module === "gsc"
        ) {

            const gscData =
                buildGSCPayload(
                    report
                );

            endpoint =
                gscData.endpoint;

            payload =
                gscData.payload;

        }

        console.log(
            "Endpoint:",
            endpoint
        );

        console.log(
            "Payload:",
            payload
        );

        const response =
            await fetch(
                API_BASE +
                endpoint,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body:
                        JSON.stringify(
                            payload
                        )
                }
            );

        if (!response.ok) {
            let detail = `HTTP Error ${response.status}`;
            try {
                const errJson = await response.json();
                if (errJson && errJson.detail) detail = errJson.detail;
            } catch (_) {}
            throw new Error(detail);
        }

        const data =
            await response.json();

        console.log(
            data
        );

        renderReport(
            report,
            data
        );

    }

    catch (error) {

        console.error(error);

        let errorMsg = error.message;

        // Try to extract the real detail from a 500 response
        try {
            const errData = JSON.parse(error._body);
            if (errData && errData.detail) errorMsg = errData.detail;
        } catch (_) {}

        document.getElementById(
            "reportOutput"
        ).innerHTML = `
            <div class="report-block">
                <h3>Error</h3>
                <p>${errorMsg}</p>
            </div>
        `;

    }

    finally {

        loadingSection.style.display =
            "none";

    }

}


// ==========================================
// GA4 PAYLOAD BUILDER
// ==========================================

function buildGA4Payload(
    report
) {

    const propertyId =
        document.getElementById(
            "propertyId"
        ).value;

    const startDate =
        document.getElementById(
            "startDate"
        ).value;

    const endDate =
        document.getElementById(
            "endDate"
        ).value;

    const limit =
        parseInt(
            document.getElementById(
                "limit"
            ).value
        );

    const templates = {

        "Traffic Acquisition": {

            dimensions: [
                "sessionPrimaryChannelGroup",
                "date"
            ],

            metrics: [
                "sessions",
                "activeUsers",
                "newUsers",
                "engagementRate",
                "bounceRate",
                "averageSessionDuration"
            ]
        },

        "User Acquisition": {

            dimensions: [
                "firstUserDefaultChannelGroup"
            ],

            metrics: [
                "newUsers",
                "totalUsers",
                "engagedSessions"
            ]
        },

        "Landing Pages": {

            dimensions: [
                "landingPage"
            ],

            metrics: [
                "sessions",
                "activeUsers",
                "newUsers"
            ]
        },

        "Pages & Screens": {

            dimensions: [
                "pageTitle"
            ],

            metrics: [
                "screenPageViews",
                "activeUsers"
            ]
        },

        "Events": {

            dimensions: [
                "eventName"
            ],

            metrics: [
                "eventCount",
                "totalUsers"
            ]
        },

        "Country Report": {

            dimensions: [
                "country"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "City Report": {

            dimensions: [
                "city"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "Device Report": {

            dimensions: [
                "deviceCategory"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "Browser Report": {

            dimensions: [
                "browser"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "Operating System Report": {

            dimensions: [
                "operatingSystem"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "Source / Medium Report": {

            dimensions: [
                "sessionSourceMedium"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "Campaign Report": {

            dimensions: [
                "sessionCampaignName"
            ],

            metrics: [
                "sessions",
                "activeUsers"
            ]
        },

        "New vs Returning Users": {

            dimensions: [
                "newVsReturning"
            ],

            metrics: [
                "totalUsers",
                "sessions"
            ]
        },

        "Daily Trend Report": {

            dimensions: [
                "date"
            ],

            metrics: [
                "sessions",
                "activeUsers",
                "newUsers"
            ]
        }

    };

    const selected =
        templates[
            report
        ];

    if (
        report ===
        "Custom Report"
    ) {

        alert(
            "Custom Report UI will be added later."
        );

        return null;
    }

    return {

        property_id:
            propertyId,

        dimensions:
            selected.dimensions,

        metrics:
            selected.metrics,

        start_date:
            startDate,

        end_date:
            endDate,

        limit:
            limit

    };

}


// ==========================================
// GSC PAYLOAD BUILDER
// ==========================================

function buildGSCPayload(
    report
) {

    // Core Web Vitals

    if (
        report ===
        "Core Web Vitals"
    ) {

        return {

            endpoint:
                "/gsc/experience/core-web-vitals",

            payload: {

                url:
                    document.getElementById(
                        "url"
                    ).value

            }

        };

    }

    const siteUrl =
        document.getElementById(
            "siteUrl"
        ).value;

    const startDate =
        document.getElementById(
            "startDate"
        ).value;

    const endDate =
        document.getElementById(
            "endDate"
        ).value;

    const rowLimit =
        parseInt(
            document.getElementById(
                "rowLimit"
            ).value
        );

    const payload = {

        site_url:
            siteUrl,

        start_date:
            startDate,

        end_date:
            endDate,

        row_limit:
            rowLimit

    };

    const endpointMap = {

        "Queries":
            "/gsc/performance/queries",

        "Pages":
            "/gsc/performance/pages",

        "Countries":
            "/gsc/performance/countries",

        "Devices":
            "/gsc/performance/devices",

        "Search Appearance":
            "/gsc/performance/search-appearance",

        "Days":
            "/gsc/performance/days",

        "Pages Coverage":
            "/gsc/indexing/pages-report",

        "Videos Coverage":
            "/gsc/indexing/videos-report",

        "Sitemaps":
            "/gsc/indexing/sitemaps",

        "HTTPS Report":
            "/gsc/experience/https",

        "Breadcrumb Report":
            "/gsc/enhancements/breadcrumbs-report"

    };

    return {

        endpoint:
            endpointMap[
                report
            ],

        payload:
            payload

    };

}

// ==========================================
// REPORT RENDERER
// ==========================================

function renderReport(
    reportName,
    data
) {

    const output =
        document.getElementById(
            "reportOutput"
        );

    output.innerHTML = "";

    let html = `
        <div class="report-title">
            ${reportName}
        </div>
    `;

    // =====================================
    // GA4 REPORTS
    // =====================================

    if (data.report) {

        if (
            data.report.length === 0
        ) {

            html += `
                <div class="report-block">
                    No data found.
                </div>
            `;

            output.innerHTML =
                html;

            return;
        }

        html += `
            <table>
                <thead>
                    <tr>
        `;

        const headers =
            Object.keys(
                data.report[0]
            );

        headers.forEach(
            header => {

                html += `
                    <th>
                        ${header}
                    </th>
                `;

            }
        );

        html += `
                    </tr>
                </thead>
                <tbody>
        `;

        data.report.forEach(
            row => {

                html += `
                    <tr>
                `;

                headers.forEach(
                    header => {

                        html += `
                            <td>
                                ${formatValue(
                                    header,
                                    row[header]
                                )}
                            </td>
                        `;

                    }
                );

                html += `
                    </tr>
                `;

            }
        );

        html += `
                </tbody>
            </table>
        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // QUERIES
    // =====================================

    if (data.queries) {

        html += createTable(
            data.queries
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // PAGES
    // =====================================

    if (data.pages) {

        html += createTable(
            data.pages
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // COUNTRIES
    // =====================================

    if (data.countries) {

        html += createTable(
            data.countries
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // DEVICES
    // =====================================

    if (data.devices) {

        html += createTable(
            data.devices
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // SEARCH APPEARANCE
    // =====================================

    if (
        data.search_appearance
    ) {

        html += createTable(
            data.search_appearance
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // DAYS
    // =====================================

    if (data.days) {

        html += createTable(
            data.days
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // PAGE COVERAGE
    // =====================================

    if (
        data.pages_report
    ) {

        const report =
            data.pages_report;

        html += `

            <div class="report-block">

                <div class="report-row">
                    <span class="report-label">
                        Indexed Pages:
                    </span>

                    <span class="report-value">
                        ${report.indexed_pages}
                    </span>
                </div>

                <div class="report-row">
                    <span class="report-label">
                        Not Indexed Pages:
                    </span>

                    <span class="report-value">
                        ${report.not_indexed_pages}
                    </span>
                </div>

                <div class="report-row">
                    <span class="report-label">
                        Coverage:
                    </span>

                    <span class="report-value">
                        ${report.index_coverage}%
                    </span>
                </div>

            </div>

        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // VIDEO COVERAGE
    // =====================================

    if (
        data.videos_report
    ) {

        const report =
            data.videos_report;

        html += `

            <div class="report-block">

                <div class="report-row">
                    <span class="report-label">
                        Pages With Video:
                    </span>

                    <span class="report-value">
                        ${report.pages_with_video}
                    </span>
                </div>

                <div class="report-row">
                    <span class="report-label">
                        Pages Without Video:
                    </span>

                    <span class="report-value">
                        ${report.pages_without_video}
                    </span>
                </div>

                <div class="report-row">
                    <span class="report-label">
                        Video Coverage:
                    </span>

                    <span class="report-value">
                        ${report.video_coverage}%
                    </span>
                </div>

            </div>

        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // HTTPS REPORT
    // =====================================

    if (
        data.https
    ) {

        const report =
            data.https;

        html += `

            <div class="report-block">

                ${renderObject(
                    report
                )}

            </div>

        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // CORE WEB VITALS
    // =====================================

    if (
        data.core_web_vitals
    ) {

        html += `

            <div class="report-block">

                ${renderObject(
                    data.core_web_vitals
                )}

            </div>

        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // BREADCRUMBS
    // =====================================

    if (
        data.breadcrumbs_report
    ) {

        html += `

            <div class="report-block">

                ${renderObject(
                    data.breadcrumbs_report
                )}

            </div>

        `;

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // SITEMAPS
    // =====================================

    if (
        data.sitemaps
    ) {

        html += createTable(
            data.sitemaps
        );

        output.innerHTML =
            html;

        return;
    }

    // =====================================
    // FALLBACK
    // =====================================

    html += `
        <pre>
            ${JSON.stringify(
                data,
                null,
                2
            )}
        </pre>
    `;

    output.innerHTML =
        html;

}
// ==========================================
// VALUE FORMATTER
// ==========================================

function formatValue(
    key,
    value
) {

    if (
        value === null ||
        value === undefined
    ) {
        return "-";
    }

    // Check numeric values
    if (
        !isNaN(value) &&
        value !== ""
    ) {

        value =
            Number(value);

        // CTR, Bounce Rate, Engagement Rate
        if (
            key.toLowerCase().includes("ctr") ||
            key.toLowerCase().includes("rate")
        ) {

            return (
                Math.round(value * 100) + "%"
            );

        }

        // Everything else
        return Math.round(value);

    }

    return value;
}


// ==========================================
// OBJECT RENDERER
// ==========================================

function renderObject(obj) {
    if (!obj || typeof obj !== "object") return `<p>${obj}</p>`;
    return Object.entries(obj).map(([k, v]) => `
        <div class="report-row">
            <span class="report-label">${k.replace(/_/g, " ")}:</span>
            <span class="report-value">${v}</span>
        </div>
    `).join("");
}


// ==========================================
// TABLE CREATOR
// ==========================================

function createTable(
    rows
) {

    if (
        !rows ||
        rows.length === 0
    ) {

        return `
            <div class="report-block">
                No Data Found
            </div>
        `;

    }

    let html = `
        <table>
            <thead>
                <tr>
    `;

    const headers =
        Object.keys(
            rows[0]
        );

    // TABLE HEADERS

    headers.forEach(
        header => {

            html += `
                <th>
                    ${header}
                </th>
            `;

        }
    );

    html += `
                </tr>
            </thead>

            <tbody>
    `;

    // TABLE ROWS

    rows.forEach(
        row => {

            html += `
                <tr>
            `;

            headers.forEach(
                header => {

                    html += `
                        <td>
                            ${formatValue(
                                header,
                                row[header]
                            )}
                        </td>
                    `;

                }
            );

            html += `
                </tr>
            `;

        }
    );

    html += `
            </tbody>
        </table>
    `;

    return html;

}