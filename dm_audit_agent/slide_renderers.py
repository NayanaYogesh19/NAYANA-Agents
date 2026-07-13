"""
slide_renderers.py — one drawing function per render_key, matching the
reference "Digital Marketing Audit Report" template exactly:

  title, metrics, current_state, visibility_gap  — per-category slides,
      receive ctx["category"] to know which of SEO/PPC/SMM this instance is for.
  best_practices, benchmarks, strategic_takeaways, growth_recommendations,
      summary_next_steps, contact — combined slides, receive
      ctx["categories"] (the full list) since their content spans all
      selected categories.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from reportlab.lib.units import inch

from pdf_engine import (
    ACCENT_INDIGO,
    ACCENT_PURPLE,
    ACCENT_SKY,
    FONT_BOLD,
    FONT_OBLIQUE,
    FONT_REGULAR,
    MARGIN,
    NAVY,
    PAGE_H,
    PAGE_W,
    STATUS_DANGER,
    STATUS_SUCCESS,
    STATUS_WARNING,
    TEXT_MUTED,
    TEXT_SECONDARY,
    WHITE,
    SlideCanvas,
    _alpha,
    _wrap_text,
)
from metrics_schema import PPC_FIELD_LABELS, SEO_FIELD_LABELS, SMM_FIELD_LABELS, fmt
from reportlab.pdfbase.pdfmetrics import stringWidth
from templates import CATEGORY_LABELS

CATEGORY_METRIC_LABELS = {"seo": SEO_FIELD_LABELS, "ppc": PPC_FIELD_LABELS, "smm": SMM_FIELD_LABELS}
CATEGORY_METRIC_TAG_COLOR = {"seo": ACCENT_SKY, "ppc": STATUS_WARNING, "smm": ACCENT_PURPLE}
CATEGORY_ICON = {"seo": "▲", "ppc": "★", "smm": "◆"}
CATEGORY_SHORT_LABEL = {"seo": "SEO", "ppc": "PPC", "smm": "SMM"}
CATEGORY_GROWTH_BLOCK_TITLE = {
    "seo": "Search & Technical Optimization",
    "ppc": "Ads Enhancement",
    "smm": "Brand Authority & Engagement",
}


def _wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    return _wrap_text(text, font, size, max_w)


def _string_w(text: str, font: str, size: float) -> float:
    return stringWidth(text, font, size)


# ---------------------------------------------------------------- title ----
def render_title(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    c = sc.c
    sc.background()
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 9)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN, "trilliant digital")
    c.setFillColor(ACCENT_SKY)
    c.setFont(FONT_OBLIQUE, 7)
    c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 12, '"Dexterity in Action"')

    card_x, card_w = MARGIN + 0.3 * inch, PAGE_W - 2 * MARGIN - 2.2 * inch
    card_h = 3.1 * inch
    card_y = (PAGE_H - card_h) / 2
    sc.rounded_card(card_x, card_y, card_w, card_h, radius=18, fill=WHITE, border=None, accent_left=ACCENT_INDIGO)

    y = card_y + card_h - 50
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 20)
    title_line1 = ctx.get("report_title", "Suggested Digital Marketing Improvement Plan")
    for line in _wrap(title_line1.upper(), FONT_BOLD, 20, card_w - 60):
        c.drawString(card_x + 34, y, line)
        y -= 24

    y -= 6
    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 30)
    c.drawString(card_x + 34, y, ctx["company_name"].upper())
    y -= 40

    c.setFillColor(TEXT_SECONDARY)
    c.setFont(FONT_OBLIQUE, 11)
    for line in _wrap(f'"{ctx.get("positioning_line") or ctx["industry"]}"', FONT_OBLIQUE, 11, card_w - 60):
        c.drawString(card_x + 34, y, line)
        y -= 16

    y -= 10
    tag = ctx["industry"]
    tag_w = _string_w(tag, FONT_BOLD, 9.5) + 28
    c.setFillColor(_alpha(STATUS_SUCCESS, 0.12))
    c.roundRect(card_x + 34, y - 6, tag_w, 22, 11, fill=1, stroke=0)
    c.setFillColor(STATUS_SUCCESS)
    c.setFont(FONT_BOLD, 9.5)
    c.drawString(card_x + 48, y, tag)

    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_REGULAR, 9)
    c.drawCentredString(
        PAGE_W / 2, MARGIN,
        f"Prepared by Trilliant Digital | {datetime.now().strftime('%B %d, %Y')}",
    )


# ------------------------------------------------------- key metrics ----
def render_metrics(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    category = ctx["category"]
    cat_label = CATEGORY_LABELS[category]
    tag_color = CATEGORY_METRIC_TAG_COLOR[category]
    field_labels = CATEGORY_METRIC_LABELS[category]
    metrics = ctx["metrics_by_category"].get(category, {})
    is_auto_fetched = category == "smm"
    tag_text = "Auto-Fetched" if is_auto_fetched else "Manual Entry"

    y = sc.header("Key Metrics Overview", f"Live Snapshot of {ctx['company_name']}'s {cat_label} Performance")

    tile_specs = []
    for key, label in field_labels.items():
        value = metrics.get(key)
        if key == "health_score" and value is not None:
            display = f"{fmt(value)}/100"
        else:
            display = fmt(value)
        color = STATUS_DANGER if key == "errors" else (STATUS_WARNING if key == "warnings" else tag_color)
        tile_specs.append((label, display, color))

    cols = 4
    gap = 12
    tile_w = (PAGE_W - 2 * MARGIN - gap * (cols - 1)) / cols
    tile_h = 1.35 * inch
    top_row_y = y - tile_h
    for i, (label, value, color) in enumerate(tile_specs):
        col = i % cols
        row = i // cols
        x = MARGIN + col * (tile_w + gap)
        ty = top_row_y - row * (tile_h + gap)
        sc.kpi_tile(x, ty, tile_w, tile_h, label, str(value), tag_text, tag_color=color, top_accent=color)

    footer_text = (
        f"Auto-fetched via social profile discovery & scraping (Snapshot Date: {datetime.now().strftime('%b %d, %Y')})."
        if is_auto_fetched
        else f"All numbers manually entered by the user (Snapshot Date: {datetime.now().strftime('%b %d, %Y')})."
    )
    sc.footer(footer_text)


# ---------------------------------------------------- generic 2x2 grid ----
def render_quad_grid(sc: SlideCanvas, title: str, subtitle: str, quads: list[tuple[str, list[str], str]]) -> None:
    """quads: list of (heading, bullets, icon) tuples."""
    y = sc.header(title, subtitle)
    gap = 14
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = (y - MARGIN - gap - 0.3 * inch) / 2
    positions = [(MARGIN, y - card_h), (MARGIN + card_w + gap, y - card_h),
                 (MARGIN, y - 2 * card_h - gap), (MARGIN + card_w + gap, y - 2 * card_h - gap)]
    for (heading, bullets, icon), (x, cy) in zip(quads[:4], positions):
        sc.rounded_card(x, cy, card_w, card_h, radius=12)
        sc.text_block(x + 16, cy + card_h - 22, card_w - 32, heading, bullets, body_size=8.6, heading_size=11.5, gap=11.5, icon=icon)
    sc.footer()


def _section(ctx: dict[str, Any], category: str, slug: str) -> dict[str, list[str]]:
    per_cat = ctx["content"].get("per_category", {}).get(category, {})
    return per_cat.get(slug) or {}


def _bullets(section: dict[str, list[str]], sub_key: str) -> list[str]:
    values = section.get(sub_key) or []
    return values if values else ["Data not available"]


# ------------------------------------------------------- current state ----
def render_current_state(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    category = ctx["category"]
    section = _section(ctx, category, "current_state")
    cat_label = CATEGORY_LABELS[category]
    quads = [
        ("Performance Overview", _bullets(section, "performance_overview"), "▲"),
        ("Technical Gaps", _bullets(section, "technical_gaps"), "★"),
        ("Content Gaps", _bullets(section, "content_gaps"), "◆"),
        (f"{cat_label} Challenges", _bullets(section, "visibility_challenges"), "●"),
    ]
    render_quad_grid(
        sc,
        f"Current Digital State of {ctx['company_name']} in the {ctx['industry']} Sector",
        f"{cat_label} Perspective",
        quads,
    )


def render_visibility_gap(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    category = ctx["category"]
    section = _section(ctx, category, "visibility_gap")
    cat_label = CATEGORY_LABELS[category]
    halves = [
        ("Client vs. Industry", _bullets(section, "client_vs_industry")),
        ("Strategic Opportunities", _bullets(section, "strategic_opportunities")),
    ]
    y = sc.header(f"Visibility Gap in {ctx['industry']}", cat_label)
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = y - MARGIN - 0.3 * inch
    icons = ["▲", "●"]
    disclaimer = "All numbers are indicative estimates based on available tools."
    # "Client vs. Industry" carries more bullets (5 vs 3) — use a slightly
    # smaller body size there so all 5 fit comfortably in the same card height.
    body_sizes = [7.8, 8.8]
    for i, ((heading, bullets), icon, body_size) in enumerate(zip(halves, icons, body_sizes)):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 26, card_w - 36, heading, bullets,
                      body_size=body_size, heading_size=12.5, gap=body_size + 4.2, icon=icon,
                      per_bullet_disclaimer=disclaimer)
    sc.footer()


# --------------------------------------------------- combined slides ----
def render_best_practices(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    """Always renders as ONE slide regardless of how many categories are
    selected — one card per selected category, each with its own 5-bullet
    "Competitor Highlights" for that category, laid out side by side."""
    categories = ctx["categories"]
    best_practices = ctx["content"].get("best_practices", {})
    industry = ctx["industry"]
    y = sc.header(f"Industry Best Practices in {industry}", "")

    n = len(categories)
    gap = 14
    card_w = (PAGE_W - 2 * MARGIN - gap * (n - 1)) / n
    card_h = y - MARGIN - 0.3 * inch

    # Fewer bullets fit comfortably at the default size; scale body size down
    # a little as more cards (narrower width) are shown side by side.
    body_size = {1: 10.5, 2: 9.2, 3: 8.2}.get(n, 8.2)

    for i, cat in enumerate(categories):
        x = MARGIN + i * (card_w + gap)
        bullets = best_practices.get(cat) or ["Data not available"]
        heading = f"Competitor Highlights — {CATEGORY_SHORT_LABEL[cat]}" if n > 1 else "Competitor Highlights"
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 26, card_w - 36, heading, bullets,
                      body_size=body_size, heading_size=(11.5 if n == 3 else 12.5) if n > 1 else 14, gap=body_size + 4,
                      icon=CATEGORY_ICON.get(cat, "◆"))
    sc.footer()


def _benchmark_slide(sc: SlideCanvas, ctx: dict[str, Any], include_takeaways: bool) -> None:
    benchmarks = ctx["content"].get("benchmarks", {})
    client_table = benchmarks.get("client_table") or {"headers": [], "rows": []}
    industry_table = benchmarks.get("industry_table") or {"headers": [], "rows": []}
    company = ctx["company_name"]

    named_competitors = ctx.get("competitor_names", "")
    y = sc.header("Competitive Benchmark Analysis", f"{company} vs. Key Industry Players ({named_competitors})" if named_competitors else company)

    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    top_card_h = (y - MARGIN - gap - (1.6 * inch if include_takeaways else 0.3 * inch)) if include_takeaways else (y - MARGIN - 0.3 * inch)

    left_headers = client_table.get("headers") or ["Metric", "Current Status", "Trend"]
    left_rows = client_table.get("rows") or [["Data not available", "Data not available", "Data not available"]]
    right_headers = industry_table.get("headers") or ["Metric", company, "Industry"]
    right_rows = industry_table.get("rows") or [["Data not available", "Data not available", "Data not available"]]

    sc.rounded_card(MARGIN, y - top_card_h, card_w, top_card_h, radius=12)
    c = sc.c
    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 12)
    c.drawString(MARGIN + 18, y - 26, f"{company} Technical Performance")
    sc.table(MARGIN + 18, y - 44, card_w - 36, left_headers, left_rows, row_h=20)

    rx = MARGIN + card_w + gap
    sc.rounded_card(rx, y - top_card_h, card_w, top_card_h, radius=12)
    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 12)
    c.drawString(rx + 18, y - 26, "Industry Comparison")
    sc.table(rx + 18, y - 44, card_w - 36, right_headers, right_rows, row_h=20)

    if include_takeaways:
        takeaways = benchmarks.get("takeaways") or ["Data not available"]
        ty_card_y = MARGIN
        ty_card_h = y - top_card_h - gap - MARGIN
        sc.rounded_card(MARGIN, ty_card_y, PAGE_W - 2 * MARGIN, ty_card_h, radius=12)
        c.setFillColor(ACCENT_PURPLE)
        c.setFont(FONT_BOLD, 12)
        c.drawString(MARGIN + 18, ty_card_y + ty_card_h - 26, "Strategic Takeaways & Opportunities")
        col_w = (PAGE_W - 2 * MARGIN - 36) / 2
        ty = ty_card_y + ty_card_h - 48
        for i, item in enumerate(takeaways):
            col = i % 2
            if col == 0 and i > 0:
                ty -= 4
            x = MARGIN + 18 + col * (col_w + 12)
            yy = ty if col == 0 else ty
            c.setFillColor(ACCENT_PURPLE)
            c.circle(x + 2, yy + 3, 1.5, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont(FONT_REGULAR, 8.6)
            for line in _wrap(item, FONT_REGULAR, 8.6, col_w - 20):
                c.drawString(x + 10, yy, line)
                yy -= 11
            if col == 1:
                ty = min(ty, yy) - 4
    sc.footer()


def render_benchmarks(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    _benchmark_slide(sc, ctx, include_takeaways=not ctx.get("has_strategic_takeaways_slide", False))


def render_strategic_takeaways(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    benchmarks = ctx["content"].get("benchmarks", {})
    takeaways = benchmarks.get("takeaways") or ["Data not available"]
    y = sc.header("Strategic Takeaways & Opportunities", ctx["company_name"])
    card_w = PAGE_W - 2 * MARGIN
    card_h = y - MARGIN - 0.3 * inch
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 20, MARGIN + 0.3 * inch + card_h - 30, card_w - 40, "Key Opportunities Across the Board", takeaways,
                  body_size=9.5, heading_size=14, gap=15, icon="★")
    sc.footer()


def render_growth_recommendations(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    """Always renders as ONE slide regardless of how many categories are
    selected — one block per selected category: SEO -> "Search & Technical
    Optimization", PPC -> "Ads Enhancement", SMM -> "Brand Authority &
    Engagement", laid out side by side."""
    categories = ctx["categories"]
    growth = ctx["content"].get("growth_recommendations", {})
    y = sc.header(f"Growth Recommendations for {ctx['company_name']}", "")

    n = len(categories)
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap * (n - 1)) / n
    card_h = y - MARGIN - 0.3 * inch
    title_size = {1: 12.5, 2: 12.5, 3: 11}.get(n, 11)

    body_size = {1: 9.2, 2: 9.2, 3: 8.2}.get(n, 8.2)
    heading_size = {1: 13, 2: 13, 3: 11}.get(n, 11)
    for i, cat in enumerate(categories):
        x = MARGIN + i * (card_w + gap)
        cards = growth.get(cat) or []
        block_title = CATEGORY_GROWTH_BLOCK_TITLE.get(cat, cat.upper())
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.benefit_card_list(x + 18, MARGIN + 0.3 * inch + card_h - 24, card_w - 36,
                            block_title, cards, icon=CATEGORY_ICON.get(cat, "●"),
                            title_size=body_size, body_size=body_size - 0.8, heading_size=heading_size)
    sc.footer()


