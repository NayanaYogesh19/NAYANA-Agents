from typing import List, Optional
from pydantic import BaseModel, Field


# ----------------------------
# Industrial Website Schemas
# ----------------------------

class MachineSpec(BaseModel):
    name: str
    build_envelope_mm: str


class WorkflowStep(BaseModel):
    step_no: int
    title: str
    description: str


class PageInsights(BaseModel):
    company: str
    page_title: str
    value_proposition: List[str]
    technologies: List[str]
    materials: List[str]
    machines: List[MachineSpec]
    workflow_steps: List[WorkflowStep]
    target_industries: List[str]
    strengths: List[str]
    risks_or_gaps: List[str]
    buyer_questions: List[str]
    short_summary: str


# ----------------------------
# Meta Ads Library Schemas
# ----------------------------

class AdRecord(BaseModel):
    advertiser: Optional[str]
    ad_text: Optional[str]
    platforms: List[str] = []
    status: Optional[str]
    start_date: Optional[str]
    ad_url: Optional[str]
    screenshot_path: Optional[str]
    raw_card_text: Optional[str]


class AdLibraryResult(BaseModel):
    query: str
    country: str
    category: str
    total_ads_collected: int
    ads: List[AdRecord]
    summary: str
    insights: List[str]