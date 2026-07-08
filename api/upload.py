import os
import json

from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import Form
from fastapi import HTTPException
from config.storage import NOTICES_DIR, REPORTS_DIR, SESSION_PATH

router = APIRouter()

MAX_UPLOAD_SIZE = 30 * 1024 * 1024  # 30 MB


@router.post("/upload_notice")
async def upload_notice(

    company_name: str = Form(""),

    fiscal_year: str = Form(""),

    file: UploadFile = File(...)

):

    # Create storage folder

    folder = NOTICES_DIR

    os.makedirs(
        folder,
        exist_ok=True
    )

    # Save uploaded PDF

    file_path = os.path.join(
        folder,
        "latest.pdf"
    )

    content = await file.read()

    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
        )

    with open(
        file_path,
        "wb"
    ) as f:

        f.write(content)

    # Create session

    session = {

        "company_name": company_name,

        "financial_year": fiscal_year,

        "pdf_path": file_path,

        "status": "uploaded"

    }

    # Save session

    with open(

        SESSION_PATH,

        "w",

        encoding="utf-8"

    ) as f:

        json.dump(

            session,

            f,

            indent=4

        )

    # Return response

    return {

        "status": "uploaded",

        "company_name": company_name,

        "financial_year": fiscal_year,

        "filename": "latest.pdf",

        "session": session

    }