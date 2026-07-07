"""Pydantic schemas shared across the pipeline.

These are the structured objects the LLM is asked to return (via
with_structured_output) and the objects the output writers consume.
"""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Category = Literal["press_release", "webinar", "event", "award"]
SourceType = Literal["company_site", "search"]
Confidence = Literal["verified", "unverified"]

CATEGORY_LABELS = {
    "press_release": "Press Releases",
    "webinar": "Webinars",
    "event": "Events / Exhibitions",
    "award": "Awards / Wins",
}


class ReportItem(BaseModel):
    """A single found item (one press release, one webinar, etc.)."""

    category: Category = Field(description="Which of the 4 report columns this belongs to")
    title: str = Field(description="Short headline in the style of a report table, e.g. "
                                    "\"Company X partners with Y to launch Z\"")
    url: str = Field(description="Direct URL to the source article/page")
    published_date: Optional[date] = Field(
        default=None, description="Best-guess publish date of the source, if determinable"
    )
    source_type: SourceType = "search"
    confidence: Confidence = "unverified"
    archived_url: Optional[str] = Field(
        default=None, description="Wayback Machine snapshot URL, filled in after archiving"
    )


class CandidatePage(BaseModel):
    """A page found by crawling or search, not yet classified."""

    url: str
    title: Optional[str] = None
    text: Optional[str] = None
    published_date: Optional[date] = None
    date_is_exact: bool = Field(
        default=False,
        description="True if published_date came from real on-page date metadata "
                     "(strict htmldate). False if it's a weaker fallback (sitemap "
                     "lastmod) or unset entirely.",
    )
    source_type: SourceType = "search"
    sitemap_lastmod: Optional[date] = Field(
        default=None,
        description="lastmod from the site's own sitemap.xml, if present — a real "
                     "signal (unlike htmldate's in-page heuristics), used only as a "
                     "fallback when no genuine publish date is found on the page itself",
    )


class CompanyReport(BaseModel):
    """The final output for one company + one reporting period."""

    company_name: str
    company_url: str
    period_start: date
    period_end: date
    press_releases: List[ReportItem] = []
    webinars: List[ReportItem] = []
    events: List[ReportItem] = []
    awards: List[ReportItem] = []

    def items_by_category(self) -> dict:
        return {
            "press_release": self.press_releases,
            "webinar": self.webinars,
            "event": self.events,
            "award": self.awards,
        }

    def add(self, item: ReportItem) -> None:
        bucket = {
            "press_release": self.press_releases,
            "webinar": self.webinars,
            "event": self.events,
            "award": self.awards,
        }[item.category]
        bucket.append(item)
