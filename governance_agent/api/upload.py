import os
import json

from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import Form

router = APIRouter()


@router.post("/upload_notice")
async def upload_notice(

    company_name: str = Form(""),

    fiscal_year: str = Form(""),

    file: UploadFile = File(...)

):

    # Create storage folder

    folder = "storage/notices"

    os.makedirs(
        folder,
        exist_ok=True
    )

    # Save uploaded PDF

    file_path = os.path.join(
        folder,
        "latest.pdf"
    )

    with open(
        file_path,
        "wb"
    ) as f:

        content = await file.read()

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

        "storage/session.json",

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