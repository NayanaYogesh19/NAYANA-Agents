from fastapi import FastAPI
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel

from agents.seo_optimizer import run_seo_agent

from tools.excel_exporter import export_excel

import os


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------------------
# REQUEST MODEL
# -----------------------------------

class SEORequest(BaseModel):

    website_url: str

    company_name: str

    max_pages: int = 5


# -----------------------------------
# HOME
# -----------------------------------

@app.get("/")
async def root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/download-excel")
async def download_excel():
    file_path = os.path.join("output", "seo_report.xlsx")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename="seo_report.xlsx"
        )
    return {"error": "No report generated yet"}


# -----------------------------------
# ANALYZE
# -----------------------------------

@app.post("/analyze")

async def analyze(request: SEORequest):

    # RUN SEO AGENT

    results = await run_seo_agent(

        request.website_url,

        request.company_name,

        request.max_pages
    )

    # -----------------------------------
    # GENERATE EXCEL
    # -----------------------------------

    excel_file = export_excel(results)

    # -----------------------------------
    # RETURN RESPONSE
    # -----------------------------------

    return {

        "results": results,

        "excel_file": excel_file
    }