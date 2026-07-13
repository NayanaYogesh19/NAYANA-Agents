"""
metrics_schema.py — defines the metric fields shown on the Key Metrics
Overview slide for each category.

SEO and PPC metrics are manually entered by the user (read off their own SE
Ranking / Google Ads / Meta Ads Manager dashboards) — no external SEO API
dependency. SMM metrics are auto-fetched (see agents/smm_metrics_agent.py:
Tavily profile discovery + Apify scraping across Instagram, Facebook,
LinkedIn, YouTube) — no manual entry, no SMM input fields in the UI.
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
    """Auto-fetched social-media metrics (Tavily profile discovery + Apify
    scraping) — no manual entry. See agents/smm_metrics_agent.py."""

    instagram_followers: Optional[float] = Field(None, description="Instagram Followers")
    facebook_followers: Optional[float] = Field(None, description="Facebook Followers")
    linkedin_followers: Optional[float] = Field(None, description="LinkedIn Followers")
    youtube_subscribers: Optional[float] = Field(None, description="YouTube Subscribers")
    linkedin_company_size: Optional[str] = Field(None, description="LinkedIn Company Size")
    linkedin_industry: Optional[str] = Field(None, description="LinkedIn Industry")
    platforms_found: Optional[float] = Field(None, description="Platforms Found")
    brand_tone: Optional[str] = Field(None, description="Brand Tone")


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
    "instagram_followers": "Instagram Followers",
    "facebook_followers": "Facebook Followers",
    "linkedin_followers": "LinkedIn Followers",
    "youtube_subscribers": "YouTube Subscribers",
    "linkedin_company_size": "Company Size",
    "linkedin_industry": "Industry (LinkedIn)",
    "platforms_found": "Platforms Found",
    "brand_tone": "Brand Tone",
}


def fmt(value) -> str:
    """Render a metric value the way the reference PDFs display metrics
    (e.g. 4900 -> '4.9K' for numbers; strings pass through as-is), or
    'Data not available' if unset/empty."""
    if value is None or value == "":
        return "Data not available"
    if isinstance(value, str):
        return value
    if value == int(value):
        value = int(value)
    if isinstance(value, int) and abs(value) >= 1000:
        return f"{value / 1000:.1f}K".replace(".0K", "K")
    return str(value)
