from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.agent import agent

from fastapi.responses import FileResponse

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer
)

from reportlab.lib.styles import getSampleStyleSheet

import re


app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

templates = Jinja2Templates(
    directory="templates"
)


class ChatRequest(BaseModel):
    message: str


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.post("/chat")
async def chat(req: ChatRequest):

    response = agent(req.message)

    return response


@app.post("/download-pdf")
async def download_pdf(req: ChatRequest):

    pdf_file = "generated_content.pdf"

    doc = SimpleDocTemplate(pdf_file)

    styles = getSampleStyleSheet()

    story = []

    content = req.message

    content = re.sub(
        r"(##\s)",
        r"\n\1",
        content
    )

    content = re.sub(
        r"(#\s)",
        r"\n\1",
        content
    )

    lines = content.split("\n")

    for line in lines:

        line = line.strip()

        if not line:
            continue

        if line.startswith("# "):

            story.append(
                Paragraph(
                    line.replace("# ", ""),
                    styles["Heading1"]
                )
            )

        elif line.startswith("## "):

            story.append(
                Paragraph(
                    line.replace("## ", ""),
                    styles["Heading2"]
                )
            )

        else:

            story.append(
                Paragraph(
                    line,
                    styles["BodyText"]
                )
            )

        story.append(
            Spacer(1, 8)
        )

    doc.build(story)

    return FileResponse(
        pdf_file,
        media_type="application/pdf",
        filename="generated_content.pdf"
    )