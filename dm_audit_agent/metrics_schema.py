"""
metrics_schema.py — defines the manual-entry metric fields shown in the UI,
replacing the SE Ranking API (removed entirely). The user reads these values
off their own SE Ranking / Google Ads / Meta Ads Manager dashboards and types
them in; nothing here is fetched automatically.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SeoMetrics(BaseModel):
    """Mirrors the 8 KPI cards on the Vertiv PDF 'Key Metrics Overview' slide."""

    health_score: Optional[float] = Field(None, description="Health Score /100")
    organic_traffic: Optional[float] = Field(None, description="Organic Traffic (monthly visits)")
    organic_keywords: Optional[float] = Field(None, description="Organic Keywords ranked")
    passed_checks: Optional[float] = Field(None, description="Passed Checks")
    crawled_pages: Optional[float] = Field(None, description="Crawled Pages")
    errors: Optional[float] = Field(None, description="Total Errors")
    warnings: Optional[float] = Field(None, description="Total Warnings")
    notices: Optional[float] = Field(None, description="Total Notices")


class PpcMetrics(BaseModel):
    """Manual performance-marketing entry, no ad-platform API dependency."""

    ad_spend: Optional[float] = Field(None, description="Ad Spend")
    impressions: Optional[float] = Field(None, description="Impressions")
    clicks: Optional[float] = Field(None, description="Clicks")
    ctr: Optional[float] = Field(None, description="CTR %")
    cpc: Optional[float] = Field(None, description="CPC")
    conversions: Optional[float] = Field(None, description="Conversions")
    conversion_rate: Optional[float] = Field(None, description="Conversion Rate %")
    roas: Optional[float] = Field(None, description="ROAS")


class SmmMetrics(BaseModel):
    """Manual social-media entry (used alongside Tavily-researched competitor
    data; the client's own numbers are not reliably scrapable)."""

    linkedin_followers: Optional[float] = Field(None, description="LinkedIn Followers")
    posts_per_month: Optional[float] = Field(None, description="Posts per Month")
    engagement_rate: Optional[float] = Field(None, description="Engagement Rate %")


SEO_FIELD_LABELS: dict[str, str] = {
    "health_score": "Health Score",
    "organic_traffic": "Organic Traffic",
    "organic_keywords": "Organic Keywords",
    "passed_checks": "Passed Checks",
    "crawled_pages": "Crawled Pages",
    "errors": "Errors",
    "warnings": "Warnings",
    "notices": "Notices",
}

PPC_FIELD_LABELS: dict[str, str] = {
    "ad_spend": "Ad Spend",
    "impressions": "Impressions",
    "clicks": "Clicks",
    "ctr": "CTR %",
    "cpc": "CPC",
    "conversions": "Conversions",
    "conversion_rate": "Conversion Rate %",
    "roas": "ROAS",
}

SMM_FIELD_LABELS: dict[str, str] = {
    "linkedin_followers": "LinkedIn Followers",
    "posts_per_month": "Posts per Month",
    "engagement_rate": "Engagement Rate %",
}


def fmt(value: Optional[float]) -> str:
    """Render a manually-entered numeric value the way the reference PDFs
    display metrics (e.g. 4900 -> '4.9K'), or 'Data not available' if unset."""
    if value is None:
        return "Data not available"
    if value == int(value):
        value = int(value)
    if isinstance(value, int) and abs(value) >= 1000:
        return f"{value / 1000:.1f}K".replace(".0K", "K")
    return str(value)
