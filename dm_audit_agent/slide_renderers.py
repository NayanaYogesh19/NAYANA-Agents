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

# Current Digital State's first 3 quadrant headings, tailored per category so
# they describe what's actually analyzed there instead of a generic
# SEO-shaped label reused for PPC/SMM. The 4th quadrant ("<Category>
# Challenges") is already category-labeled via CATEGORY_LABELS and stays as-is.
CATEGORY_CURRENT_STATE_LABELS = {
    "seo": {
        "performance_overview": "Performance Overview",
        "technical_gaps": "Technical Gaps",
        "content_gaps": "Content Gaps",
    },
    "ppc": {
        "performance_overview": "Ad Presence Overview",
        "technical_gaps": "Ad Format & Platform Gaps",
        "content_gaps": "Ad Creative Gaps",
    },
    "smm": {
        "performance_overview": "Social Presence Overview",
        "technical_gaps": "Platform Coverage Gaps",
        "content_gaps": "Content & Engagement Gaps",
    },
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

    # Skip a tile entirely if its value is genuinely null (e.g. an
    # auto-fetched SMM platform that couldn't be found) rather than showing
    # a "Data not available" tile — the grid reflows with fewer tiles.
    tile_specs = []
    for key, label in field_labels.items():
        value = metrics.get(key)
        if value is None or value == "":
            continue
        if key == "health_score":
            display = f"{fmt(value)}/100"
        else:
            display = fmt(value)
        color = STATUS_DANGER if key == "errors" else (STATUS_WARNING if key == "warnings" else tag_color)
        tile_specs.append((label, display, color))

    # Choose a column count based on how many tiles actually have real data
    # (never more columns than tiles), then stretch tile height to fill the
    # available vertical space evenly across however many rows result — a
    # sparse category (e.g. 1-2 auto-fetched SMM tiles) gets a small number
    # of large tiles instead of a handful of small ones huddled at the top
    # with the rest of the slide left blank.
    gap = 12
    n = len(tile_specs)
    if n == 0:
        sc.footer(
            f"Auto-fetched via social profile discovery & scraping (Snapshot Date: {datetime.now().strftime('%b %d, %Y')})."
            if is_auto_fetched
            else f"All numbers manually entered by the user (Snapshot Date: {datetime.now().strftime('%b %d, %Y')})."
        )
        return
    # With very few real tiles (1-2), use fewer/wider columns so each tile
    # gets real visual presence instead of sitting narrow on one side of a
    # mostly-empty row. With 3+ tiles, cap at 4 columns as before.
    cols = n if n <= 2 else min(4, n)
    rows = -(-n // cols)  # ceil
    content_h = y - MARGIN - 0.3 * inch
    tile_w = (PAGE_W - 2 * MARGIN - gap * (cols - 1)) / cols
    # kpi_tile's internal content (label/value/tag) is drawn at fixed offsets
    # from the top and bottom of the tile, so stretching a tile's height far
    # beyond its natural size just creates dead space INSIDE the card. Cap
    # tile height at a comfortable size (larger when very few tiles, so they
    # still carry real visual weight) and center the whole grid block
    # vertically in the available area, so leftover space becomes even
    # breathing room around the grid rather than empty page below it.
    max_tile_h = 2.4 * inch if n <= 2 else 1.55 * inch
    tile_h = min(max_tile_h, (content_h - gap * (rows - 1)) / rows)
    grid_h = tile_h * rows + gap * (rows - 1)
    top_row_y = y - (content_h - grid_h) / 2 - tile_h
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
# Layout coordinates for N populated quadrants (1-4), reflowing so an empty
# quadrant never renders as a blank/placeholder card. Each entry is a list of
# (x_frac, y_frac, w_frac, h_frac) fractions of the available content area.
def _estimate_bullet_lines(bullet: str, body_size: float, w: float, per_bullet_disclaimer: str | None = None) -> int:
    """Mirrors SlideCanvas._draw_bullet_text's greedy word-wrap exactly (bold
    'Label:' prefix + regular rest, wrapped as one continuous word stream
    within width w) so we can predict how many lines a bullet will occupy at
    a candidate body_size WITHOUT actually drawing it."""
    colon_idx = bullet.find(":")
    if 0 < colon_idx <= 60:
        label = bullet[: colon_idx + 1]
        rest = bullet[colon_idx + 1:].lstrip()
    else:
        label, rest = "", bullet

    lines = 1
    cursor_x = 0.0
    for word_group, is_bold in ((label, True), (rest, False)) if label else ((rest, False),):
        if not word_group:
            continue
        font = FONT_BOLD if is_bold else FONT_REGULAR
        for word in word_group.split():
            word_w = stringWidth(word + " ", font, body_size)
            if cursor_x + word_w > w and cursor_x > 0:
                lines += 1
                cursor_x = 0.0
            cursor_x += word_w

    if per_bullet_disclaimer:
        lines += len(_wrap_text(per_bullet_disclaimer, FONT_OBLIQUE, body_size - 1.5, w))
    return lines


def _estimate_text_block_height(w: float, heading: str, bullets: list[str], body_size: float,
                                heading_size: float, gap: float, icon: str | None = None,
                                per_bullet_disclaimer: str | None = None) -> float:
    """Predicts the total vertical space SlideCanvas.text_block() will
    consume for the given content at a candidate body_size, without drawing
    anything — the estimator side of the auto-fit sizing search below."""
    text_x_offset = (heading_size * 0.85) * 2 + 8 if icon else 0
    height = heading_size + 8 + 14  # heading line + underline gap
    bullet_w = w - 14 - text_x_offset
    for bullet in bullets:
        n_lines = _estimate_bullet_lines(bullet, body_size, bullet_w, per_bullet_disclaimer)
        height += n_lines * gap + 3
    return height


def _auto_fit_body_size(w: float, h: float, heading: str, bullets: list[str], heading_size: float,
                        icon: str | None = None, per_bullet_disclaimer: str | None = None,
                        min_size: float = 7.0, max_size: float = 12.5, gap_ratio: float = 1.24) -> float:
    """Picks the LARGEST body_size (within [min_size, max_size]) whose
    estimated text_block height fits inside the available height h, so
    sparse sections render with bigger, more readable text instead of always
    using a small size assumed to fit worst-case-dense content. Falls back
    to min_size if even that overflows (matches prior clamping behaviour —
    text may then run tight but never explodes off the card)."""
    if not bullets:
        return max_size
    best = min_size
    size = max_size
    while size >= min_size:
        gap = size * gap_ratio
        est_h = _estimate_text_block_height(w, heading, bullets, size, heading_size, gap, icon, per_bullet_disclaimer)
        if est_h <= h:
            best = size
            break
        size -= 0.2
    else:
        best = min_size
    return round(best, 1)


def _estimate_benefit_card_list_height(w: float, heading: str, cards: list[dict], title_size: float,
                                       body_size: float, gap: float, heading_size: float,
                                       icon: str | None = None) -> float:
    """Mirrors SlideCanvas.benefit_card_list's line-wrapping (via _wrap_text,
    same as it actually uses) to predict total height at a candidate size
    without drawing — the estimator for growth-recommendation cards."""
    height = _estimate_text_block_height(w, heading, [], heading_size, heading_size, heading_size, icon)
    for card in cards:
        title = card.get("title", "")
        detail = card.get("detail", "")
        benefit = card.get("benefit", "")
        combined = f"{title}: {detail}" if title and detail else (title or detail)
        n_lines = len(_wrap_text(combined, FONT_REGULAR, title_size, w - 24)) if combined else 0
        height += n_lines * (title_size + 4)
        if benefit:
            n_lines = len(_wrap_text(f"→ {benefit}", FONT_OBLIQUE, body_size, w - 32))
            height += n_lines * (body_size + 3)
        height += gap + 8
    return height


def _auto_fit_benefit_card_size(w: float, h: float, heading: str, cards: list[dict], heading_size: float,
                                icon: str | None = None, min_size: float = 6.5, max_size: float = 9.2) -> float:
    """Same largest-that-fits search as _auto_fit_body_size, applied to the
    title/detail/benefit card shape used by benefit_card_list."""
    if not cards:
        return max_size
    size = max_size
    while size >= min_size:
        est_h = _estimate_benefit_card_list_height(w, heading, cards, size, size - 0.8, 3, heading_size, icon)
        if est_h <= h:
            return round(size, 1)
        size -= 0.2
    return min_size


def _estimate_two_col_takeaways_height(col_w: float, items: list[str], body_size: float) -> float:
    """Mirrors _benchmark_slide's two-column takeaways loop (items alternate
    columns, each item's height is its wrapped line count * row_step, with a
    4pt extra drop before each new left-column row) to predict the total
    card height needed at a candidate body_size."""
    row_step = body_size + 1.9
    left_h = right_h = 0.0
    for i, item in enumerate(items):
        col = i % 2
        n_lines = len(_wrap_text(item, FONT_REGULAR, body_size, col_w - 20))
        item_h = n_lines * row_step
        if col == 0:
            if i > 0:
                left_h += 4
            left_h += item_h
        else:
            right_h += item_h
    return max(left_h, right_h) + 48  # + heading/top padding


def _auto_fit_takeaways_size(col_w: float, available_h: float, items: list[str],
                             min_size: float = 7.0, max_size: float = 10.5) -> float:
    if not items:
        return max_size
    size = max_size
    while size >= min_size:
        if _estimate_two_col_takeaways_height(col_w, items, size) <= available_h:
            return round(size, 1)
        size -= 0.2
    return min_size


def _quad_layout(n: int) -> list[tuple[float, float, float, float]]:
    if n <= 0:
        return []
    if n == 1:
        return [(0, 0, 1, 1)]
    if n == 2:
        return [(0, 0.5, 1, 0.5), (0, 0, 1, 0.5)]  # stacked, top then bottom
    if n == 3:
        return [(0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5), (0, 0, 1, 0.5)]  # 2 up top, 1 full-width bottom
    return [(0, 0.5, 0.5, 0.5), (0.5, 0.5, 0.5, 0.5), (0, 0, 0.5, 0.5), (0.5, 0, 0.5, 0.5)]  # full 2x2


def render_quad_grid(sc: SlideCanvas, title: str, subtitle: str, quads: list[tuple[str, list[str], str]]) -> None:
    """quads: list of (heading, bullets, icon) tuples. Any quad with an empty
    bullets list is skipped entirely (no placeholder card) — the remaining
    populated quads reflow to fill the available space via _quad_layout, so
    the slide never shows a blank or "Data not available" card."""
    populated = [(heading, bullets, icon) for heading, bullets, icon in quads if bullets]
    y = sc.header(title, subtitle)
    if not populated:
        sc.footer()
        return

    gap = 14
    content_w = PAGE_W - 2 * MARGIN
    content_h = y - MARGIN - 0.3 * inch
    n = len(populated)

    if n <= 2:
        # Stacked full-width card(s) — vertical space between them is freely
        # reassignable, so split it proportionally to each card's actual
        # estimated content need (at a shared body_size) instead of a fixed
        # 50/50 split, which otherwise leaves a short section floating in a
        # half-empty card while a longer one is unnecessarily cramped.
        card_w = content_w
        fit_sizes = [
            _auto_fit_body_size(card_w - 32, content_h - 22, heading, bullets, heading_size=11.5, icon=icon,
                               min_size=7.0, max_size=11.0)
            for heading, bullets, icon in populated
        ]
        body_size = min(fit_sizes)
        gap_size = round(body_size * 1.24, 1)

        est_heights = [
            _estimate_text_block_height(card_w - 32, heading, bullets, body_size, 11.5, gap_size, icon) + 44
            for heading, bullets, icon in populated
        ]
        if n == 1:
            heights = [max(1.1 * inch, min(est_heights[0], content_h))]
        else:
            avail = content_h - gap
            min_h = 1.1 * inch
            # Cap each card at its OWN estimated need (never stretch a short
            # section to fill leftover space, which just creates a bigger
            # blank gap inside that one card) — any genuinely unused space
            # collapses out of the stack and becomes even margin around the
            # whole block instead of dead space inside a specific card.
            heights = [max(min_h, min(h_est, avail)) for h_est in est_heights]
            if sum(heights) > avail:
                scale = avail / sum(heights)
                heights = [h * scale for h in heights]

        used_h = sum(heights) + gap * (n - 1)
        top_margin = max(0.0, (content_h - used_h) / 2)
        cy = MARGIN + content_h - top_margin
        for (heading, bullets, icon), card_h in zip(populated, heights):
            cy -= card_h
            sc.rounded_card(MARGIN, cy, card_w, card_h, radius=12)
            sc.text_block(MARGIN + 16, cy + card_h - 22, card_w - 32, heading, bullets, body_size=body_size,
                          heading_size=11.5, gap=gap_size, icon=icon)
            cy -= gap
        sc.footer()
        return

    layout = _quad_layout(n)

    # Auto-fit: measure each populated card's available w/h and pick the
    # largest body_size that fits its own bullets, then use the SMALLEST of
    # those per-card sizes across the slide so every card stays visually
    # consistent (no card looks tiny next to an oversized neighbor) while
    # still growing overall when content is sparse.
    card_dims = []
    for (heading, bullets, icon), (xf, yf, wf, hf) in zip(populated, layout):
        card_w = content_w * wf - (gap / 2 if wf < 1 else 0)
        card_h = content_h * hf - (gap / 2 if hf < 1 else 0)
        card_dims.append((card_w, card_h))

    fit_sizes = [
        _auto_fit_body_size(card_w - 32, card_h - 22, heading, bullets, heading_size=11.5, icon=icon,
                           min_size=7.0, max_size=11.0)
        for (heading, bullets, icon), (card_w, card_h) in zip(populated, card_dims)
    ]
    body_size = min(fit_sizes)
    gap_size = round(body_size * 1.24, 1)

    for (heading, bullets, icon), (xf, yf, wf, hf), (card_w, card_h) in zip(populated, layout, card_dims):
        x = MARGIN + content_w * xf + (gap / 2 if xf > 0 else 0)
        cy = MARGIN + content_h * yf + (gap / 2 if yf > 0 else 0)
        sc.rounded_card(x, cy, card_w, card_h, radius=12)
        sc.text_block(x + 16, cy + card_h - 22, card_w - 32, heading, bullets, body_size=body_size, heading_size=11.5, gap=gap_size, icon=icon)
    sc.footer()


def _section(ctx: dict[str, Any], category: str, slug: str) -> dict[str, list[str]]:
    per_cat = ctx["content"].get("per_category", {}).get(category, {})
    return per_cat.get(slug) or {}


def _bullets(section: dict[str, list[str]], sub_key: str) -> list[str]:
    """Returns the real bullet list, or an empty list if genuinely nothing
    was generated — callers (render_quad_grid etc.) skip empty sections
    entirely rather than showing a placeholder."""
    return section.get(sub_key) or []


# ------------------------------------------------------- current state ----
def render_current_state(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    category = ctx["category"]
    section = _section(ctx, category, "current_state")
    cat_label = CATEGORY_LABELS[category]
    labels = CATEGORY_CURRENT_STATE_LABELS[category]
    quads = [
        (labels["performance_overview"], _bullets(section, "performance_overview"), "▲"),
        (labels["technical_gaps"], _bullets(section, "technical_gaps"), "★"),
        (labels["content_gaps"], _bullets(section, "content_gaps"), "◆"),
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
        ("Client vs. Industry", _bullets(section, "client_vs_industry"), "▲"),
        ("Strategic Opportunities", _bullets(section, "strategic_opportunities"), "●"),
    ]
    populated = [(heading, bullets, icon) for heading, bullets, icon in halves if bullets]

    y = sc.header(f"Visibility Gap in {ctx['industry']}", cat_label)
    if not populated:
        sc.footer()
        return

    gap = 16
    card_h = y - MARGIN - 0.3 * inch
    disclaimer = "All numbers are indicative estimates based on available tools."

    if len(populated) == 1:
        # Only one side has real content — use the full width for it.
        heading, bullets, icon = populated[0]
        card_w = PAGE_W - 2 * MARGIN
        body_size = _auto_fit_body_size(card_w - 36, card_h - 26, heading, bullets, heading_size=12.5, icon=icon,
                                        per_bullet_disclaimer=disclaimer, min_size=7.0, max_size=11.5)
        gap_size = round(body_size * 1.24, 1)
        # Cap the card at its own estimated content need instead of always
        # filling the full slide height, so a short section doesn't render
        # as a mostly-empty card — leftover space becomes even margin
        # around a content-sized card instead.
        est_h = _estimate_text_block_height(card_w - 36, heading, bullets, body_size, 12.5, gap_size, icon,
                                            disclaimer) + 48
        actual_card_h = max(1.3 * inch, min(est_h, card_h))
        card_y = MARGIN + 0.3 * inch + (card_h - actual_card_h) / 2
        sc.rounded_card(MARGIN, card_y, card_w, actual_card_h, radius=12)
        sc.text_block(MARGIN + 18, card_y + actual_card_h - 26, card_w - 36, heading, bullets,
                      body_size=body_size, heading_size=12.5, gap=gap_size, icon=icon,
                      per_bullet_disclaimer=disclaimer)
    else:
        card_w = (PAGE_W - 2 * MARGIN - gap) / 2
        fit_sizes = [
            _auto_fit_body_size(card_w - 36, card_h - 26, heading, bullets, heading_size=12.5, icon=icon,
                               per_bullet_disclaimer=disclaimer, min_size=7.0, max_size=11.5)
            for heading, bullets, icon in populated
        ]
        body_size = min(fit_sizes)
        for i, (heading, bullets, icon) in enumerate(populated):
            x = MARGIN + i * (card_w + gap)
            sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
            sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 26, card_w - 36, heading, bullets,
                          body_size=body_size, heading_size=12.5, gap=round(body_size * 1.24, 1), icon=icon,
                          per_bullet_disclaimer=disclaimer)
    sc.footer()


# --------------------------------------------------- combined slides ----
def render_best_practices(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    """Always renders as ONE slide regardless of how many categories are
    selected — one card per selected category that actually has real
    content (a category with zero genuinely-supported bullets is skipped
    entirely, and the remaining cards reflow across the full slide width)."""
    categories = ctx["categories"]
    best_practices = ctx["content"].get("best_practices", {})
    industry = ctx["industry"]
    y = sc.header(f"Industry Best Practices in {industry}", "")

    populated_categories = [cat for cat in categories if best_practices.get(cat)]
    if not populated_categories:
        sc.footer()
        return

    n = len(populated_categories)
    gap = 14
    card_w = (PAGE_W - 2 * MARGIN - gap * (n - 1)) / n
    card_h = y - MARGIN - 0.3 * inch
    heading_size = (11.5 if n == 3 else 12.5) if n > 1 else 14

    headings = {
        cat: (f"Competitor Highlights — {CATEGORY_SHORT_LABEL[cat]}" if n > 1 else "Competitor Highlights")
        for cat in populated_categories
    }
    fit_sizes = [
        _auto_fit_body_size(card_w - 36, card_h - 26, headings[cat], best_practices.get(cat), heading_size=heading_size,
                           icon=CATEGORY_ICON.get(cat, "◆"), min_size=7.0, max_size=11.0)
        for cat in populated_categories
    ]
    body_size = min(fit_sizes)

    for i, cat in enumerate(populated_categories):
        x = MARGIN + i * (card_w + gap)
        bullets = best_practices.get(cat)
        heading = headings[cat]
        sc.rounded_card(x, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
        sc.text_block(x + 18, MARGIN + 0.3 * inch + card_h - 26, card_w - 36, heading, bullets,
                      body_size=body_size, heading_size=heading_size, gap=round(body_size * 1.24, 1),
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
    takeaways = benchmarks.get("takeaways") or []
    # Only reserve space for the takeaways card if it will actually be drawn
    # (both include_takeaways=True AND there's genuinely real content for
    # it) — otherwise the tables above expand to use the full slide height.
    show_takeaways = include_takeaways and bool(takeaways)
    full_h = y - MARGIN - 0.3 * inch
    if show_takeaways:
        takeaways_col_w = (PAGE_W - 2 * MARGIN - 36) / 2
        takeaways_font_size = _auto_fit_takeaways_size(takeaways_col_w, full_h - gap, takeaways,
                                                        min_size=7.5, max_size=10.5)
        needed_ty_h = _estimate_two_col_takeaways_height(takeaways_col_w, takeaways, takeaways_font_size)
        # Reserve only as much height as the takeaways content actually
        # needs (clamped to a sane minimum/maximum) so the tables above
        # expand to fill the rest instead of leaving fixed blank space.
        ty_card_h = max(1.1 * inch, min(needed_ty_h, full_h - gap - 1.5 * inch))
        top_card_h = full_h - gap - ty_card_h
    else:
        top_card_h = full_h

    left_headers = client_table.get("headers") or ["Metric", "Current Status", "Trend"]
    left_rows = client_table.get("rows") or []
    right_headers = industry_table.get("headers") or ["Metric", company, "Industry"]
    right_rows = industry_table.get("rows") or []

    # Scale row height to the available card height (up to a comfortable
    # cap) so a table with few real rows uses taller rows rather than
    # leaving blank space below a handful of default-height rows. If even
    # the capped row height doesn't consume the full card (very few rows),
    # shrink the card itself to the table's real content need and center it
    # in the available slot, so leftover space becomes even margin instead
    # of a mostly-empty card.
    max_rows = max(len(left_rows), len(right_rows), 1)
    row_h = 26.0
    table_top_y = y
    card_top_y = y
    if not show_takeaways:
        # No competing takeaways card below — safe to shrink the table cards
        # to their real content need and center the pair in the available
        # slide height, rather than always stretching to fill it.
        table_content_h = 44 + row_h * (max_rows + 1) + 14
        fitted_card_h = max(1.6 * inch, min(table_content_h, top_card_h))
        if fitted_card_h < top_card_h:
            y_offset = (top_card_h - fitted_card_h) / 2
            table_top_y = y - y_offset
            card_top_y = y - y_offset
        top_card_h = fitted_card_h

    sc.rounded_card(MARGIN, card_top_y - top_card_h, card_w, top_card_h, radius=12)
    c = sc.c
    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 12)
    c.drawString(MARGIN + 18, table_top_y - 26, f"{company} Technical Performance")
    sc.table(MARGIN + 18, table_top_y - 44, card_w - 36, left_headers, left_rows, row_h=row_h)

    rx = MARGIN + card_w + gap
    sc.rounded_card(rx, card_top_y - top_card_h, card_w, top_card_h, radius=12)
    c.setFillColor(ACCENT_PURPLE)
    c.setFont(FONT_BOLD, 12)
    c.drawString(rx + 18, table_top_y - 26, "Industry Comparison")
    sc.table(rx + 18, table_top_y - 44, card_w - 36, right_headers, right_rows, row_h=row_h)

    if show_takeaways:
        ty_card_y = MARGIN
        sc.rounded_card(MARGIN, ty_card_y, PAGE_W - 2 * MARGIN, ty_card_h, radius=12)
        c.setFillColor(ACCENT_PURPLE)
        c.setFont(FONT_BOLD, 12)
        c.drawString(MARGIN + 18, ty_card_y + ty_card_h - 26, "Strategic Takeaways & Opportunities")
        col_w = takeaways_col_w
        row_step = takeaways_font_size + 1.9
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
            c.setFont(FONT_REGULAR, takeaways_font_size)
            for line in _wrap(item, FONT_REGULAR, takeaways_font_size, col_w - 20):
                c.drawString(x + 10, yy, line)
                yy -= row_step
            if col == 1:
                ty = min(ty, yy) - 3
    sc.footer()


def render_benchmarks(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    _benchmark_slide(sc, ctx, include_takeaways=not ctx.get("has_strategic_takeaways_slide", False))


def render_strategic_takeaways(sc: SlideCanvas, ctx: dict[str, Any]) -> None:
    benchmarks = ctx["content"].get("benchmarks", {})
    takeaways = benchmarks.get("takeaways") or []
    y = sc.header("Strategic Takeaways & Opportunities", ctx["company_name"])
    if not takeaways:
        sc.footer()
        return
    card_w = PAGE_W - 2 * MARGIN
    card_h = y - MARGIN - 0.3 * inch
    heading = "Key Opportunities Across the Board"
    body_size = _auto_fit_body_size(card_w - 40, card_h - 30, heading, takeaways, heading_size=14, icon="★",
                                    min_size=8.0, max_size=12.5)
    sc.rounded_card(MARGIN, MARGIN + 0.3 * inch, card_w, card_h, radius=12)
    sc.text_block(MARGIN + 20, MARGIN + 0.3 * inch + card_h - 30, card_w - 40, heading, takeaways,
                  body_size=body_size, heading_size=14, gap=round(body_size * 1.3, 1), icon="★")
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
    heading_size = {1: 13, 2: 13, 3: 11}.get(n, 11)

    block_titles = {cat: CATEGORY_GROWTH_BLOCK_TITLE.get(cat, cat.upper()) for cat in categories}
    fit_sizes = [
        _auto_fit_benefit_card_size(card_w - 36, card_h - 24, block_titles[cat], growth.get(cat) or [],
                                    heading_size=heading_size, icon=CATEGORY_ICON.get(cat, "●"),
                                    min_size=6.5, max_size=9.5)
        for cat in categories
    ]
    body_size = min(fit_sizes) if fit_sizes else 9.5
    for i, cat in enumerate(categories):
        x = MARGIN + i * (card_w + gap)
        cards = growth.get(cat) or []
        block_title = block_titles[cat]
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
