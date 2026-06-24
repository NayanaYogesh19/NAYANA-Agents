import os
import json

from fastapi import APIRouter
from fastapi.responses import FileResponse, HTMLResponse

from report_generator.generate_pdf import generate_pdf_report

router = APIRouter()


@router.get("/generate_report")
async def generate_report_endpoint():
    """
    Generate a PDF (or HTML fallback) governance report from the current
    approved or analyzed session.

    Returns a downloadable file when the report is generated successfully.
    """
    session_path = "storage/session.json"

    if not os.path.exists(session_path):
        return {
            "status":  "error",
            "message": "No active session. Please upload a notice first.",
        }

    with open(session_path, "r", encoding="utf-8") as f:
        session = json.load(f)

    resolutions = session.get("resolutions", [])
    if not resolutions:
        return {
            "status":  "error",
            "message": "No resolutions found. Run /extract_resolutions first.",
        }

    result = generate_pdf_report(session)

    if result["status"] == "error":
        return {
            "status":  "error",
            "message": result["message"],
        }

    if result["status"] == "html_only":
        html_content = result.get("html_content", "")
        return HTMLResponse(
            content=html_content,
            status_code=200,
            headers={
                "Content-Disposition": f'attachment; filename="{result["filename"]}"'
            },
        )

    # PDF success — stream the file
    filepath = result["filepath"]
    if not os.path.exists(filepath):
        return {
            "status":  "error",
            "message": f"Generated file not found at {filepath}",
        }

    return FileResponse(
        path=filepath,
        media_type="application/pdf",
        filename=result["filename"],
    )


@router.get("/download_report/{filename}")
async def download_report(filename: str):
    """
    Download a previously generated report by filename from storage/reports/.
    """
    filepath = os.path.join("storage/reports", filename)

    if not os.path.exists(filepath):
        return {"status": "error", "message": "File not found."}

    media_type = "application/pdf" if filename.endswith(".pdf") else "text/html"

    return FileResponse(
        path=filepath,
        media_type=media_type,
        filename=filename,
    )