def render_summary_next_steps(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    """Fixed 3-section structure (NOT per-category) — Foundation & Strategy,
    Growth & Execution, and Action Plan — each with up to 6 compact numbered
    items, laid out in 3 columns so all 18 items fit on one slide."""
    summary = ctx["content"].get("summary_next_steps", {})
    sections = [
        ("Foundation & Strategy", summary.get("foundation_strategy") or []),
        ("Growth & Execution", summary.get("growth_execution") or []),
        ("Action Plan", summary.get("action_plan") or []),
    ]
    y = sc.header(f"Summary & Next Steps for {ctx['company_name']}", "")
    gap = 12
    banner_h = 0.7 * inch
    n = len(sections)
    card_w = (PAGE_W - 2 * MARGIN - gap * (n - 1)) / n
    card_h = y - MARGIN - banner_h - 0.25 * inch

    running_number = 1
    for i, (heading, cards) in enumerate(sections):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + banner_h + 0.15 * inch, card_w, card_h, radius=12)
        c = sc.c
        c.setFillColor(ACCENT_PURPLE)
        c.setFont(FONT_BOLD, 10.5)
        cy = MARGIN + banner_h + 0.15 * inch + card_h - 20
        c.drawString(x + 14, cy, heading)
        cy -= 16
        for card in cards:
            cy = sc.numbered_card_compact(x + 14, cy, card_w - 28, running_number,
                                          card.get("title", ""), card.get("detail", ""),
                                          card.get("impact", card.get("benefit", "")))
            running_number += 1

    sc.dark_panel(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, banner_h, "", "Ready to Accelerate Growth?",
                  ["Let's finalize the implementation timeline together."])


