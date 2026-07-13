"""
templates.py — declarative slide-sequence definitions, built dynamically from
which of SEO / Performance Marketing (PPC) / Social Media (SMM) categories
the user selects (any combination).

Matches the reference "Digital Marketing Audit Report" template:
  1. Title — one slide, always.
  2. Key Metrics Overview — REPEATED once per selected category.
  3. Current Digital State — REPEATED once per selected category.
  4. Visibility Gap — REPEATED once per selected category.
  5. Industry Best Practices — ONE combined slide; content adapts to
     whichever categories are selected.
  6. Competitive Benchmark Analysis — ONE combined slide (two tables), with
     Strategic Takeaways folded into the same slide UNLESS all three
     categories are selected, in which case Strategic Takeaways becomes its
     own slide (see below).
  7. Growth Recommendations — ONE combined slide; its two blocks (Search &
     Technical Optimization / Brand Authority & Engagement) adapt to draw
     from whichever categories are selected.
  8. Summary & Next Steps — ONE combined slide summarizing everything above.
  9. Contact — one slide, always.

A single selected category always produces exactly 9 slides (matching the
reference PDF 1:1). Selecting all three categories expands slides 2/3/4 to 3
sub-slides each (+6 slides over the single-category case) and splits
Strategic Takeaways out of the Benchmark slide into its own slide (+1),
totalling 9 + 6 + 1 = 16 slides.
"""

from __future__ import annotations

from dataclasses import dataclass

VALID_CATEGORIES = {"seo", "ppc", "smm"}
CATEGORY_ORDER = ["seo", "ppc", "smm"]

CATEGORY_LABELS = {
    "seo": "SEO",
    "ppc": "Performance Marketing (PPC)",
    "smm": "Social Media (SMM)",
}


@dataclass(frozen=True)
class SlideGroup:
    slug: str
    title: str
    per_category: bool  # True = repeated once per selected category
    toggleable: bool = True
    always_on: bool = False


# Slide groups in render order. per_category=True groups expand into one
# slide per selected category (slug becomes "<slug>__<category>" at resolve
# time); per_category=False groups render exactly once, with content adapted
# to cover whichever categories were selected.
SLIDE_GROUPS: list[SlideGroup] = [
    SlideGroup("title", "Title Slide", per_category=False, toggleable=False, always_on=True),
    SlideGroup("metrics", "Key Metrics Overview", per_category=True, toggleable=False, always_on=True),
    SlideGroup("current_state", "Current Digital State", per_category=True, toggleable=True),
    SlideGroup("visibility_gap", "Visibility Gap", per_category=True, toggleable=True),
    SlideGroup("best_practices", "Industry Best Practices", per_category=False, toggleable=True),
    SlideGroup("benchmarks", "Competitive Benchmark Analysis", per_category=False, toggleable=True),
    # "strategic_takeaways" only ever appears as its own slide when all three
    # categories are selected (see resolve_included_slides) — for a single
    # category it stays folded into the "benchmarks" slide, matching the
    # reference PDF's combined layout and keeping the single-category count at 9.
    SlideGroup("strategic_takeaways", "Strategic Takeaways & Opportunities", per_category=False, toggleable=True),
    SlideGroup("growth_recommendations", "Growth Recommendations", per_category=False, toggleable=False, always_on=True),
    SlideGroup("summary_next_steps", "Summary & Next Steps", per_category=False, toggleable=False, always_on=True),
    SlideGroup("contact", "Contact & Next Steps", per_category=False, toggleable=False, always_on=True),
]

SLIDE_GROUPS_BY_SLUG: dict[str, SlideGroup] = {g.slug: g for g in SLIDE_GROUPS}

# Sections that must NEVER appear regardless of category/toggles.
ALWAYS_EXCLUDED_SLUGS = {"investment_summary", "terms_and_conditions", "tools_we_use", "monthly_retainer"}


def validate_categories(categories: list[str]) -> list[str]:
    """Returns the deduped list of valid categories in canonical order
    (seo, ppc, smm). Raises ValueError if none are valid/selected."""
    seen = [c for c in CATEGORY_ORDER if c in (categories or [])]
    if not seen:
        raise ValueError(
            f"At least one category must be selected. Expected one or more of {sorted(VALID_CATEGORIES)}."
        )
    return seen


def toggleable_groups() -> list[SlideGroup]:
    return [g for g in SLIDE_GROUPS if g.toggleable]


def resolve_included_slides(categories: list[str], excluded_slugs: list[str] | None) -> list[dict]:
    """Returns the final ordered list of slides to render. Each entry is
    {"slug": <group_slug>, "category": <category or None>, "render_key":
    <slug used to look up the renderer, e.g. "metrics">}. per_category groups
    produce one entry per selected category (in canonical seo/ppc/smm order);
    other groups produce exactly one entry with category=None.

    "strategic_takeaways" only becomes its own slide when all three
    categories are selected; otherwise it is skipped here and its content is
    folded into the "benchmarks" slide by the renderer (single-category runs
    total exactly 9 slides; all-three runs total exactly 16)."""
    excluded = set(excluded_slugs or []) | ALWAYS_EXCLUDED_SLUGS
    all_three_selected = set(categories) == set(CATEGORY_ORDER)
    result: list[dict] = []
    for group in SLIDE_GROUPS:
        if group.slug in ALWAYS_EXCLUDED_SLUGS:
            continue
        if group.slug == "strategic_takeaways" and not all_three_selected:
            continue
        if group.toggleable and group.slug in excluded:
            continue
        if group.per_category:
            for cat in categories:
                result.append({"slug": group.slug, "category": cat, "render_key": group.slug})
        else:
            result.append({"slug": group.slug, "category": None, "render_key": group.slug})
    return result
