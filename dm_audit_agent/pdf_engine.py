"""
pdf_engine.py — reusable slide-drawing primitives for the audit report PDF.

Built with ReportLab (pure Python, no native/GTK dependency — WeasyPrint was
tried first but requires system-level Pango/Cairo libraries not present on
this machine, so this pure-Python renderer is used instead to guarantee the
report always generates without errors).

Visual language follows Design.md (Trilliant glassmorphism system) adapted to
print: brand purple/indigo accents, rounded cards, colored left-accent bars,
uppercase micro-labels — and mirrors the layout of the reference PDFs
(vertiv_digital_audit / karishye_audit_growth_strategy): a title band, a
content area of one or more rounded cards, and a footer disclaimer line.
"""

from __future__ import annotations

from dataclasses import dataclass
from textwrap import wrap
from typing import Callable, Optional

from reportlab.lib.colors import Color, HexColor
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import inch
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = landscape((11 * inch, 8.5 * inch))

# ---- Palette (from Design.md) ----
NAVY = HexColor("#1E1B4B")
TEXT_SECONDARY = HexColor("#475569")
TEXT_MUTED = HexColor("#9CA3AF")
SURFACE_BASE = HexColor("#EFF3FC")
WHITE = HexColor("#FFFFFF")
BORDER = HexColor("#E2E8F0")

ACCENT_PURPLE = HexColor("#7C3AED")
ACCENT_INDIGO = HexColor("#4F46E5")
ACCENT_SKY = HexColor("#0EA5E9")

STATUS_SUCCESS = HexColor("#10B981")
STATUS_WARNING = HexColor("#F59E0B")
STATUS_DANGER = HexColor("#DC2626")
STATUS_INFO = HexColor("#0EA5E9")

DARK_BAND = HexColor("#1E1B4B")

FONT_REGULAR = "Helvetica"
FONT_BOLD = "Helvetica-Bold"
FONT_OBLIQUE = "Helvetica-Oblique"

MARGIN = 0.45 * inch


def _alpha(color: Color, alpha: float) -> Color:
    return Color(color.red, color.green, color.blue, alpha=alpha)


def _wrap_text(text: str, font: str, size: float, max_width: float) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if stringWidth(candidate, font, size) <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


@dataclass
class Card:
    x: float
    y: float
    w: float
    h: float


