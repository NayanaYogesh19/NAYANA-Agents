"""In-memory job store for pipeline runs.

The pipeline takes minutes (crawl + search + LLM calls + optional
Wayback polling), so the API hands back a job id immediately and runs
the actual work on a background thread; the frontend polls for status.
No persistence needed — jobs live only as long as the server process,
which matches this being a single-user local tool.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from agent.models import CompanyReport
from agent.pipeline import run as run_pipeline

JobStatus = str  # "pending" | "running" | "done" | "error"


@dataclass
class Job:
    id: str
    company_url: str
    period_start: date
    period_end: date
    status: JobStatus = "pending"
    stage: str = "Queued"
    error: Optional[str] = None
    report: Optional[CompanyReport] = None
    lock: threading.Lock = field(default_factory=threading.Lock)


_jobs: dict[str, Job] = {}


def _execute(job: Job) -> None:
    job.status = "running"

    def on_progress(stage: str) -> None:
        job.stage = stage

    try:
        report = run_pipeline(
            job.company_url, job.period_start, job.period_end, on_progress=on_progress
        )
        job.report = report
        job.status = "done"
        job.stage = "Done"
    except Exception as exc:  # surfaced to the UI, never crashes the server
        job.status = "error"
        job.error = str(exc)


def create_job(company_url: str, start: date, end: date) -> Job:
    job = Job(id=str(uuid.uuid4()), company_url=company_url, period_start=start, period_end=end)
    _jobs[job.id] = job
    thread = threading.Thread(target=_execute, args=(job,), daemon=True)
    thread.start()
    return job


def get_job(job_id: str) -> Optional[Job]:
    return _jobs.get(job_id)
