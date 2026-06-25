import os

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from app.services.new_sitemap_service import get_service_product_urls
from app.services.new_se_ranking_service import get_ranking_keywords, pick_top_keywords
from app.services.new_excel_service import export_to_excel

app = FastAPI(title="SEO Keyword Research")

app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

OUTPUT_FILE = "reports/SEO_keyword_research_new.xlsx"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="new_index.html",
        context={"request": request}
    )


@app.post("/generate-report")
async def generate_report(
    website_url: str = Form(...),
    country: str = Form(...)
):
    print("=" * 60)
    print("GENERATE REPORT")
    print("WEBSITE:", website_url)
    print("COUNTRY:", country)
    print("=" * 60)

    pages = get_service_product_urls(website_url)

    if not pages:
        return {"error": "No service or product pages found in sitemap."}

    rows = []

    for page in pages:
        page_url = page["url"]

        raw_keywords = get_ranking_keywords(page_url, country)

        if not raw_keywords:
            print(f"NO RANKING KEYWORDS: {page_url}")
            continue

        top_keywords = pick_top_keywords(raw_keywords, n=15)

        for kw in top_keywords:
            rows.append({
                "Page URL": page_url,
                "Keyword": kw.get("keyword", ""),
                "Position": kw.get("position", ""),
                "Volume": kw.get("volume", ""),
                "Difficulty": kw.get("difficulty", ""),
                "CPC": kw.get("cpc", ""),
                "Competition": kw.get("competition", ""),
                "Traffic": kw.get("traffic", "")
            })

    if not rows:
        return {"error": "No ranking keywords found for any page. The domain may not have indexed data in SE Ranking for this country."}

    os.makedirs("reports", exist_ok=True)
    export_to_excel(rows, OUTPUT_FILE)

    print("=" * 60)
    print("DONE — ROWS:", len(rows))
    print("=" * 60)

    return FileResponse(
        path=OUTPUT_FILE,
        filename="SEO_keyword_research.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