class SlideCanvas:
    """Thin wrapper around a ReportLab canvas page giving Design.md-flavoured
    drawing primitives (rounded cards, accent bars, KPI tiles, tables)."""

    def __init__(self, c: canvas.Canvas):
        self.c = c

    # ---- page chrome ----
    def background(self) -> None:
        self.c.setFillColor(SURFACE_BASE)
        self.c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    def header(self, title: str, subtitle: str = "") -> float:
        """Draws the slide title band (top-left big bold title, small brand
        mark top-right). Returns the y-coordinate where content may start."""
        self.background()
        c = self.c
        top_y = PAGE_H - MARGIN - 6
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 22)
        max_w = PAGE_W - 2 * MARGIN - 1.6 * inch
        lines = _wrap_text(title.upper(), FONT_BOLD, 22, max_w)
        y = top_y
        for line in lines[:2]:
            c.drawString(MARGIN, y, line)
            y -= 26
        if subtitle:
            c.setFillColor(ACCENT_PURPLE)
            c.setFont(FONT_BOLD, 12)
            c.drawString(MARGIN, y - 4, subtitle.upper())
            y -= 22

        # brand mark top-right
        c.setFillColor(TEXT_SECONDARY)
        c.setFont(FONT_BOLD, 11)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 4, "trilliant digital")
        c.setFillColor(ACCENT_SKY)
        c.setFont(FONT_OBLIQUE, 7.5)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN - 16, '"Dexterity in Action"')

        return y - 14

    def footer(self, text: str = "All numbers are indicative estimates based on available tools.") -> None:
        c = self.c
        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_OBLIQUE, 7.5)
        c.drawString(MARGIN, MARGIN * 0.55, text)

    def new_page(self) -> None:
        self.c.showPage()

    # ---- primitives ----
    def rounded_card(self, x: float, y: float, w: float, h: float, radius: float = 10,
                      fill: Color = WHITE, border: Optional[Color] = BORDER,
                      accent_left: Optional[Color] = None, accent_top: Optional[Color] = None) -> None:
        c = self.c
        c.setFillColor(fill)
        if border:
            c.setStrokeColor(border)
            c.setLineWidth(0.75)
            c.roundRect(x, y, w, h, radius, fill=1, stroke=1)
        else:
            c.roundRect(x, y, w, h, radius, fill=1, stroke=0)
        if accent_left:
            c.setFillColor(accent_left)
            c.roundRect(x, y, 5, h, 2, fill=1, stroke=0)
        if accent_top:
            c.setFillColor(accent_top)
            c.roundRect(x, y + h - 5, w, 5, 2, fill=1, stroke=0)

    def text_block(self, x: float, y: float, w: float, heading: str, bullets: list[str],
                   heading_color: Color = ACCENT_PURPLE, body_size: float = 9.2,
                   heading_size: float = 12.5, gap: float = 13.5, icon: Optional[str] = None,
                   per_bullet_disclaimer: Optional[str] = None) -> float:
        """Draws a heading (optionally with a light-blue icon-circle badge,
        matching the reference template) + bullet list inside a card;
        returns the y-coordinate after the last line drawn. If
        per_bullet_disclaimer is set, that italic line is drawn under EVERY
        bullet (matching the reference Visibility Gap slide's repeated
        "All numbers are indicative..." line) instead of only once in the
        page footer."""
        c = self.c
        text_x = x
        if icon:
            circle_r = heading_size * 0.85
            c.setFillColor(_alpha(ACCENT_INDIGO, 0.12))
            c.circle(x + circle_r, y - circle_r * 0.55, circle_r, fill=1, stroke=0)
            c.setFillColor(ACCENT_INDIGO)
            c.setFont(FONT_BOLD, heading_size * 0.9)
            c.drawCentredString(x + circle_r, y - circle_r * 0.55 - heading_size * 0.32, icon)
            text_x = x + circle_r * 2 + 8

        c.setFillColor(heading_color)
        c.setFont(FONT_BOLD, heading_size)
        c.drawString(text_x, y, heading)
        y -= heading_size + 8
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(x, y, x + w, y)
        y -= 14

        c.setFont(FONT_REGULAR, body_size)
        for bullet in bullets:
            c.setFillColor(ACCENT_PURPLE)
            c.circle(x + 2, y + 3, 1.5, fill=1, stroke=0)
            c.setFillColor(NAVY)
            y = self._draw_bullet_text(x + 10, y, w - 14, bullet, body_size, gap)
            if per_bullet_disclaimer:
                c.setFillColor(TEXT_MUTED)
                c.setFont(FONT_OBLIQUE, body_size - 1.5)
                for line in _wrap_text(per_bullet_disclaimer, FONT_OBLIQUE, body_size - 1.5, w - 14):
                    c.drawString(x + 10, y, line)
                    y -= (body_size - 1.5) + 3
            y -= 3
        return y

    def _draw_bullet_text(self, x: float, y: float, w: float, bullet: str, body_size: float, gap: float) -> float:
        """Draws a bullet's text, bolding a leading 'Label:' phrase (matching
        the reference template's '**Health Score [XX/100]:** text...' style)
        while the rest stays regular weight — wrapping across lines as needed."""
        c = self.c
        colon_idx = bullet.find(":")
        # Only treat it as a bold label if the colon is reasonably early
        # (a real label, not a colon inside the explanation text).
        if 0 < colon_idx <= 60:
            label = bullet[: colon_idx + 1]
            rest = bullet[colon_idx + 1:].lstrip()
        else:
            label, rest = "", bullet

        cursor_x = x
        for word_group, is_bold in ((label, True), (rest, False)) if label else ((rest, False),):
            if not word_group:
                continue
            for word in word_group.split():
                font = FONT_BOLD if is_bold else FONT_REGULAR
                word_w = stringWidth(word + " ", font, body_size)
                if cursor_x + word_w > x + w and cursor_x > x:
                    y -= gap
                    cursor_x = x
                c.setFont(font, body_size)
                c.drawString(cursor_x, y, word)
                cursor_x += word_w
        return y - gap

    def benefit_card_list(self, x: float, y: float, w: float, heading: str, cards: list[dict],
                          heading_color: Color = ACCENT_PURPLE, icon: Optional[str] = None,
                          title_size: float = 9.2, body_size: float = 8.4, gap: float = 3,
                          heading_size: float = 13) -> float:
        """Draws a heading + a list of {title, detail, benefit} cards, each
        rendered as: **Title:** detail, then an indented arrow-prefixed
        italic benefit line — matching the Growth Recommendations reference
        slide exactly."""
        c = self.c
        y = self.text_block(x, y, w, heading, [], heading_color=heading_color, heading_size=heading_size, icon=icon)
        for card in cards:
            title = card.get("title", "")
            detail = card.get("detail", "")
            benefit = card.get("benefit", "")

            c.setFillColor(ACCENT_PURPLE)
            c.circle(x + 12, y + 3, 1.5, fill=1, stroke=0)
            combined = f"{title}: {detail}" if title and detail else (title or detail)
            lines = _wrap_text(combined, FONT_REGULAR, title_size, w - 24)
            for i, line in enumerate(lines):
                if i == 0 and title:
                    bold_part = f"{title}:"
                    c.setFont(FONT_BOLD, title_size)
                    c.setFillColor(NAVY)
                    c.drawString(x + 20, y, bold_part)
                    bold_w = stringWidth(bold_part + " ", FONT_BOLD, title_size)
                    c.setFont(FONT_REGULAR, title_size)
                    rest = line[len(bold_part):].strip()
                    c.drawString(x + 20 + bold_w, y, rest)
                else:
                    c.setFont(FONT_REGULAR, title_size)
                    c.setFillColor(NAVY)
                    c.drawString(x + 20, y, line)
                y -= title_size + 4
            if benefit:
                c.setFillColor(ACCENT_INDIGO)
                c.setFont(FONT_OBLIQUE, body_size)
                for line in _wrap_text(f"→ {benefit}", FONT_OBLIQUE, body_size, w - 32):
                    c.drawString(x + 24, y, line)
                    y -= body_size + 3
            y -= gap + 8
        return y

    def numbered_card(self, x: float, y: float, w: float, number: int, title: str,
                      detail: str, impact: str = "", impact_label: str = "Business Impact") -> float:
        """Draws a numbered-circle heading (1/2/3/4) + bold title + detail +
        italic 'Business Impact:' line, matching the Summary & Next Steps
        reference slide."""
        c = self.c
        circle_r = 9
        c.setFillColor(ACCENT_INDIGO)
        c.circle(x + circle_r, y - circle_r, circle_r, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 9.5)
        c.drawCentredString(x + circle_r, y - circle_r - 3.3, str(number))

        text_x = x + circle_r * 2 + 10
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 11)
        c.drawString(text_x, y - 4, title)
        y -= 20

        c.setFont(FONT_REGULAR, 8.6)
        c.setFillColor(TEXT_SECONDARY)
        for line in _wrap_text(detail, FONT_REGULAR, 8.6, w - (text_x - x) - 10):
            c.drawString(text_x, y, line)
            y -= 12

        if impact:
            y -= 3
            c.setFont(FONT_OBLIQUE, 8)
            c.setFillColor(TEXT_MUTED)
            for line in _wrap_text(f"{impact_label}: {impact}", FONT_OBLIQUE, 8, w - (text_x - x) - 10):
                c.drawString(text_x, y, line)
                y -= 11
        return y - 14

    def numbered_card_compact(self, x: float, y: float, w: float, number: int, title: str,
                              detail: str, impact: str = "") -> float:
        """A tighter numbered-item layout for slides with many items in a
        column (e.g. 6 items per column) — small numbered circle, bold title
        on the same line where it fits, 1-2 line detail, and the impact
        folded into a single italic line rather than its own labeled block."""
        c = self.c
        circle_r = 7
        c.setFillColor(ACCENT_INDIGO)
        c.circle(x + circle_r, y - circle_r, circle_r, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 7.5)
        c.drawCentredString(x + circle_r, y - circle_r - 2.6, str(number))

        text_x = x + circle_r * 2 + 8
        text_w = w - (text_x - x) - 6
        c.setFillColor(NAVY)
        c.setFont(FONT_BOLD, 8.6)
        title_lines = _wrap_text(title, FONT_BOLD, 8.6, text_w)
        c.drawString(text_x, y - 3, title_lines[0])
        y -= 14

        c.setFont(FONT_REGULAR, 7.6)
        c.setFillColor(TEXT_SECONDARY)
        detail_lines = _wrap_text(detail, FONT_REGULAR, 7.6, text_w)[:2]
        for line in detail_lines:
            c.drawString(text_x, y, line)
            y -= 10

        if impact:
            c.setFont(FONT_OBLIQUE, 7.2)
            c.setFillColor(TEXT_MUTED)
            impact_lines = _wrap_text(impact, FONT_OBLIQUE, 7.2, text_w)
            if impact_lines:
                line = impact_lines[0]
                if len(impact_lines) > 1:
                    while stringWidth(line + "…", FONT_OBLIQUE, 7.2) > text_w and len(line) > 1:
                        line = line[:-1]
                    line = line.rstrip() + "…"
                c.drawString(text_x, y, line)
                y -= 10
        return y - 8

    def kpi_tile(self, x: float, y: float, w: float, h: float, label: str, value: str,
                 tag: str = "", tag_color: Color = STATUS_SUCCESS, top_accent: Color = STATUS_SUCCESS) -> None:
        c = self.c
        self.rounded_card(x, y, w, h, radius=10, fill=WHITE, border=BORDER, accent_top=top_accent)
        inner_w = w - 24

        c.setFillColor(TEXT_MUTED)
        c.setFont(FONT_BOLD, 8)
        for line in _wrap_text(label.upper(), FONT_BOLD, 8, inner_w)[:1]:
            c.drawString(x + 12, y + h - 22, line)

        c.setFillColor(NAVY)
        value_text = str(value)
        # Auto-shrink long values (e.g. "Food and Beverage", "Authentic, warm,
        # and approachable") instead of overflowing the tile — short numeric
        # values (e.g. "4.9K") keep the original large 22pt size.
        size = 22
        min_size = 10
        while size > min_size and stringWidth(value_text, FONT_BOLD, size) > inner_w:
            size -= 1
        c.setFont(FONT_BOLD, size)
        lines = _wrap_text(value_text, FONT_BOLD, size, inner_w)
        if len(lines) > 2:
            lines = lines[:2]
            lines[-1] = lines[-1].rstrip() + "…"
        value_y = y + h - 40 if len(lines) > 1 else y + h - 52
        line_gap = size + 4
        for i, line in enumerate(lines):
            c.drawString(x + 12, value_y - i * line_gap, line)

        if tag:
            tag_w = stringWidth(tag, FONT_BOLD, 7.5) + 14
            c.setFillColor(Color(tag_color.red, tag_color.green, tag_color.blue, alpha=0.12))
            c.roundRect(x + 12, y + 10, tag_w, 16, 8, fill=1, stroke=0)
            c.setFillColor(tag_color)
            c.setFont(FONT_BOLD, 7.5)
            c.drawString(x + 18, y + 15, tag)

    def table(self, x: float, y: float, w: float, headers: list[str], rows: list[list[str]],
              col_widths: Optional[list[float]] = None, row_h: float = 20,
              header_fill: Color = NAVY, zebra: bool = True) -> float:
        c = self.c
        n = len(headers)
        widths = col_widths or [w / n] * n
        c.setFillColor(header_fill)
        c.roundRect(x, y - row_h, w, row_h, 4, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 8.5)
        cx = x + 10
        for i, hdr in enumerate(headers):
            c.drawString(cx, y - row_h + 6, hdr.upper())
            cx += widths[i]
        y -= row_h

        for ridx, row in enumerate(rows):
            if zebra and ridx % 2 == 1:
                c.setFillColor(HexColor("#F8FAFC"))
                c.rect(x, y - row_h, w, row_h, fill=1, stroke=0)
            c.setFillColor(NAVY)
            c.setFont(FONT_REGULAR, 8.5)
            cx = x + 10
            for i, cell in enumerate(row):
                c.setFont(FONT_BOLD if i == 0 else FONT_REGULAR, 8.5)
                c.drawString(cx, y - row_h + 6, str(cell)[:40])
                cx += widths[i]
            c.setStrokeColor(BORDER)
            c.setLineWidth(0.4)
            c.line(x, y - row_h, x + w, y - row_h)
            y -= row_h
        return y

    def dark_panel(self, x: float, y: float, w: float, h: float, eyebrow: str, heading: str,
                   body_lines: list[str]) -> None:
        c = self.c
        self.rounded_card(x, y, w, h, radius=14, fill=DARK_BAND, border=None)
        yy = y + h - 26
        if eyebrow:
            c.setFillColor(ACCENT_SKY)
            c.setFont(FONT_BOLD, 8.5)
            c.drawString(x + 16, yy, eyebrow.upper())
            yy -= 20
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 14)
        for line in _wrap_text(heading, FONT_BOLD, 14, w - 32):
            c.drawString(x + 16, yy, line)
            yy -= 18
        yy -= 6
        c.setFont(FONT_REGULAR, 8.8)
        c.setFillColor(HexColor("#CBD5E1"))
        for line in body_lines:
            for wline in _wrap_text(line, FONT_REGULAR, 8.8, w - 32):
                c.drawString(x + 16, yy, wline)
                yy -= 13


def build_pdf(path: str, slide_fns: list[Callable[[SlideCanvas], None]]) -> str:
    """slide_fns: list of callables, each given a SlideCanvas for one page.
    Each callable is responsible for drawing its own header/footer/content."""
    c = canvas.Canvas(path, pagesize=(PAGE_W, PAGE_H))
    sc = SlideCanvas(c)
    for fn in slide_fns:
        fn(sc)
        sc.new_page()
    c.save()
    return path
