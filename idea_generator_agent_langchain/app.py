from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from agents.input_parser import parse_input
from agents.website_fetcher import fetch_website
from agents.html_extractor import extract_html_content
from agents.keyword_extractor import extract_keywords
from agents.google_trends import get_google_trends
from agents.merge import merge_data
from agents.content_generator import generate_content
from agents.json_validator import validate_json
from agents.google_sheet import update_google_sheet

app = FastAPI(
    title="Idea Generator Agent",
    version="1.0.0",
    description="LangChain version of the n8n Idea Generator Agent"
)

class IdeaRequest(BaseModel):
    website_url: str
    domain: str
    topic: str
    lead_magnet: str = "none"


@app.get("/", response_class=HTMLResponse)
def root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.post("/generate-ideas")
def generate_ideas(request: IdeaRequest):

    try:

        # -------------------------------------------------
        # STEP 1
        # Input Parser
        # (Same as Code in JavaScript node)
        # -------------------------------------------------

        parsed_data = parse_input(
            website_url=request.website_url,
            domain=request.domain,
            topic=request.topic,
            lead_magnet=request.lead_magnet
        )

        # -------------------------------------------------
        # STEP 2
        # HTTP Request Node
        # -------------------------------------------------

        html = fetch_website(parsed_data["website_url"])

        # -------------------------------------------------
        # STEP 3
        # HTML Extract Node
        # -------------------------------------------------

        extracted_data = extract_html_content(html)

        # -------------------------------------------------
        # STEP 4
        # Keyword Extraction
        # -------------------------------------------------

        keyword_data = extract_keywords(
            extracted_data,
            parsed_data
        )

        # -------------------------------------------------
        # STEP 5
        # Google Trends
        # -------------------------------------------------

        trends = get_google_trends(
            topic=parsed_data["topic"],
            domain=parsed_data["domain"],
            keywords=keyword_data.get("keywords", [])
        )

        # -------------------------------------------------
        # STEP 6
        # Merge Node
        # -------------------------------------------------

        merged_data = merge_data(
            keyword_data,
            trends
        )

        # -------------------------------------------------
        # STEP 7
        # AI Agent
        # -------------------------------------------------

        ai_output = generate_content(
            merged_data
        )

        # -------------------------------------------------
        # STEP 8
        # JSON Validation
        # -------------------------------------------------

        validated_output = validate_json(
            ai_output,
            parsed_data["lead_magnet"]
        )

        # -------------------------------------------------
        # STEP 9
        # Google Sheets (non-blocking — ideas returned even if sheet fails)
        # -------------------------------------------------

        sheet_status = "success"
        sheet_error  = None

        try:
            update_google_sheet(validated_output)
        except Exception as sheet_err:
            sheet_status = "skipped"
            sheet_error  = str(sheet_err)

        # -------------------------------------------------
        # Final Response
        # -------------------------------------------------

        response_data = {
            "status": "success",
            "total_ideas": len(validated_output),
            "ideas": validated_output,
            "sheet_status": sheet_status,
        }

        if sheet_error:
            response_data["sheet_error"] = sheet_error

        return response_data

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )