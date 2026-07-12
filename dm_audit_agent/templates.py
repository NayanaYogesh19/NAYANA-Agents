"""
templates.py — declarative slide-sequence definitions for the two audit
modes, so slide composition is data-driven instead of hardcoded per company.

Mode "seo": 9 slides, mirrors vertiv_digital_audit reference PDF.
Mode "full": 15 slides (within the user's requested 14-16 range), mirrors
karishye_audit_growth_strategy reference PDF, with Investment Summary /
Tools We Use / Terms & Conditions permanently excluded per the user's
instruction, and the single combined benchmark slide split into three
(SEO / SMM / PPC) as requested.

Every section except the always-on ones (title, metrics, contact) has a
`toggleable=True` slug so the frontend can offer it as a checkbox and the
backend can drop it from the run without touching any other slide.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Section:
    slug: str
    title: str
    toggleable: bool = True
    always_on: bool = False
    requires_full_mode: bool = False


# Canonical section order per mode. "always_on" sections are never shown as
# a toggle and can never be excluded (title/metrics/contact + growth+summary
# which the user described as required "over all" content coverage).
SEO_MODE_SECTIONS: list[Section] = [
    Section("title", "Title Slide", toggleable=False, always_on=True),
    Section("metrics", "Key Metrics Overview", toggleable=False, always_on=True),
    Section("current_state", "Current Digital State", toggleable=True),
    Section("visibility_gap", "Visibility Gap", toggleable=True),
    Section("best_practices", "Industry Best Practices", toggleable=True),
    Section("benchmarks_seo", "Competitive Benchmark Analysis (SEO)", toggleable=True),
    Section("growth_recommendations", "Growth Recommendations", toggleable=False, always_on=True),
    Section("summary_next_steps", "Summary & Next Steps", toggleable=False, always_on=True),
    Section("contact", "Contact & Next Steps", toggleable=False, always_on=True),
]

FULL_MODE_SECTIONS: list[Section] = [
    Section("title", "Title Slide", toggleable=False, always_on=True),
    Section("metrics", "Key Metrics Overview", toggleable=False, always_on=True),
    Section("executive_summary", "Executive Summary", toggleable=True),
    Section("positioning_audit", "Strategic Positioning Audit", toggleable=True),
    Section("performance_marketing", "Performance Marketing Audit", toggleable=True, requires_full_mode=True),
    Section("seo_technical_audit", "SEO & Technical Audit", toggleable=True),
    Section("smm_audit", "Social Media Audit", toggleable=True, requires_full_mode=True),
    Section("conversion_funnel", "Conversion System Audit", toggleable=True, requires_full_mode=True),
    Section("best_practices", "Industry Best Practices", toggleable=True),
    Section("benchmarks_seo", "Competitor Benchmarks — SEO", toggleable=True),
    Section("benchmarks_smm", "Competitor Benchmarks — SMM", toggleable=True, requires_full_mode=True),
    Section("benchmarks_ppc", "Competitor Benchmarks — PPC", toggleable=True, requires_full_mode=True),
    Section("strategic_recommendations", "Strategic Recommendations", toggleable=False, always_on=True),
    Section("kpis_targets", "KPIs & Targets / Summary", toggleable=False, always_on=True),
    Section("contact", "Contact & Next Steps", toggleable=False, always_on=True),
]

MODES = {
    "seo": {
        "label": "ONLY SEO",
        "slide_count": len(SEO_MODE_SECTIONS),
        "sections": SEO_MODE_SECTIONS,
    },
    "full": {
        "label": "SEO + Performance Marketing + Social Media Auditing",
        "slide_count": len(FULL_MODE_SECTIONS),
        "sections": FULL_MODE_SECTIONS,
    },
}

# Sections that must NEVER appear regardless of mode/toggles.
ALWAYS_EXCLUDED_SLUGS = {"investment_summary", "terms_and_conditions", "tools_we_use", "monthly_retainer"}


def get_sections(mode: str) -> list[Section]:
    if mode not in MODES:
        raise ValueError(f"Unknown audit mode: {mode!r}. Expected one of {list(MODES)}.")
    return MODES[mode]["sections"]


def toggleable_sections(mode: str) -> list[Section]:
    return [s for s in get_sections(mode) if s.toggleable]


def resolve_included_slugs(mode: str, excluded_slugs: list[str] | None) -> list[str]:
    """Given a mode and a list of slugs the user unchecked, return the final
    ordered list of section slugs to actually render — always-on sections are
    kept no matter what, and anything in ALWAYS_EXCLUDED_SLUGS is dropped."""
    excluded = set(excluded_slugs or []) | ALWAYS_EXCLUDED_SLUGS
    result = []
    for section in get_sections(mode):
        if section.slug in ALWAYS_EXCLUDED_SLUGS:
            continue
        if not section.toggleable or section.slug not in excluded:
            result.append(section.slug)
    return result
