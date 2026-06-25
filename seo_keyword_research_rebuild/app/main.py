
from fastapi import (
    FastAPI,
    Request,
    Form
)

from fastapi.responses import (
    HTMLResponse,
    FileResponse
)

from fastapi.templating import (
    Jinja2Templates
)

from fastapi.staticfiles import (
    StaticFiles
)

from app.services.sitemap_discovery import (
    discover_sitemap
)

from app.services.sitemap_crawler import (
    crawl_sitemap
)

from app.services.se_ranking_keyword_service import (

    fetch_related_keywords,

    infer_category_from_keywords
)

from app.services.se_ranking_bulk_service import (
    get_bulk_keyword_metrics
)

from app.services.competitor_matcher import (
    match_competitor_products
)

from app.services.excel_export_service import (
    export_excel
)

# =========================================
# FASTAPI
# =========================================

app = FastAPI(
    title="SEO Keyword Research Agent"
)

# =========================================
# STATIC
# =========================================

app.mount(

    "/static",

    StaticFiles(
        directory="app/static"
    ),

    name="static"
)

# =========================================
# TEMPLATES
# =========================================

templates = Jinja2Templates(
    directory="app/templates"
)

# =========================================
# HOME
# =========================================

@app.get(
    "/",
    response_class=HTMLResponse
)
async def home(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="index.html",

        context={
            "request": request
        }
    )

# =========================================
# GENERATE REPORT
# =========================================

@app.post("/generate-report")
async def generate_report(

    website_url: str = Form(...),

    competitors: str = Form(...)
):

    print("=" * 60)
    print("GENERATE REPORT CALLED")
    print("WEBSITE:", website_url)
    print("COMPETITORS:", competitors)
    print("=" * 60)

    competitor_urls = [

        x.strip()

        for x in competitors.split(",")

        if x.strip()
    ]

    # =====================================
    # MAIN WEBSITE
    # =====================================

    main_sitemap = discover_sitemap(
        website_url
    )

    if not main_sitemap:

        return {
            "error":
            "Main sitemap not found"
        }

    print(
        "MAIN SITEMAP:",
        main_sitemap
    )

    main_products = crawl_sitemap(
        main_sitemap
    )

    print(
        "MAIN PRODUCTS:",
        len(main_products)
    )

    # =====================================
    # COMPETITORS
    # =====================================

    competitor_products = []

    for competitor in competitor_urls:

        try:

            competitor_sitemap = discover_sitemap(
                competitor
            )

            if not competitor_sitemap:

                continue

            products = crawl_sitemap(
                competitor_sitemap
            )

            competitor_products.extend(
                products
            )

            print(
                "COMPETITOR PRODUCTS:",
                competitor,
                len(products)
            )

        except Exception as e:

            print(
                "COMPETITOR ERROR:",
                e
            )

    # =====================================
    # FINAL ROWS
    # =====================================

    final_rows = []

    for product in main_products:

        try:

            keywords = fetch_related_keywords(
                product["product"]
            )

            if not keywords:
                continue

            category = infer_category_from_keywords(
                keywords
            )

            metrics = get_bulk_keyword_metrics(
                keywords
            )

            metrics = match_competitor_products(

                metrics,

                competitor_products
            )

            for metric in metrics:

                final_rows.append({

                    "Keyword":
                    metric.get("keyword", ""),

                    "Cluster / Category":
                    category,

                    "Vol/mo (India)":
                    metric.get("volume", 0),

                    "KD Score":
                    metric.get("kd_score", 0),

                    "KD Level":
                    metric.get("kd_level", ""),

                    "Intent":
                    metric.get("intent", ""),

                    "CPC (₹)":
                    metric.get("cpc", 0),

                    "Competition":
                    metric.get("competition", 0),

                    "Trend / Seasonality":
                    metric.get("trend", ""),

                    "SERP Features":
                    metric.get("serp_features", ""),

                    "Competitor Usage":
                    metric.get(
                        "competitor_usage",
                        ""
                    ),

                    "Competitor Product URL":
                    metric.get(
                        "competitor_product_url",
                        ""
                    ),

                    "Main Website Product":
                    product.get("product", ""),

                    "Main Website Product URL":
                    product.get("url", ""),

                    "Google Rank":
                    "Not Ranked",

                    "Notes / Opportunities":
                    "SEO opportunity keyword"
                })

        except Exception as e:

            print(
                "PRODUCT ERROR:",
                e
            )

    # =====================================
    # EXPORT
    # =====================================

    output_file = (
        "reports/SEO_keyword_research.xlsx"
    )

    export_excel(

        final_rows,

        output_file
    )

    print("=" * 60)
    print("EXCEL GENERATED")
    print("ROWS:", len(final_rows))
    print("=" * 60)

    return FileResponse(

        path=output_file,

        filename="SEO_keyword_research.xlsx",

        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    )
