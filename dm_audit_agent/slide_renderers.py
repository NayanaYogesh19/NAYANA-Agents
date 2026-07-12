"""
slide_renderers.py — one drawing function per section slug, each given the
company context + manual metrics + LLM-generated section text, and a
SlideCanvas to draw onto. This is the layer that turns dynamic, per-company
LLM content into pages matching the reference PDFs' fixed visual layout.
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
)
from metrics_schema import PPC_FIELD_LABELS, SEO_FIELD_LABELS, SMM_FIELD_LABELS, fmt


def _bullets_from_text(text: str, max_items: int = 8) -> list[str]:
    """Splits an LLM section's plain-text output into bullet lines. Accepts
    lines already starting with '-'/'•' or falls back to sentence-splitting."""
    lines = [l.strip(" -•\t:") for l in text.splitlines() if l.strip()]
    lines = [l for l in lines if len(l) > 3]
    if not lines:
        lines = [s.strip(" -•\t:") for s in text.split(".") if len(s.strip()) > 3]
    return lines[:max_items]


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
    for line in _wrap(f'"{ctx.get("positioning_line", ctx["industry"])}"', FONT_OBLIQUE, 11, card_w - 60):
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


# ------------------------------------------------------------- metrics ----
def render_metrics(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    y = sc.header("Key Metrics Overview", f"Manually Entered Snapshot of {ctx['company_name']}'s Performance")
    seo = ctx["seo_metrics"]

    tiles = [
        ("Health Score", f"{fmt(seo.get('health_score'))}/100" if seo.get("health_score") is not None else "Data not available", "Manual Entry", STATUS_SUCCESS),
        ("Organic Traffic", fmt(seo.get("organic_traffic")), "Manual Entry", ACCENT_SKY),
        ("Organic Keywords", fmt(seo.get("organic_keywords")), "Manual Entry", ACCENT_SKY),
        ("Passed Checks", fmt(seo.get("passed_checks")), "Manual Entry", STATUS_SUCCESS),
        ("Crawled Pages", fmt(seo.get("crawled_pages")), "Manual Entry", TEXT_MUTED),
        ("Errors", fmt(seo.get("errors")), "Manual Entry", STATUS_DANGER),
        ("Warnings", fmt(seo.get("warnings")), "Manual Entry", STATUS_WARNING),
        ("Notices", fmt(seo.get("notices")), "Manual Entry", ACCENT_SKY),
    ]

    cols = 4
    gap = 12
    tile_w = (PAGE_W - 2 * MARGIN - gap * (cols - 1)) / cols
    tile_h = 1.35 * inch
    top_row_y = y - tile_h
    for i, (label, value, tag, color) in enumerate(tiles):
        col = i % cols
        row = i // cols
        x = MARGIN + col * (tile_w + gap)
        ty = top_row_y - row * (tile_h + gap)
        sc.kpi_tile(x, ty, tile_w, tile_h, label, str(value), tag, tag_color=color, top_accent=color)

    sc.footer(f"All numbers manually entered by the user (Snapshot Date: {datetime.now().strftime('%b %d, %Y')}).")


# ---------------------------------------------------- generic 2x2 grid ----
def render_quad_grid(sc: SlideCanvas, title: str, subtitle: str, quads: list[tuple[str, list[str]]]) -> None:
    y = sc.header(title, subtitle)
    gap = 14
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = (y - MARGIN - gap - 0.3 * inch) / 2
    positions = [(MARGIN, y - card_h), (MARGIN + card_w + gap, y - card_h),
                 (MARGIN, y - 2 * card_h - gap), (MARGIN + card_w + gap, y - 2 * card_h - gap)]
    for (heading, bullets), (x, cy) in zip(quads[:4], positions):
        sc.rounded_card(x, cy, card_w, card_h, radius=12)
        sc.text_block(x + 16, cy + card_h - 26, card_w - 32, heading, bullets, body_size=8.6, heading_size=11.5, gap=11.5)
    sc.footer()


# ------------------------------------------------------- current state ----
def render_current_state(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("current_state", "")
    quads = _split_into_quads(content, [
        "Performance Overview", "Technical Gaps", "Content Gaps", "Visibility Challenges",
    ])
    render_quad_grid(
        sc,
        f"Current Digital State of {ctx['company_name']} in the {ctx['industry']} Sector",
        "",
        quads,
    )


def render_visibility_gap(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("visibility_gap", "")
    halves = _split_into_quads(content, ["Client vs. Industry", "Strategic Opportunities"])
    y = sc.header(f"Visibility Gap in {ctx['industry']}", "")
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = y - MARGIN - 0.3 * inch
    for i, (heading, bullets) in enumerate(halves[:2]):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 30, card_w - 36, heading, bullets, body_size=8.8, heading_size=12.5, gap=13)
    sc.footer()


def render_best_practices(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("best_practices", "")
    bullets = _bullets_from_text(content, max_items=6)
    y = sc.header(f"Industry Best Practices in {ctx['industry']}", "")
    card_w = PAGE_W - 2 * MARGIN
    card_h = y - MARGIN - 0.3 * inch
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 20, MARGIN + 0.3 * inch + card_h - 34, card_w - 40, "Competitor Highlights", bullets,
                   body_size=9.5, heading_size=14, gap=15)
    sc.footer()


def _benchmark_table(sc: SlideCanvas, ctx: dict[str, Any], kind: str, title: str) -> None:
    y = sc.header(title, f"{ctx['company_name']} vs. Key Industry Players")
    data = ctx["benchmarks"].get(kind, {})
    rows = data.get("rows", []) or [["Data not available", "Data not available", "Data not available"]]
    headers = data.get("headers", ["Metric", ctx["company_name"], "Industry Average"])

    table_h = 22 * (len(rows) + 1) + 20
    card_w = PAGE_W - 2 * MARGIN
    sc.rounded_card(MARGIN, y - table_h - 20, card_w, table_h + 20, radius=12)
    sc.table(MARGIN + 16, y - 12, card_w - 32, headers, rows, row_h=22)

    takeaways = data.get("takeaways", [])
    if takeaways:
        ty = y - table_h - 34
        c = sc.c
        c.setFillColor(ACCENT_PURPLE)
        c.setFont(FONT_BOLD, 10.5)
        c.drawString(MARGIN, ty, "Strategic Takeaways")
        ty -= 16
        c.setFont(FONT_REGULAR, 8.6)
        c.setFillColor(NAVY)
        for t in takeaways[:3]:
            for line in _wrap(f"• {t}", FONT_REGULAR, 8.6, card_w):
                c.drawString(MARGIN, ty, line)
                ty -= 12
    sc.footer()


def render_benchmarks_seo(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    _benchmark_table(sc, ctx, "seo", "Competitive Benchmark Analysis — SEO")


def render_benchmarks_smm(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    _benchmark_table(sc, ctx, "smm", "Competitive Benchmark Analysis — Social Media")


def render_benchmarks_ppc(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    _benchmark_table(sc, ctx, "ppc", "Competitive Benchmark Analysis — Performance Marketing")


def render_growth_recommendations(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("growth_recommendations", "")
    quads = _split_into_quads(content, ["Search & Technical Optimization", "Brand Authority & Engagement"])
    y = sc.header(f"Growth Recommendations for {ctx['company_name']}", "")
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = y - MARGIN - 0.3 * inch
    for i, (heading, bullets) in enumerate(quads[:2]):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 30, card_w - 36, heading, bullets, body_size=8.6, heading_size=12, gap=12.5)
    sc.footer()


def render_summary_next_steps(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("summary_next_steps", "")
    quads = _split_into_quads(content, ["Foundation & Strategy", "Growth & Execution"])
    y = sc.header(f"Summary & Next Steps for {ctx['company_name']}", "")
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = y - MARGIN - 1.1 * inch - 0.3 * inch
    for i, (heading, bullets) in enumerate(quads[:2]):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + 1.1 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 1.1 * inch + card_h - 30, card_w - 36, heading, bullets, body_size=8.6, heading_size=12, gap=12.5)

    sc.dark_panel(MARGIN, MARGIN, PAGE_W - 2 * MARGIN, 0.85 * inch, "", "Ready to Accelerate Growth?",
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
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 11)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 30, name)
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(FONT_REGULAR, 8)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 48, email)
        c.drawCentredString(x + card_w / 2, card_y + card_h - 62, phone)

    c.setFillColor(TEXT_MUTED)
    c.setFont(FONT_OBLIQUE, 7.5)
    c.drawCentredString(PAGE_W / 2, MARGIN, "All numerical values are indicative and derived from available analytics tools.")


# ------------------------------------------------------------ full mode ----
def render_executive_summary(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("executive_summary", "")
    quads = _split_into_quads(content, ["Strengths (To Scale)", "Performance Gaps (To Fix Now)"])
    y = sc.header("Executive Summary", "Current State Assessment & Growth Opportunity")
    gap = 16
    left_w = (PAGE_W - 2 * MARGIN - gap) * 0.55
    right_w = (PAGE_W - 2 * MARGIN - gap) * 0.45
    card_h = y - MARGIN - 0.3 * inch
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, left_w, card_h, radius=12)
    sc.text_block(MARGIN + 18, MARGIN + 0.3 * inch + card_h - 30, left_w - 36,
                  "Strengths & Gaps", quads[0][1] + quads[1][1] if len(quads) >= 2 else quads[0][1] if quads else [],
                  body_size=8.4, heading_size=12, gap=11.5)

    rx = MARGIN + left_w + gap
    imperative = ctx["section_text"].get("executive_summary_imperative", "The opportunity is to build a system for compounding growth.")
    sc.dark_panel(rx, MARGIN + 0.3 * inch, right_w, card_h, "Strategic Imperative", imperative,
                  ["Focus must shift toward sustainable, trust-driven growth across all channels."])
    sc.footer()


def render_positioning_audit(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("positioning_audit", "")
    quads = _split_into_quads(content, [f"{ctx['company_name']} Stands For", "Market Gap Analysis"])
    render_quad_grid(sc, "Strategic Positioning Audit", "Brand Authority & Market Opportunity Analysis", quads[:2] + [("", [])] * max(0, 2 - len(quads)))


def render_performance_marketing(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    ppc = ctx.get("ppc_metrics", {})
    content = ctx["section_text"].get("performance_marketing", "")
    y = sc.header("Performance Marketing Audit", "Funnel Reality & Channel Optimization")

    tiles = [(label, fmt(ppc.get(key))) for key, label in PPC_FIELD_LABELS.items()]
    cols = 4
    gap = 12
    tile_w = (PAGE_W - 2 * MARGIN - gap * (cols - 1)) / cols
    tile_h = 1.05 * inch
    for i, (label, value) in enumerate(tiles[:8]):
        col = i % cols
        row = i // cols
        x = MARGIN + col * (tile_w + gap)
        ty = y - tile_h - row * (tile_h + gap)
        sc.kpi_tile(x, ty, tile_w, tile_h, label, str(value), tag_color=ACCENT_SKY, top_accent=ACCENT_SKY)

    bullets = _bullets_from_text(content, max_items=5)
    text_y = y - 2 * (tile_h + gap) - 10
    card_h = text_y - MARGIN - 0.3 * inch
    card_w = PAGE_W - 2 * MARGIN
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 18, MARGIN + 0.3 * inch + card_h - 28, card_w - 36, "Channel Analysis", bullets,
                  body_size=8.6, heading_size=12, gap=12)
    sc.footer()


def render_seo_technical_audit(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("seo_technical_audit", "")
    seo = ctx["seo_metrics"]
    y = sc.header("SEO & Technical Audit", "Critical Infrastructure & Health Analysis")

    tiles = [
        ("Errors", fmt(seo.get("errors")), STATUS_DANGER),
        ("Warnings", fmt(seo.get("warnings")), STATUS_WARNING),
        ("Notices", fmt(seo.get("notices")), ACCENT_SKY),
        ("Crawled Pages", fmt(seo.get("crawled_pages")), TEXT_MUTED),
    ]
    gap = 12
    tile_w = (PAGE_W - 2 * MARGIN - gap * 3) / 4
    tile_h = 1.1 * inch
    for i, (label, value, color) in enumerate(tiles):
        x = MARGIN + i * (tile_w + gap)
        sc.kpi_tile(x, y - tile_h, tile_w, tile_h, label, str(value), tag_color=color, top_accent=color)

    bullets = _bullets_from_text(content, max_items=6)
    text_y = y - tile_h - gap - 10
    card_h = text_y - MARGIN - 0.3 * inch
    card_w = PAGE_W - 2 * MARGIN
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 18, MARGIN + 0.3 * inch + card_h - 28, card_w - 36, "Structural Gaps", bullets,
                  body_size=8.6, heading_size=12, gap=12)
    sc.footer()


def render_smm_audit(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    smm = ctx.get("smm_metrics", {})
    content = ctx["section_text"].get("smm_audit", "")
    y = sc.header("Social Media Audit", "Client vs. Industry Presence")

    tiles = [(label, fmt(smm.get(key))) for key, label in SMM_FIELD_LABELS.items()]
    gap = 14
    tile_w = (PAGE_W - 2 * MARGIN - gap * 2) / 3
    tile_h = 1.1 * inch
    for i, (label, value) in enumerate(tiles):
        x = MARGIN + i * (tile_w + gap)
        sc.kpi_tile(x, y - tile_h, tile_w, tile_h, label, str(value), tag_color=ACCENT_PURPLE, top_accent=ACCENT_PURPLE)

    bullets = _bullets_from_text(content, max_items=6)
    text_y = y - tile_h - gap - 10
    card_h = text_y - MARGIN - 0.3 * inch
    card_w = PAGE_W - 2 * MARGIN
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 18, MARGIN + 0.3 * inch + card_h - 28, card_w - 36, "Competitive Gap Analysis", bullets,
                  body_size=8.6, heading_size=12, gap=12)
    sc.footer()


def render_conversion_funnel(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("conversion_funnel", "")
    quads = _split_into_quads(content, ["Diagnosis", "Conversion System Fix"])
    render_quad_grid(sc, "Conversion System Audit", "Funnel Flow Analysis & Friction Points", quads[:2] + [("", [])] * max(0, 2 - len(quads)))


def render_strategic_recommendations(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    content = ctx["section_text"].get("strategic_recommendations", "")
    quads = _split_into_quads(content, ["Phase 1 — Foundation Repair", "Phase 2 — Growth & Scale"])
    y = sc.header("Strategic Recommendations", "Phased Roadmap")
    gap = 16
    card_w = (PAGE_W - 2 * MARGIN - gap) / 2
    card_h = y - MARGIN - 0.3 * inch
    for i, (heading, bullets) in enumerate(quads[:2]):
        x = MARGIN + i * (card_w + gap)
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 30, card_w - 36, heading, bullets, body_size=8.4, heading_size=12, gap=11.5)
    sc.footer()


def render_kpis_targets(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    data = ctx.get("kpi_targets", {})
    rows = data.get("rows") or [["Data not available", "Data not available", "Data not available", "Data not available"]]
    headers = data.get("headers", ["Metric", "Current State", "6-Month Target", "Strategic Impact"])
    y = sc.header("KPIs & Targets", "Measuring Success & Growth Trajectory")
    card_w = PAGE_W - 2 * MARGIN
    table_h = 22 * (len(rows) + 1) + 16
    sc.rounded_card(MARGIN, y - table_h - 10, card_w, table_h, radius=12)
    col_widths = [card_w * 0.22, card_w * 0.2, card_w * 0.2, card_w * 0.38 - 32]
    sc.table(MARGIN + 16, y - 6, card_w - 32, headers, rows, col_widths=col_widths, row_h=22)
    sc.footer()


# ------------------------------------------------------------- helpers ----
def _split_into_quads(text: str, headings: list[str]) -> list[tuple[str, list[str]]]:
    """Splits LLM output into (heading, bullets) groups using the given
    heading labels as section markers if present in the text; otherwise
    evenly distributes bullet lines across the requested number of quads."""
    result: list[tuple[str, list[str]]] = []
    lower = text.lower()
    positions = []
    for h in headings:
        idx = lower.find(h.lower())
        positions.append(idx if idx >= 0 else None)

    if all(p is not None for p in positions):
        sorted_pairs = sorted(zip(positions, headings), key=lambda p: p[0])
        for i, (pos, heading) in enumerate(sorted_pairs):
            end = sorted_pairs[i + 1][0] if i + 1 < len(sorted_pairs) else len(text)
            chunk = text[pos + len(heading): end]
            result.append((heading, _bullets_from_text(chunk, max_items=4)))
        order_map = {h: b for h, b in result}
        return [(h, order_map.get(h, [])) for h in headings]

    all_bullets = _bullets_from_text(text, max_items=len(headings) * 3)
    per = max(1, len(all_bullets) // max(1, len(headings)))
    out = []
    for i, h in enumerate(headings):
        chunk = all_bullets[i * per: (i + 1) * per] or ["Data not available"]
        out.append((h, chunk))
    return out


def _wrap(text: str, font: str, size: float, max_w: float) -> list[str]:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_w or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _string_w(text: str, font: str, size: float) -> float:
    from reportlab.pdfbase.pdfmetrics import stringWidth
    return stringWidth(text, font, size)


def _alpha(color, alpha: float):
    from reportlab.lib.colors import Color
    return Color(color.red, color.green, color.blue, alpha=alpha)


RENDERERS: dict[str, Callable[[SlideCanvas, dict], None]] = {
    "title": render_title,
    "metrics": render_metrics,
    "current_state": render_current_state,
    "visibility_gap": render_visibility_gap,
    "best_practices": render_best_practices,
    "benchmarks_seo": render_benchmarks_seo,
    "benchmarks_smm": render_benchmarks_smm,
    "benchmarks_ppc": render_benchmarks_ppc,
    "growth_recommendations": render_growth_recommendations,
    "summary_next_steps": render_summary_next_steps,
    "contact": render_contact,
    "executive_summary": render_executive_summary,
    "positioning_audit": render_positioning_audit,
    "performance_marketing": render_performance_marketing,
    "seo_technical_audit": render_seo_technical_audit,
    "smm_audit": render_smm_audit,
    "conversion_funnel": render_conversion_funnel,
    "strategic_recommendations": render_strategic_recommendations,
    "kpis_targets": render_kpis_targets,
}
