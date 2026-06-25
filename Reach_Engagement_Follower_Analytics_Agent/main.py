from fastapi import FastAPI
from fastapi import Request

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from agents.analytics_agent import ReachAnalyticsAgent


app = FastAPI(
    title="Reach Engagement Analytics Agent"
)


templates = Jinja2Templates(
    directory="templates"
)


app.mount(
    "/static",
    StaticFiles(
        directory="static"
    ),
    name="static"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyticsRequest(BaseModel):

    instagram_url: str = ""

    facebook_url: str = ""

    linkedin_url: str = ""

    youtube_url: str = ""


@app.get(
    "/",
    response_class=HTMLResponse
)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="index.html"
    )


@app.post("/analyze")
def analyze(request: AnalyticsRequest):

    agent = ReachAnalyticsAgent()

    result = agent.run(

        instagram_url=request.instagram_url,

        facebook_url=request.facebook_url,

        linkedin_url=request.linkedin_url,

        youtube_url=request.youtube_url
    )

    return result