def render_contact(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    sc.background()
    c = sc.c
    c.setFillColor(NAVY)
    c.setFont(FONT_BOLD, 26)
    c.drawCentredString(PAGE_W / 2, PAGE_H - 1.4 * inch, "Contact and Next Steps")
    c.setStrokeColor(ACCENT_INDIGO)
    c.setLineWidth(2)
    c.line(PAGE_W / 2 - 40, PAGE_H - 1.55 * inch, PAGE_W / 2 + 40, PAGE_H - 1.55 * inch)

    c.setFillColor(TEXT_SECONDARY)
    c.setFont(FONT_REGULAR, 10.5)
    msg = (f"Thank you for reviewing our Digital Marketing Improvement Plan for {ctx['company_name']}. "
           f"We look forward to partnering with you to drive sustainable growth in the {ctx['industry']} industry.")
    y = PAGE_H - 2.1 * inch
    for line in _wrap(msg, FONT_REGULAR, 10.5, PAGE_W - 4 * inch):
        c.drawCentredString(PAGE_W / 2, y, line)
        y -= 15

    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 11)
    c.drawCentredString(PAGE_W / 2, y - 20, "Trilliant Digital — Empowering sustainable growth through data-driven marketing")

    card_w = 2.6 * inch
    card_h = 1.5 * inch
    gap = 0.4 * inch
    total_w = card_w * 2 + gap
    start_x = (PAGE_W - total_w) / 2
    card_y = y - 20 - card_h - 0.7 * inch
    for i, (name, email, phone) in enumerate([
        ("Gurmeet Tyagi", "gurmeet.tyagi@trilliantdigital.com", "+91 70178 56109"),
        ("Suryanarayana Valluri", "suri.valluri@trilliantdigital.com", "+91 98450 55736"),
    ]):
        x = start_x + i * (card_w + gap)
        sc.rounded_card(x, card_y, card_w, card_h, radius=14)

        avatar_r = 14
        avatar_cx = x + card_w / 2
        avatar_cy = card_y + card_h - 14
        c.saveState()
        p = c.beginPath()
        p.circle(avatar_cx, avatar_cy, avatar_r)
        c.clipPath(p, stroke=0, fill=0)
        c.setFillColor(_alpha(ACCENT_INDIGO, 0.12))
        c.circle(avatar_cx, avatar_cy, avatar_r, fill=1, stroke=0)
        c.setFillColor(ACCENT_INDIGO)
        c.circle(avatar_cx, avatar_cy + 4, 4.3, fill=1, stroke=0)
        c.circle(avatar_cx, avatar_cy - 11, 9, fill=1, stroke=0)
        c.restoreState()

        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 11)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 48, name)
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(FONT_REGULAR, 8)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 64, email)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 76, phone)

    button_w, button_h = 1.9 * inch, 0.42 * inch
    button_x = (PAGE_W - button_w) / 2
    button_y = card_y - 0.55 * inch
    c.setFillColor(ACCENT_INDIGO)
    c.roundRect(button_x, button_y, button_w, button_h, button_h / 2, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(FONT_BOLD, 9.5)
    c.drawCentredString(button_x + button_w / 2, button_y + button_h / 2 - 3.3, "Schedule a Discussion")

    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_OBLIQUE, 7.5)
    c.drawCentredString(PAGE_W / 2, MARGIN, "All numerical values are indicative and derived from available analytics tools.")


RENDERERS: dict[str, Callable[[SlideCanvas, dict], None]] = {
    "title": render_title,
    "metrics": render_metrics,
    "current_state": render_current_state,
    "visibility_gap": render_visibility_gap,
    "best_practices": render_best_practices,
    "benchmarks": render_benchmarks,
    "strategic_takeaways": render_strategic_takeaways,
    "growth_recommendations": render_growth_recommendations,
    "summary_next_steps": render_summary_next_steps,
    "contact": render_contact,
}
