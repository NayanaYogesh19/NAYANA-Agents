"""
models.py — Pydantic schemas for all agent inputs and outputs.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class BusinessType(str, Enum):
    B2B = "B2B"
    B2C = "B2C"


class BusinessGoal(str, Enum):
    LEAD_GENERATION      = "Lead Generation"
    DEMO_BOOKING         = "Demo Booking"
    ECOMMERCE            = "E-commerce"
    BRAND_AWARENESS      = "Brand Awareness"
    CONSULTATION_REQUEST = "Consultation Request"
    PRODUCT_SALES        = "Product Sales"
    SUBSCRIPTION_SIGNUP  = "Subscription Sign-up"
    EVENT_REGISTRATION   = "Event Registration"
    CONTENT_DOWNLOADS    = "Content Downloads"
    SAAS_TRIAL_SIGNUP    = "SaaS Trial Sign-up"
    CUSTOM               = "Custom"


class AnalysisMode(str, Enum):
    AUDIT_EXISTING = "audit_existing"
    NEW_STRUCTURE  = "new_structure"


# ─── Agent Request ────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    target_url:      str
    mode:            AnalysisMode
    business_type:   BusinessType
    business_goal:   BusinessGoal
    custom_goal:     Optional[str] = None       # filled when business_goal == "Custom"
    competitor_urls: List[str] = []             # required for audit, optional for new_structure
    audit_text:      Optional[str] = None

    @field_validator("competitor_urls")
    @classmethod
    def check_competitors(cls, v):
        clean = [u.strip() for u in v if u.strip()]
        if len(clean) > 5:
            raise ValueError("Maximum 5 competitor URLs allowed.")
        return clean

    @field_validator("target_url", mode="before")
    @classmethod
    def strip_target(cls, v):
        return v.strip() if isinstance(v, str) else v


# ─── Internal Data Models ─────────────────────────────────────────────────────

class ScrapedSite(BaseModel):
    url:              str
    nav_labels:       List[str] = []
    url_patterns:     List[str] = []
    url_endpoints:    List[str] = []        # actual discovered URL paths
    content_depth:    int       = 0
    page_count:       int       = 0
    top_pages:        List[str] = []
    structural_notes: List[str] = []
    error:            Optional[str] = None


class AuditFindings(BaseModel):
    crawl_errors:        List[str] = []
    orphan_pages:        List[str] = []
    redirect_chains:     List[str] = []
    thin_content_pages:  List[str] = []
    missing_pages:       List[str] = []
    structural_issues:   List[str] = []
    raw_notes:           Optional[str] = None


class PageNode(BaseModel):
    page_name:         str
    tier:              int
    url_slug:          str
    page_type:         str
    parent_page:       Optional[str] = None
    priority:          str
    cta_type:          Optional[str] = None
    wireframe_pattern: Optional[str] = None


class NavigationMenu(BaseModel):
    primary_nav:            List[str] = []
    secondary_nav:          List[str] = []
    breadcrumb_example:     List[str] = []
    internal_linking_rules: List[str] = []


class ConversionPath(BaseModel):
    goal:               str
    funnel_steps:       List[str] = []
    cta_per_tier:       dict      = {}
    key_landing_pages:  List[str] = []


class StructurePlan(BaseModel):
    pages:                   List[PageNode]       = []
    navigation:              NavigationMenu       = NavigationMenu()
    conversion_paths:        List[ConversionPath] = []
    recommendations:         List[str]            = []
    implementation_strategy: List[str]            = []


# ─── Agent Output ─────────────────────────────────────────────────────────────

class AgentOutput(BaseModel):
    mode:                 str
    target_url:           str
    business_type:        str
    business_goal:        str
    scraped_competitors:  List[ScrapedSite]       = []
    scraped_target:       Optional[ScrapedSite]   = None
    audit_findings:       Optional[AuditFindings] = None
    structure_plan:       Optional[StructurePlan] = None
    pdf_path:             Optional[str]           = None
    error:                Optional[str]           = None
    status:               str                     = "pending"
