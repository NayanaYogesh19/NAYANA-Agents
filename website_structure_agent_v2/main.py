"""
main.py — FastAPI server for the Website Structure Planning Agent.
AI: Claude Haiku via OpenRouter | Scraping: Tavily API | PDF: ReportLab
"""
import os
import uuid
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models import AgentRequest, AgentOutput, AnalysisMode, BusinessType, BusinessGoal

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title       = "Website Structure Planning Agent",
    description = "AI-powered website architecture planner — LangChain + Claude Haiku (OpenRouter) + Tavily",
    version     = "2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_jobs:    Dict[str, AgentOutput] = {}
_executor = ThreadPoolExecutor(max_workers=4)


# ── Request / Response schemas ────────────────────────────────────────────────

class RunRequest(BaseModel):
    target_url:      str
    mode:            str
    business_type:   str
    business_goal:   str
    custom_goal:     Optional[str]       = None
    business_desc:   Optional[str]       = None
    competitor_urls: List[str]           = []
    audit_text:      Optional[str]       = None


class RunResponse(BaseModel):
    job_id:  str
    status:  str
    message: str


class StatusResponse(BaseModel):
    job_id:     str
    status:     str
    mode:       Optional[str]  = None
    target_url: Optional[str]  = None
    pdf_ready:  bool           = False
    error:      Optional[str]  = None
    summary:    Optional[dict] = None


# ── Background worker ─────────────────────────────────────────────────────────

def _run_sync(job_id: str, request: AgentRequest, business_desc: Optional[str]):
    from agents.structure_agent import run_agent
    # Attach business_desc dynamically since it's not in the Pydantic model
    request.__dict__['business_desc'] = business_desc or ''
    try:
        _jobs[job_id] = run_agent(request)
    except Exception as e:
        logger.error(f"Job {job_id} crashed: {e}", exc_info=True)
        _jobs[job_id] = AgentOutput(
            mode          = request.mode.value,
            target_url    = request.target_url,
            business_type = request.business_type.value,
            business_goal = request.business_goal.value,
            status        = "error",
            error         = str(e),
        )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/api/run", response_model=RunResponse)
async def run_analysis(body: RunRequest):
    # Validate business_goal — allow any string (custom goals pass through)
    try:
        goal_enum = BusinessGoal(body.business_goal)
    except ValueError:
        goal_enum = BusinessGoal.CUSTOM

    # For new_structure, competitor_urls is optional (can be empty)
    try:
        req = AgentRequest(
            target_url      = body.target_url,
            mode            = AnalysisMode(body.mode),
            business_type   = BusinessType(body.business_type),
            business_goal   = goal_enum,
            custom_goal     = body.custom_goal,
            competitor_urls = body.competitor_urls or [],
            audit_text      = body.audit_text,
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = str(uuid.uuid4())
    _jobs[job_id] = AgentOutput(
        mode=body.mode, target_url=body.target_url,
        business_type=body.business_type,
        business_goal=body.custom_goal if body.business_goal == 'Custom' and body.custom_goal else body.business_goal,
        status="running",
    )

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_executor, _run_sync, job_id, req, body.business_desc)

    logger.info(f"Job {job_id} started | mode={body.mode} | target={body.target_url}")
    return RunResponse(
        job_id  = job_id,
        status  = "running",
        message = f"Analysis started. Poll /api/status/{job_id} for updates.",
    )


@app.get("/api/status/{job_id}", response_model=StatusResponse)
async def get_status(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = _jobs[job_id]
    summary = None
    if job.status == "complete" and job.structure_plan:
        p = job.structure_plan
        # Count real discovered URLs from scraped target
        urls_discovered = len(job.scraped_target.url_endpoints) if job.scraped_target else 0
        summary = {
            "total_pages":        len(p.pages),
            "recommendations":    len(p.recommendations),
            "conversion_paths":   len(p.conversion_paths),
            "competitor_count":   len(job.scraped_competitors),
            "urls_discovered":    urls_discovered,
            "has_audit_findings": job.audit_findings is not None,
        }
    return StatusResponse(
        job_id     = job_id,
        status     = job.status,
        mode       = job.mode,
        target_url = job.target_url,
        pdf_ready  = bool(job.pdf_path and os.path.exists(job.pdf_path or "")),
        error      = job.error,
        summary    = summary,
    )


@app.get("/api/download/{job_id}")
async def download_pdf(job_id: str):
    if job_id not in _jobs:
        raise HTTPException(status_code=404, detail="Job not found.")
    job = _jobs[job_id]
    if job.status != "complete":
        raise HTTPException(status_code=400, detail=f"Job is '{job.status}', not complete.")
    if not job.pdf_path or not os.path.exists(job.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found.")
    return FileResponse(
        job.pdf_path,
        media_type = "application/pdf",
        filename   = os.path.basename(job.pdf_path),
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "2.0.0", "model": "claude-haiku-4-5 via OpenRouter"}


@app.get("/", response_class=HTMLResponse)
async def frontend():
    html_path = os.path.join(os.path.dirname(__file__), "frontend", "index.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse("<h2>Frontend not found.</h2>")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.host, port=settings.port,
                reload=settings.debug, workers=1)
