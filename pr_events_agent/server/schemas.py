"""API request/response models — separate from agent/models.py, which
are the pipeline's internal schemas. Keeping them apart means the API
contract doesn't silently change if the pipeline's internals do.
"""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field

from agent.models import Category, Confidence, SourceType


class RunRequest(BaseModel):
    company_url: str = Field(description="Company website URL, e.g. https://example.com")
    start: date
    end: date


class RunAccepted(BaseModel):
    job_id: str


class ReportItemOut(BaseModel):
    category: Category
    title: str
    url: str
    published_date: Optional[date] = None
    source_type: SourceType
    confidence: Confidence
    archived_url: Optional[str] = None


class ReportOut(BaseModel):
    company_name: str
    company_url: str
    period_start: date
    period_end: date
    press_releases: List[ReportItemOut]
    webinars: List[ReportItemOut]
    events: List[ReportItemOut]
    awards: List[ReportItemOut]


class JobStatusOut(BaseModel):
    job_id: str
    status: str
    stage: str
    error: Optional[str] = None
    report: Optional[ReportOut] = None
