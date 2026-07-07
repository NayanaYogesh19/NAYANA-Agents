"""FastAPI wrapper around the existing agent pipeline.

This is purely a thin HTTP layer: it does not reimplement discovery,
extraction, classification, or archiving — it just exposes
agent.pipeline.run() as a submit-then-poll job API for the frontend.
Run with: uvicorn server.app:app --reload --port 8000
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from server.jobs import create_job, get_job
from server.schemas import JobStatusOut, ReportOut, RunAccepted, RunRequest

app = FastAPI(title="PR & Events Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/runs", response_model=RunAccepted)
def start_run(req: RunRequest) -> RunAccepted:
    if req.end < req.start:
        raise HTTPException(status_code=422, detail="end date must not be before start date")
    job = create_job(req.company_url, req.start, req.end)
    return RunAccepted(job_id=job.id)


@app.get("/api/runs/{job_id}", response_model=JobStatusOut)
def get_run(job_id: str) -> JobStatusOut:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown job id")

    report_out = None
    if job.report is not None:
        report_out = ReportOut(**job.report.model_dump())

    return JobStatusOut(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        error=job.error,
        report=report_out,
    )
