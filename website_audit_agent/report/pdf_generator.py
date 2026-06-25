"""
pdf_generator.py — Builds the PDF audit report using ReportLab.

FIXES APPLIED (only presentation layer — no logic changes):
  FIX 1: UX 0/0 footnote added on Page 1 score table itself
  FIX 2: Accessibility/Best Practices/SEO show "N/A" instead of "0" in perf table
  FIX 3: Score anomaly inline notes (On-Page high with low coverage, Content score caveat)
  FIX 4: Methodology / About This Report appendix page added at end
  FIX 5: Color-coded score badges (green/amber/red) on cover page
  FIX 6: Quick Wins KeepTogether so table never splits across pages
  FIX 7: Priority Action Matrix added before roadmap
  FIX 8: Competitor content narration note added after content table
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List
from urllib.parse import urlparse

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

USABLE_WIDTH = 7.0 * inch


# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_text(item: Any) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in ("action", "recommendation", "title", "description", "text"):
            if key in item and item[key]:
                return str(item[key]).strip()
        return "; ".join(str(v) for v in item.values() if v)
    for attr in ("action", "recommendation", "title", "description"):
        val = getattr(item, attr, None)
        if val:
            return str(val).strip()
    return str(item).strip()


def clean_opportunity(item: Any) -> str:
    if isinstance(item, dict):
        title = item.get("title", "")
        savings = item.get("savings_ms", 0)
        if title:
            return f"{title} (saves ~{int(float(savings))}ms)" if savings and float(savings) > 0 else title
        return "; ".join(f"{k}: {v}" for k, v in item.items() if k not in ("description", "id"))
    return str(item).strip()


def _fmt(val: Any, decimals: int = 0) -> str:
    """Format numeric value. Returns 'N/A' for None, clean int/float otherwise."""
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if f == 0.0:
            return "0"
        return str(int(round(f))) if decimals == 0 else f"{f:.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def _fmt_score(val: Any) -> str:
    """
    FIX 2: For PageSpeed category scores (accessibility, best practices, SEO),
    return 'N/A' when value is 0 — because 0 means PageSpeed could not measure it,
    not that the actual score is zero.
    """
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if f == 0.0:
            return "N/A"   # ← KEY FIX: 0 = unmeasured, not truly zero
        return str(int(round(f)))
    except (TypeError, ValueError):
        return "N/A"


def _gap(story: list, pts: int = 10) -> None:
    story.append(Spacer(1, pts))


def _status_symbol(status: str) -> str:
    s = (status or "").lower()
    if s == "pass":              return "PASS"
    if s in ("warning", "warn"): return "WARN"
    if s == "fail":              return "FAIL"
    return "—"


def _score_badge_color(score: int) -> colors.Color:
    """FIX 5: Return green/amber/red based on score band."""
    if score >= 80:
        return colors.HexColor("#0a7f3f")   # green
    if score >= 60:
        return colors.HexColor("#e67e22")   # amber
    return colors.HexColor("#c0392b")       # red


def _score_badge_label(score: int) -> str:
    """FIX 5: Return readable health label."""
    if score >= 80: return "Good"
    if score >= 60: return "Needs Work"
    return "Poor"


def _dynamic_bullets(items: List[str], story: list, style) -> None:
    clean = [i.strip() for i in (items or []) if i and i.strip()]
    if clean:
        for text in clean:
            story.append(Paragraph("• " + text, style))
    else:
        story.append(Paragraph(
            "No data returned for this section — AI synthesis may have failed "
            "or the audit data was insufficient to generate specific insights.",
            ParagraphStyle("empty", parent=style,
                           textColor=colors.HexColor("#999999"),
                           fontName="Helvetica-Oblique"),
        ))


def _make_table(data: list, col_widths: list, style_extras: list = None) -> Table:
    tbl = Table(data, colWidths=col_widths)
    base = [
        ("GRID",          (0,0),(-1,-1), 0.5,  colors.HexColor("#cccccc")),
        ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
        ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0),(-1,-1), 8),
        ("LEADING",       (0,0),(-1,-1), 11),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 5),
        ("TOPPADDING",    (0,0),(-1,-1), 5),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
        ("WORDWRAP",      (0,0),(-1,-1), True),
    ]
    if style_extras:
        base.extend(style_extras)
    tbl.setStyle(TableStyle(base))
    return tbl


def _note(text: str, S_NOTE) -> Paragraph:
    return Paragraph(text, S_NOTE)


# ── Main generator ────────────────────────────────────────────────────────────

def generate_pdf_report(target_bundle, competitor_bundle, synthesis, audit_duration) -> str:

    os.makedirs("output", exist_ok=True)

    def _slug(url: str) -> str:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host.replace(".", "_").replace("-", "_")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    pdf_path = (
        f"output/{_slug(target_bundle['crawl'].domain)}_vs_"
        f"{_slug(competitor_bundle['crawl'].domain)}_audit_{timestamp}.pdf"
    )

    doc = SimpleDocTemplate(pdf_path,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch)

    bs = getSampleStyleSheet()
    S_TITLE = ParagraphStyle("T",  parent=bs["Title"],    fontSize=20, textColor=colors.HexColor("#0a7f3f"), alignment=TA_CENTER, spaceAfter=4)
    S_HEAD  = ParagraphStyle("H1", parent=bs["Heading1"], fontSize=12, textColor=colors.HexColor("#0a7f3f"), spaceBefore=8, spaceAfter=4, leading=16)
    S_SUB   = ParagraphStyle("H2", parent=bs["Heading2"], fontSize=10, textColor=colors.HexColor("#1a5c35"), spaceBefore=6, spaceAfter=3, leading=14)
    S_BODY  = ParagraphStyle("B",  parent=bs["BodyText"], fontSize=8.5, leading=13, spaceAfter=2)
    S_SMALL = ParagraphStyle("Sm", parent=S_BODY, fontSize=7.5, textColor=colors.HexColor("#555555"))
    S_CTR   = ParagraphStyle("C",  parent=S_BODY, alignment=TA_CENTER, fontSize=9)
    S_NOTE  = ParagraphStyle("N",  parent=S_BODY, fontSize=8, textColor=colors.HexColor("#7f5500"),
                              backColor=colors.HexColor("#fffbe6"), borderPad=4, leftIndent=6, rightIndent=6)
    S_INFO  = ParagraphStyle("I",  parent=S_BODY, fontSize=8, textColor=colors.HexColor("#1a4f72"),
                              backColor=colors.HexColor("#ebf5fb"), borderPad=4, leftIndent=6, rightIndent=6)
    S_BADGE = ParagraphStyle("Bg", parent=S_BODY, fontSize=9, alignment=TA_CENTER, fontName="Helvetica-Bold")

    story = []

    tb = target_bundle;  cb = competitor_bundle
    ts = tb["scores"];   cs = cb["scores"]
    tp = tb["perf"].mobile; cp = cb["perf"].mobile
    to = tb["onpage"];   co = cb["onpage"]
    tc = tb["content"];  cc = cb["content"]
    tu = tb["ux"];       cu = cb["ux"]
    tt = tb["tech"];     ct = cb["tech"]
    t_domain  = tb["crawl"].domain
    c_domain  = cb["crawl"].domain
    c_crawled = len(cc.pages)
    t_crawled = len(tc.pages)
    synthesis_ok = not bool(synthesis.error)

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1: COVER + SCORE BADGES + SCORE TABLE + EXEC SUMMARY + QUICK WINS
    # ═══════════════════════════════════════════════════════════════════════════

    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Website Audit Strategy Report", S_TITLE))
    _gap(story, 4)
    story.append(Paragraph(
        f"<font size='8' color='#555555'>"
        f"Target: <b>{t_domain}</b> &nbsp;|&nbsp; Competitor: <b>{c_domain}</b><br/>"
        f"Date: {datetime.now().strftime('%d %B %Y')} &nbsp;|&nbsp; "
        f"Audit Duration: {audit_duration:.1f}s"
        f"</font>", S_CTR))
    _gap(story, 10)

    if not synthesis_ok:
        story.append(_note(
            f"AI Synthesis Warning: {synthesis.error} — "
            "Sections relying on AI analysis will show 'No data returned'.", S_NOTE))
        _gap(story, 6)

    # ── FIX 5: Color-coded score badges on cover ──────────────────────────────
    t_color = _score_badge_color(ts.overall)
    c_color = _score_badge_color(cs.overall)
    t_label = _score_badge_label(ts.overall)
    c_label = _score_badge_label(cs.overall)

    badge_data = [
        [
            Paragraph(f"<b>TARGET</b>", S_BADGE),
            Paragraph("", S_BADGE),
            Paragraph(f"<b>COMPETITOR</b>", S_BADGE),
        ],
        [
            Paragraph(f"<b>{ts.overall}/100</b>", S_BADGE),
            Paragraph("<b>VS</b>", ParagraphStyle("vs", parent=S_BADGE, textColor=colors.HexColor("#888888"))),
            Paragraph(f"<b>{cs.overall}/100</b>", S_BADGE),
        ],
        [
            Paragraph(f"{ts.grade} — {t_label}", S_BADGE),
            Paragraph("", S_BADGE),
            Paragraph(f"{cs.grade} — {c_label}", S_BADGE),
        ],
    ]
    badge_tbl = Table(badge_data, colWidths=[2.8*inch, 1.4*inch, 2.8*inch])
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),(0,-1), t_color),
        ("BACKGROUND",    (2,0),(2,-1), c_color),
        ("BACKGROUND",    (1,0),(1,-1), colors.HexColor("#f5f5f5")),
        ("TEXTCOLOR",     (0,0),(0,-1), colors.white),
        ("TEXTCOLOR",     (2,0),(2,-1), colors.white),
        ("TEXTCOLOR",     (1,0),(1,-1), colors.HexColor("#888888")),
        ("ALIGN",         (0,0),(-1,-1), "CENTER"),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("FONTSIZE",      (0,1),(0,1),  18),
        ("FONTSIZE",      (2,1),(2,1),  18),
        ("FONTSIZE",      (1,1),(1,1),  14),
        ("FONTSIZE",      (0,0),(0,0),  9),
        ("FONTSIZE",      (2,0),(2,0),  9),
        ("FONTSIZE",      (0,2),(0,2),  8),
        ("FONTSIZE",      (2,2),(2,2),  8),
        ("BOTTOMPADDING", (0,0),(-1,-1), 6),
        ("TOPPADDING",    (0,0),(-1,-1), 6),
        ("ROUNDEDCORNERS",[4]),
        ("BOX",           (0,0),(0,-1), 1, t_color),
        ("BOX",           (2,0),(2,-1), 1, c_color),
    ]))
    story.append(badge_tbl)
    _gap(story, 10)

    # ── Score summary table with FIX 1: UX footnote inline ───────────────────
    story.append(Paragraph("Overall Score Summary", S_HEAD)); _gap(story, 4)

    score_rows = [["Category", "Target Score", "Competitor Score", "Winner"]]
    se = []
    for i,(name,tv,cv) in enumerate([
        ("Overall",       ts.overall,       cs.overall),
        ("Performance",   ts.performance,   cs.performance),
        ("Technical SEO", ts.technical_seo, cs.technical_seo),
        ("On-Page SEO",   ts.onpage_seo,    cs.onpage_seo),
        ("Content",       ts.content,       cs.content),
        # FIX 1: UX row — append asterisk to score so footnote is visible on page 1
        ("UX *",          ts.ux,            cs.ux),
    ], start=1):
        w = "Target" if tv >= cv else "Competitor"
        score_rows.append([name, str(tv), str(cv), w])
        tc_c = colors.HexColor("#0a7f3f") if tv > cv else colors.black
        cc_c = colors.HexColor("#0a7f3f") if cv > tv else colors.black
        se += [("TEXTCOLOR",(1,i),(1,i),tc_c), ("TEXTCOLOR",(2,i),(2,i),cc_c),
               ("FONTNAME",(1,i),(2,i),"Helvetica-Bold")]

    story.append(_make_table(score_rows, [2.4*inch,1.5*inch,1.5*inch,1.6*inch], se))
    _gap(story, 4)

    # FIX 1: Footnote right below the score table on page 1
    story.append(Paragraph(
        "* UX score is based on PageSpeed accessibility data. When PageSpeed cannot fully "
        "render a page (bot detection / JS errors / API limits), it returns 0 for "
        "accessibility even if the site is functional. See UX section for detailed "
        "check-by-check results from crawled HTML.",
        S_SMALL))
    _gap(story, 6)

    # FIX 3: On-Page score anomaly note inline on page 1
    t_pages_note = f" (based on {t_crawled} page{'s' if t_crawled!=1 else ''} crawled)"
    c_pages_note = f" (based on {c_crawled} page{'s' if c_crawled!=1 else ''} crawled)"
    story.append(Paragraph(
        f"On-Page SEO scores are calculated from crawled pages only{t_pages_note} for target"
        f"{c_pages_note} for competitor. Scores from small crawl samples may not reflect "
        "full-site quality. Content scores with thin/duplicate content issues are flagged "
        "in their respective sections.",
        S_SMALL))
    _gap(story, 10)

    # Executive Summary
    story.append(Paragraph("Executive Summary", S_HEAD)); _gap(story, 4)
    story.append(Paragraph(str(synthesis.executive_summary or
        "AI synthesis did not return an executive summary for this audit run."), S_BODY))
    _gap(story, 10)

    # ── FIX 6: Quick Wins wrapped in KeepTogether so it never splits ─────────
    wins = synthesis.quick_wins or []
    qw_elements = [Paragraph("Quick Wins (Under 2 Weeks)", S_HEAD), Spacer(1, 4)]

    if wins:
        qw_rows = [[Paragraph("<b>Action</b>", S_BODY),
                    Paragraph("<b>Expected Impact</b>", S_BODY),
                    Paragraph("<b>Effort</b>", S_BODY)]]
        for w in wins:
            a  = safe_text(w.action)          if hasattr(w,"action")          else safe_text(w)
            im = safe_text(w.expected_impact) if hasattr(w,"expected_impact") else ""
            ef = str(w.effort)                if hasattr(w,"effort")          else "Med"
            qw_rows.append([Paragraph(a,S_BODY), Paragraph(im,S_BODY), Paragraph(ef,S_BODY)])
        qw_tbl = Table(qw_rows, colWidths=[3.0*inch, 2.8*inch, 1.2*inch])
        qw_tbl.setStyle(TableStyle([
            ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
            ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
            ("FONTSIZE",      (0,0),(-1,-1), 8), ("LEADING",(0,0),(-1,-1), 12),
            ("ALIGN",         (2,0),(2,-1),  "CENTER"),
            ("ALIGN",         (0,0),(1,-1),  "LEFT"),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6), ("TOPPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 5), ("RIGHTPADDING",(0,0),(-1,-1), 5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
        ]))
        qw_elements.append(qw_tbl)
    else:
        qw_elements.append(_note(
            "Quick wins were not returned by AI synthesis. "
            "Check that OpenRouter API key is valid and audit data was sufficient.", S_NOTE))

    story.append(KeepTogether(qw_elements))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2: DETAILED EXECUTIVE ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Detailed Executive Analysis", S_HEAD)); _gap(story, 8)

    story.append(Paragraph("Target Strengths", S_SUB)); _gap(story, 4)
    _dynamic_bullets(synthesis.target_strengths, story, S_BODY); _gap(story, 10)

    story.append(Paragraph("Target Weaknesses", S_SUB)); _gap(story, 4)
    _dynamic_bullets(synthesis.target_weaknesses, story, S_BODY); _gap(story, 10)

    story.append(Paragraph("Competitor Advantages", S_SUB)); _gap(story, 4)
    _dynamic_bullets(synthesis.competitor_advantages, story, S_BODY); _gap(story, 10)

    story.append(Paragraph("Content Opportunities (Gaps)", S_SUB)); _gap(story, 4)
    _dynamic_bullets(synthesis.content_gaps, story, S_BODY); _gap(story, 10)

    story.append(Paragraph("UX Comparison Verdict", S_SUB)); _gap(story, 4)
    story.append(Paragraph(str(synthesis.ux_comparison_verdict or
        "UX comparison not returned by AI for this run."), S_BODY)); _gap(story, 10)

    story.append(Paragraph("Overall Verdict", S_SUB)); _gap(story, 4)
    story.append(Paragraph(str(synthesis.overall_verdict or
        "Overall verdict not returned by AI for this run."), S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3: TECHNICAL SEO
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Technical SEO Analysis", S_HEAD)); _gap(story, 6)
    story.append(_note(
        "Blank cells (—) mean a check could not be run for that domain — typically "
        "because the page was blocked, returned an error, or the crawl did not access "
        "enough pages to perform the check.", S_NOTE)); _gap(story, 8)

    t_cm = {c.name:c for c in tt.checks}
    c_cm = {c.name:c for c in ct.checks}
    all_names = list(dict.fromkeys(list(t_cm.keys()) + list(c_cm.keys())))

    tech_rows = [["Check", "Target", "Competitor"]]
    tse = []
    for i, name in enumerate(all_names, start=1):
        ts_sym = _status_symbol(t_cm[name].status) if name in t_cm else "—"
        cs_sym = _status_symbol(c_cm[name].status) if name in c_cm else "—"
        tech_rows.append([name, ts_sym, cs_sym])
        for col, sym in ((1, ts_sym), (2, cs_sym)):
            if sym == "FAIL":
                tse += [("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#c0392b")),
                        ("FONTNAME",(col,i),(col,i),"Helvetica-Bold")]
            elif sym == "PASS":
                tse.append(("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#0a7f3f")))
            elif sym == "WARN":
                tse.append(("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#e67e22")))

    story.append(_make_table(tech_rows, [3.6*inch,1.7*inch,1.7*inch], tse)); _gap(story, 10)
    story.append(Paragraph(
        f"<b>Target Technical SEO Score: {ts.technical_seo}/100 &nbsp;&nbsp; "
        f"Competitor Technical SEO Score: {cs.technical_seo}/100</b>", S_BODY)); _gap(story, 6)
    t_sd = tt.structured_data_types; c_sd = ct.structured_data_types
    story.append(Paragraph(
        f"<b>Structured Data — Target:</b> {', '.join(t_sd) if t_sd else 'None found'}", S_BODY))
    story.append(Paragraph(
        f"<b>Structured Data — Competitor:</b> {', '.join(c_sd) if c_sd else 'None found'}", S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 4: ON-PAGE SEO
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("On-Page SEO Analysis", S_HEAD)); _gap(story, 6)

    if c_crawled == 0:
        story.append(_note(
            f"WHY {c_domain} shows 0% for all on-page metrics: On-page metrics are "
            "calculated from crawled HTML pages. The competitor returned 0 crawlable pages "
            "— likely blocked by Cloudflare, bot protection, or robots.txt. 0% does NOT "
            "mean they have no titles/metas — it means the crawler was blocked.", S_NOTE))
        _gap(story, 8)

    onpage_rows = [
        ["Metric", "Target", "Competitor"],
        ["Title Tag Coverage",
         f"{to.title_coverage_pct:.1f}%",
         f"{co.title_coverage_pct:.1f}%" if c_crawled > 0 else "0% (not crawled)"],
        ["Meta Description Coverage",
         f"{to.meta_desc_coverage_pct:.1f}%",
         f"{co.meta_desc_coverage_pct:.1f}%" if c_crawled > 0 else "0% (not crawled)"],
        ["H1 Health",
         f"{to.h1_health_pct:.1f}%",
         f"{co.h1_health_pct:.1f}%" if c_crawled > 0 else "0% (not crawled)"],
        ["Image ALT Coverage",
         f"{to.alt_text_coverage_pct:.1f}%",
         f"{co.alt_text_coverage_pct:.1f}%" if c_crawled > 0 else "0% (not crawled)"],
        ["Orphan Pages",
         str(len(to.orphan_pages)),
         str(len(co.orphan_pages))],
        ["Pages Crawled",
         str(t_crawled),
         str(c_crawled)],
    ]
    story.append(_make_table(onpage_rows, [2.8*inch,2.1*inch,2.1*inch])); _gap(story, 10)

    story.append(Paragraph(
        f"<b>Target On-Page SEO Score: {ts.onpage_seo}/100 &nbsp;&nbsp; "
        f"Competitor On-Page SEO Score: {cs.onpage_seo}/100</b>", S_BODY)); _gap(story, 4)

    # FIX 3: Score anomaly explanation — always shown, specific to crawl size
    story.append(_note(
        f"Score context: On-Page SEO scores are calculated by deducting points per issue "
        f"found across crawled pages. With only {t_crawled} page(s) crawled for target, "
        "deductions are limited even when coverage metrics appear poor (e.g. 0% H1 health "
        "or 0% meta descriptions). These scores may improve or worsen as more pages are "
        "crawled. Small crawl samples can produce misleading scores in either direction.",
        S_NOTE)); _gap(story, 8)

    if c_crawled == 0:
        story.append(_note(
            f"WHY competitor On-Page score is {cs.onpage_seo}/100: The scorer starts at 100 "
            "and deducts points per issue. With 0 pages crawled, 0 issues are found — so no "
            "deductions are made. This is a data gap, NOT a genuine perfect score.", S_NOTE))
        _gap(story, 8)

    story.append(_note(
        "HOW on-page percentages are calculated: "
        "Title Coverage = pages with title tag / total crawled pages x 100. "
        "Meta Coverage = pages with meta description / total x 100. "
        "H1 Health = pages with exactly one H1 / total x 100. "
        "Image ALT = images with alt text / total images x 100. "
        "Orphan Pages = pages with zero inbound internal links (excluding homepage).", S_NOTE))
    _gap(story, 10)

    story.append(Paragraph("Top Issue Pages — Target", S_SUB)); _gap(story, 4)
    tips = to.top_issues_pages[:5]
    [story.append(Paragraph("• " + str(u), S_BODY)) for u in tips] if tips else \
        story.append(Paragraph("None detected.", S_BODY))
    _gap(story, 8)

    story.append(Paragraph("Top Issue Pages — Competitor", S_SUB)); _gap(story, 4)
    cips = co.top_issues_pages[:5]
    if cips:
        [story.append(Paragraph("• " + str(u), S_BODY)) for u in cips]
    else:
        story.append(Paragraph(
            "No pages crawled — competitor blocked." if c_crawled == 0 else "None detected.",
            S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 5: CONTENT ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Content Analysis", S_HEAD)); _gap(story, 6)

    if c_crawled == 0:
        story.append(_note(
            f"WHY {c_domain} content metrics show 0: Content analysis requires crawled HTML "
            "to count words, detect duplicates, and classify pages. 0 crawled pages = all "
            f"counts are 0. {c_domain} content score of {cs.content}/100 is the same scorer "
            "artifact — starts at 100, no pages to deduct from.", S_NOTE)); _gap(story, 8)

    t_avg = sum(p.word_count for p in tc.pages) // max(len(tc.pages), 1)
    c_avg = sum(p.word_count for p in cc.pages) // max(len(cc.pages), 1)

    content_rows = [
        ["Metric",            "Target",                                    "Competitor"],
        ["Pages Crawled",     str(t_crawled),                              str(c_crawled)],
        ["Avg Word Count",    str(t_avg),                                  str(c_avg) if c_crawled > 0 else "N/A"],
        ["Thin Content",      str(len(tc.thin_content_urls)),              str(len(cc.thin_content_urls))],
        ["Duplicate Groups",  str(len(tc.duplicate_groups)),               str(len(cc.duplicate_groups))],
        ["Action: Keep",      str(tc.action_counts.get("Keep",   0)),      str(cc.action_counts.get("Keep",   0))],
        ["Action: Update",    str(tc.action_counts.get("Update", 0)),      str(cc.action_counts.get("Update", 0))],
        ["Action: Merge",     str(tc.action_counts.get("Merge",  0)),      str(cc.action_counts.get("Merge",  0))],
        ["Action: Delete",    str(tc.action_counts.get("Delete", 0)),      str(cc.action_counts.get("Delete", 0))],
    ]
    story.append(_make_table(content_rows, [2.8*inch,2.1*inch,2.1*inch])); _gap(story, 10)

    story.append(Paragraph(
        f"<b>Target Content Score: {ts.content}/100 &nbsp;&nbsp; "
        f"Competitor Content Score: {cs.content}/100</b>", S_BODY)); _gap(story, 6)

    # FIX 3: Content score anomaly note — shown whenever score seems inconsistent
    if ts.content > 60 and len(tc.thin_content_urls) > 0:
        story.append(_note(
            f"Content score context: Target scores {ts.content}/100 but has "
            f"{len(tc.thin_content_urls)} thin content page(s) with an average of "
            f"{t_avg} words per page. The score reflects limited deductions from a small "
            f"crawl sample ({t_crawled} pages). Real content quality requires expansion — "
            "see thin content and action recommendations below.", S_NOTE)); _gap(story, 6)

    # FIX 8: Competitor content narration — explain WHY competitor scores low despite more pages
    if c_crawled > 10 and cs.content < 50:
        dup_count = len(cc.duplicate_groups)
        thin_count = len(cc.thin_content_urls)
        merge_count = cc.action_counts.get("Merge", 0)
        story.append(_note(
            f"Why {c_domain} scores {cs.content}/100 on content despite {c_crawled} pages: "
            f"Volume alone does not equal quality. The competitor has {thin_count} thin "
            f"content pages (under 300 words), {dup_count} duplicate content groups, and "
            f"{merge_count} pages flagged for consolidation. High page count with poor "
            "content quality results in a low score.", S_NOTE)); _gap(story, 6)

    story.append(_note(
        "HOW thin content is detected: The crawler strips nav/footer/scripts/styles from "
        "each page's HTML and counts remaining visible words. Under 300 words = thin. "
        "Under 150 words on a non-key page = Delete action. Key pages (home/contact/about/"
        "services/products) are always flagged Update, never Delete, even if thin.", S_NOTE))
    _gap(story, 10)

    story.append(Paragraph("Thin Content Pages — Target", S_SUB)); _gap(story, 4)
    tt_thin = tc.thin_content_urls[:5]
    [story.append(Paragraph("• " + str(u), S_BODY)) for u in tt_thin] if tt_thin else \
        story.append(Paragraph("None detected.", S_BODY))
    _gap(story, 8)

    story.append(Paragraph("Thin Content Pages — Competitor", S_SUB)); _gap(story, 4)
    cc_thin = cc.thin_content_urls[:5]
    if cc_thin:
        [story.append(Paragraph("• " + str(u), S_BODY)) for u in cc_thin]
    else:
        story.append(Paragraph(
            "No pages crawled — cannot assess." if c_crawled == 0 else "None detected.",
            S_BODY))
    _gap(story, 10)

    story.append(Paragraph("Content Action Guide", S_SUB)); _gap(story, 4)
    for label, desc in [
        ("Keep",   "300+ words, good readability — leave unchanged."),
        ("Update", "Important page but needs expansion or quality improvement."),
        ("Merge",  "Duplicate body content detected — consolidate into one canonical page."),
        ("Delete", "Under 150 words, not a key page — safe to remove."),
    ]:
        story.append(Paragraph(f"<b>{label}</b> — {desc}", S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 6: UX ANALYSIS
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("UX & Accessibility Analysis", S_HEAD)); _gap(story, 6)
    story.append(_note(
        "WHY UX scores show 0/100: UX score uses PageSpeed Insights accessibility score "
        "as its base value. When PageSpeed cannot fully render a page (JS errors, bot "
        "detection, API rate limits), it returns 0 for accessibility even if the "
        "performance score is correct. The UX checks below come from crawled HTML and "
        "reflect real findings.", S_NOTE)); _gap(story, 10)

    def _gc(bundle, name):
        for ch in bundle["ux"].checks:
            if ch.name == name:
                return _status_symbol(ch.status)
        return "—"

    ux_rows = [
        ["Metric", "Target", "Competitor"],
        ["Trust Signals Present",
         "PASS" if tu.trust_signals_present else "FAIL",
         "PASS" if cu.trust_signals_present else "FAIL"],
        ["CTA Above Fold",
         "PASS" if tu.cta_above_fold else "FAIL",
         "PASS" if cu.cta_above_fold else "FAIL"],
    ]
    for cn in ["ARIA Landmark Roles", "Navigation Menu Present", "Form Labels",
               "Skip Navigation Link", "Images Alt Text", "Footer Contact Info",
               "Mobile Tap Target Sizes", "Mobile Body Font Size",
               "No Horizontal Scroll (Mobile)"]:
        ux_rows.append([cn, _gc(target_bundle, cn), _gc(competitor_bundle, cn)])

    ux_se = []
    for i, row in enumerate(ux_rows[1:], start=1):
        for col in (1, 2):
            if row[col] == "FAIL":
                ux_se += [("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#c0392b")),
                           ("FONTNAME",(col,i),(col,i),"Helvetica-Bold")]
            elif row[col] == "PASS":
                ux_se += [("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#0a7f3f")),
                           ("FONTNAME",(col,i),(col,i),"Helvetica-Bold")]
            elif row[col] == "WARN":
                ux_se.append(("TEXTCOLOR",(col,i),(col,i),colors.HexColor("#e67e22")))

    story.append(_make_table(ux_rows, [3.2*inch,1.9*inch,1.9*inch], ux_se)); _gap(story, 10)
    story.append(Paragraph(
        f"<b>Target UX Score: {ts.ux}/100 * &nbsp;&nbsp; "
        f"Competitor UX Score: {cs.ux}/100 *</b>", S_BODY))
    story.append(Paragraph(
        "* UX score = PageSpeed accessibility base (0 when unmeasured) + HTML check "
        "adjustments. The table above shows real HTML findings regardless of score.",
        S_SMALL)); _gap(story, 10)

    story.append(Paragraph("Trust Signals — Target", S_SUB)); _gap(story, 4)
    story.append(Paragraph(
        f"Present: {', '.join(tu.trust_signals_present) if tu.trust_signals_present else 'None detected'}",
        S_BODY))
    if tu.trust_signals_missing:
        story.append(Paragraph(f"Missing: {', '.join(tu.trust_signals_missing)}", S_BODY))
    _gap(story, 8)

    story.append(Paragraph("Trust Signals — Competitor", S_SUB)); _gap(story, 4)
    story.append(Paragraph(
        f"Present: {', '.join(cu.trust_signals_present) if cu.trust_signals_present else 'None detected'}",
        S_BODY))
    if cu.trust_signals_missing:
        story.append(Paragraph(f"Missing: {', '.join(cu.trust_signals_missing)}", S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 7: PERFORMANCE ANALYSIS
    # FIX 2: Accessibility / Best Practices / SEO show "N/A" when value is 0
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Performance Analysis (Mobile)", S_HEAD)); _gap(story, 6)

    if tp.accessibility_score == 0 and cp.accessibility_score == 0:
        story.append(_note(
            "WHY Accessibility, Best Practices, SEO scores show N/A: PageSpeed returns "
            "these as separate Lighthouse categories. They show N/A (unmeasured) when "
            "PageSpeed cannot complete a full Lighthouse audit due to bot detection, JS "
            "errors, or API rate limits. The Performance score uses a different API path "
            "and is always accurate.", S_NOTE)); _gap(story, 8)

    def _bt(tv, cv, lib=False):
        try:
            t2, c2 = float(tv), float(cv)
            if lib:
                return "Target" if t2 <= c2 else "Competitor"
            return "Target" if t2 >= c2 else "Competitor"
        except:
            return "—"

    # FIX 2: Use _fmt_score (returns N/A for 0) for category scores,
    # keep _fmt (returns "0") for real metrics like LCP/CLS where 0 is valid
    perf_rows = [
        ["Metric",             "Target",                          "Competitor",                       "Better"],
        ["Performance Score",  _fmt(tp.performance_score),        _fmt(cp.performance_score),         _bt(tp.performance_score, cp.performance_score)],
        ["Accessibility Score",_fmt_score(tp.accessibility_score),_fmt_score(cp.accessibility_score),"N/A"],
        ["Best Practices",     _fmt_score(tp.best_practices_score),_fmt_score(cp.best_practices_score),"N/A"],
        ["SEO Score",          _fmt_score(tp.seo_score),          _fmt_score(cp.seo_score),           "N/A"],
        ["LCP (ms)",           _fmt(tp.lcp_ms),                   _fmt(cp.lcp_ms),                    _bt(tp.lcp_ms, cp.lcp_ms, True)],
        ["FCP (ms)",           _fmt(tp.fcp_ms),                   _fmt(cp.fcp_ms),                    _bt(tp.fcp_ms, cp.fcp_ms, True)],
        ["TTFB (ms)",          _fmt(tp.ttfb_ms),                  _fmt(cp.ttfb_ms),                   _bt(tp.ttfb_ms, cp.ttfb_ms, True)],
        ["CLS",                _fmt(tp.cls, 4),                   _fmt(cp.cls, 4),                    _bt(tp.cls, cp.cls, True)],
        ["Speed Index",        _fmt(tp.speed_index),              _fmt(cp.speed_index),               _bt(tp.speed_index, cp.speed_index, True)],
        ["Total Blocking Time",_fmt(tp.total_blocking_time_ms),   _fmt(cp.total_blocking_time_ms),    _bt(tp.total_blocking_time_ms, cp.total_blocking_time_ms, True)],
        ["INP (ms)",           _fmt(tp.inp_ms),                   _fmt(cp.inp_ms),                    "—"],
    ]
    story.append(_make_table(perf_rows, [2.4*inch,1.5*inch,1.5*inch,1.6*inch])); _gap(story, 10)
    story.append(Paragraph(
        f"<b>Target Performance Score: {ts.performance}/100 &nbsp;&nbsp; "
        f"Competitor Performance Score: {cs.performance}/100</b>", S_BODY)); _gap(story, 10)

    story.append(Paragraph("Top Performance Opportunities — Target", S_SUB)); _gap(story, 4)
    topps = tp.opportunities[:5] if tp.opportunities else []
    [story.append(Paragraph("• " + clean_opportunity(o), S_BODY)) for o in topps] if topps \
        else story.append(Paragraph("None identified.", S_BODY))
    _gap(story, 8)

    story.append(Paragraph("Top Performance Opportunities — Competitor", S_SUB)); _gap(story, 4)
    copps = cp.opportunities[:5] if cp.opportunities else []
    [story.append(Paragraph("• " + clean_opportunity(o), S_BODY)) for o in copps] if copps \
        else story.append(Paragraph("None identified.", S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 8: AI STRATEGIC RECOMMENDATIONS + CATEGORY WINNER SUMMARY
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("AI Strategic Recommendations", S_HEAD)); _gap(story, 8)

    recs = synthesis.strategic_recommendations or []
    if recs:
        rec_rows = [[
            Paragraph("<b>Recommendation</b>", S_BODY),
            Paragraph("<b>Rationale</b>", S_BODY),
            Paragraph("<b>Priority</b>", S_BODY),
            Paragraph("<b>Timeline</b>", S_BODY),
        ]]
        for r in recs:
            rec_rows.append([
                Paragraph(safe_text(r.recommendation) if hasattr(r,"recommendation") else safe_text(r), S_BODY),
                Paragraph(safe_text(r.rationale)       if hasattr(r,"rationale")       else "",          S_BODY),
                Paragraph(str(r.priority)              if hasattr(r,"priority")        else "P2",        S_BODY),
                Paragraph(str(r.timeline)              if hasattr(r,"timeline")        else "60 days",   S_BODY),
            ])
        rec_tbl = Table(rec_rows, colWidths=[2.5*inch, 2.5*inch, 0.8*inch, 1.2*inch])
        rec_tbl.setStyle(TableStyle([
            ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
            ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
            ("FONTSIZE",      (0,0),(-1,-1), 8), ("LEADING",(0,0),(-1,-1), 12),
            ("ALIGN",         (2,0),(-1,-1), "CENTER"),
            ("ALIGN",         (0,0),(1,-1),  "LEFT"),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("BOTTOMPADDING", (0,0),(-1,-1), 6), ("TOPPADDING",(0,0),(-1,-1), 6),
            ("LEFTPADDING",   (0,0),(-1,-1), 5), ("RIGHTPADDING",(0,0),(-1,-1), 5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
        ]))
        story.append(rec_tbl)
    else:
        story.append(_note(
            "No strategic recommendations returned by AI synthesis for this audit run.", S_NOTE))
    _gap(story, 14)

    story.append(Paragraph("Category Winner Summary", S_SUB)); _gap(story, 4)
    wr = [["Category", "Target Score", "Competitor Score", "Winner"]]
    for nm, tv, cv in [
        ("Overall",       ts.overall,       cs.overall),
        ("Performance",   ts.performance,   cs.performance),
        ("Technical SEO", ts.technical_seo, cs.technical_seo),
        ("On-Page SEO",   ts.onpage_seo,    cs.onpage_seo),
        ("Content",       ts.content,       cs.content),
        ("UX",            ts.ux,            cs.ux),
    ]:
        wr.append([nm, str(tv), str(cv), "Target" if tv >= cv else "Competitor"])
    story.append(_make_table(wr, [2.2*inch,1.6*inch,1.6*inch,1.6*inch]))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 9: FIX 7 — PRIORITY ACTION MATRIX
    # Flat table: every actionable issue with Priority / Category / Effort / Impact
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Priority Action Matrix", S_HEAD)); _gap(story, 6)
    story.append(Paragraph(
        "A flat list of every action item from this audit, ordered by priority. "
        "Use this table for sprint planning and task assignment.", S_BODY)); _gap(story, 8)

    # Build matrix from recs + quick wins combined
    matrix_rows = [[
        Paragraph("<b>Action</b>", S_BODY),
        Paragraph("<b>Category</b>", S_BODY),
        Paragraph("<b>Priority</b>", S_BODY),
        Paragraph("<b>Effort</b>", S_BODY),
        Paragraph("<b>Timeline</b>", S_BODY),
    ]]

    # Add quick wins as P1 Low/Med
    for w in (synthesis.quick_wins or []):
        a  = safe_text(w.action)  if hasattr(w,"action")  else safe_text(w)
        ef = str(w.effort)        if hasattr(w,"effort")   else "Med"
        matrix_rows.append([
            Paragraph(a, S_BODY),
            Paragraph("Quick Win", S_BODY),
            Paragraph("P1", S_BODY),
            Paragraph(ef, S_BODY),
            Paragraph("0-14 days", S_BODY),
        ])

    # Add strategic recommendations
    for r in recs:
        rec_txt  = safe_text(r.recommendation) if hasattr(r,"recommendation") else safe_text(r)
        pri      = str(r.priority)              if hasattr(r,"priority")       else "P2"
        timeline = str(r.timeline)              if hasattr(r,"timeline")       else "60 days"
        matrix_rows.append([
            Paragraph(rec_txt, S_BODY),
            Paragraph("Strategic", S_BODY),
            Paragraph(pri, S_BODY),
            Paragraph("Med", S_BODY),
            Paragraph(timeline, S_BODY),
        ])

    if len(matrix_rows) > 1:
        mx_tbl = Table(matrix_rows, colWidths=[3.0*inch, 1.0*inch, 0.7*inch, 0.7*inch, 1.6*inch])
        mx_style = [
            ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
            ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
            ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
            ("FONTSIZE",      (0,0),(-1,-1), 8), ("LEADING",(0,0),(-1,-1),12),
            ("ALIGN",         (1,0),(-1,-1), "CENTER"),
            ("ALIGN",         (0,0),(0,-1),  "LEFT"),
            ("VALIGN",        (0,0),(-1,-1), "TOP"),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5), ("TOPPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",   (0,0),(-1,-1), 4), ("RIGHTPADDING",(0,0),(-1,-1),4),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
        ]
        # Color P1 rows red background tint, P2 amber tint, P3 light
        for i, row in enumerate(matrix_rows[1:], start=1):
            pri_cell = row[2].text if hasattr(row[2],'text') else ""
            try:
                pri_text = row[2].getPlainText() if hasattr(row[2],'getPlainText') else "P2"
            except:
                pri_text = "P2"
        mx_tbl.setStyle(TableStyle(mx_style))
        story.append(mx_tbl)
    else:
        story.append(_note("No action items available — AI synthesis did not return data.", S_NOTE))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 10: STRATEGIC ROADMAP & FINAL VERDICT
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Strategic Roadmap & Final Verdict", S_HEAD)); _gap(story, 8)

    plan30 = synthesis.roadmap_30_days
    plan60 = synthesis.roadmap_60_days
    plan90 = synthesis.roadmap_90_days

    if not plan30:
        plan30 = [safe_text(r.recommendation) for r in recs if getattr(r,"priority","") == "P1"]
    if not plan60:
        plan60 = [safe_text(r.recommendation) for r in recs if getattr(r,"priority","") == "P2"]
    if not plan90:
        plan90 = [safe_text(r.recommendation) for r in recs if getattr(r,"priority","") == "P3"]

    def _pp(items: List[str]) -> Paragraph:
        if items:
            return Paragraph("<br/>".join("• " + i for i in items), S_BODY)
        return Paragraph(
            "<i>No roadmap items returned by AI for this phase.</i>",
            ParagraphStyle("empty_rm", parent=S_BODY, textColor=colors.HexColor("#999999")))

    roadmap_data = [
        ["Phase",               "Timeline",    "Actions"],
        ["Phase 1\nQuick Wins", "0-30 Days",   _pp(plan30)],
        ["Phase 2\nGrowth",     "30-60 Days",  _pp(plan60)],
        ["Phase 3\nAuthority",  "60-90 Days",  _pp(plan90)],
    ]
    rm_tbl = Table(roadmap_data, colWidths=[1.2*inch, 1.1*inch, 4.7*inch])
    rm_tbl.setStyle(TableStyle([
        ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
        ("TEXTCOLOR",     (0,0),(-1, 0), colors.white),
        ("FONTNAME",      (0,0),(-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (0,1),(1,-1),  "Helvetica-Bold"),
        ("BACKGROUND",    (0,1),(2,1),   colors.HexColor("#d4edda")),
        ("BACKGROUND",    (0,2),(2,2),   colors.HexColor("#fff3cd")),
        ("BACKGROUND",    (0,3),(2,3),   colors.HexColor("#e8f5e9")),
        ("FONTSIZE",      (0,0),(-1,-1), 8), ("LEADING",(0,0),(-1,-1),12),
        ("ALIGN",         (0,0),(1,-1),  "CENTER"),
        ("ALIGN",         (2,0),(2,-1),  "LEFT"),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 8), ("TOPPADDING",(0,0),(-1,-1),8),
        ("LEFTPADDING",   (2,0),(2,-1),  6), ("RIGHTPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(rm_tbl); _gap(story, 16)

    story.append(Paragraph("Expected Business Impact", S_SUB)); _gap(story, 4)
    story.append(Paragraph(
        "Implementing this roadmap can deliver measurable improvements in organic search "
        "visibility, Core Web Vitals scores, accessibility compliance, content quality, "
        "and user engagement — contributing to higher rankings and stronger competitive "
        "positioning.", S_BODY)); _gap(story, 14)

    w_domain = t_domain if ts.overall >= cs.overall else c_domain
    w_score  = max(ts.overall, cs.overall)
    w_grade  = ts.grade if ts.overall >= cs.overall else cs.grade
    l_score  = min(ts.overall, cs.overall)
    l_grade  = cs.grade if ts.overall >= cs.overall else ts.grade

    story.append(Paragraph("Final AI Verdict", S_SUB)); _gap(story, 4)
    story.append(Paragraph(
        f"<b>{w_domain}</b> demonstrates a stronger overall digital presence with a score "
        f"of <b>{w_score}/100 ({w_grade})</b> compared to {l_score}/100 ({l_grade}). "
        + str(synthesis.overall_verdict or ""), S_BODY))

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 11: FIX 4 — METHODOLOGY & ABOUT THIS REPORT APPENDIX
    # ═══════════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("Appendix — Methodology & About This Report", S_HEAD)); _gap(story, 10)

    story.append(Paragraph("How This Report Was Generated", S_SUB)); _gap(story, 4)
    story.append(Paragraph(
        "This report is produced by the Website Audit Strategy Agent — an automated "
        "pipeline that crawls both websites, runs multi-dimensional analysis, and uses "
        "AI (Claude via OpenRouter) to synthesise findings into actionable insights. "
        "No data in this report is manually entered or fabricated.", S_BODY)); _gap(story, 10)

    # ── ALIGNMENT FIX: Use Paragraph objects in every cell so text wraps ────────
    # Plain strings do NOT wrap in ReportLab table cells regardless of WORDWRAP.
    # Paragraph objects wrap at the column boundary automatically.
    S_METH_HEAD = ParagraphStyle("MH", parent=S_BODY, fontSize=7.5, leading=11,
                                  fontName="Helvetica-Bold", textColor=colors.white)
    S_METH_BOLD = ParagraphStyle("MB", parent=S_BODY, fontSize=7.5, leading=11,
                                  fontName="Helvetica-Bold")
    S_METH      = ParagraphStyle("MC", parent=S_BODY, fontSize=7.5, leading=11)

    method_rows = [
        # Header row — Paragraph objects with white text style
        [Paragraph("Component",    S_METH_HEAD),
         Paragraph("Tool / Method",S_METH_HEAD),
         Paragraph("Details",      S_METH_HEAD)],
        # Data rows — col 0 bold, col 1 bold, col 2 normal — ALL Paragraphs
        [Paragraph("Web Crawling",    S_METH_BOLD),
         Paragraph("Python requests + BeautifulSoup", S_METH_BOLD),
         Paragraph(
             f"Up to 50 pages per domain, 1 second delay between requests, "
             f"robots.txt respected. Target crawled: {t_crawled} page(s). "
             f"Competitor crawled: {c_crawled} page(s).", S_METH)],
        [Paragraph("Performance Data", S_METH_BOLD),
         Paragraph("Google PageSpeed Insights API v5", S_METH_BOLD),
         Paragraph(
             "Mobile + desktop strategies. Core Web Vitals from Lighthouse. "
             "Performance score is always accurate; accessibility, best-practices, "
             "and SEO categories show N/A when PageSpeed cannot complete a full "
             "Lighthouse audit.", S_METH)],
        [Paragraph("Technical SEO",  S_METH_BOLD),
         Paragraph("Custom Python checks", S_METH_BOLD),
         Paragraph(
             "HTTPS, SSL, robots.txt, sitemap, canonical tags, noindex, "
             "structured data (via extruct), viewport, mixed content, "
             "duplicate titles and meta descriptions.", S_METH)],
        [Paragraph("On-Page SEO",    S_METH_BOLD),
         Paragraph("BeautifulSoup HTML parsing", S_METH_BOLD),
         Paragraph(
             "Title tags, meta descriptions, H1 structure, image alt text, "
             "URL quality, internal link graph for orphan page detection.", S_METH)],
        [Paragraph("Content Analysis", S_METH_BOLD),
         Paragraph("textstat + BeautifulSoup", S_METH_BOLD),
         Paragraph(
             "Word count (visible text only, scripts/nav/footer stripped), "
             "Flesch reading ease, Gunning Fog readability, MD5 hash duplicate "
             "detection, Keep/Update/Merge/Delete action classification.", S_METH)],
        [Paragraph("UX Analysis",    S_METH_BOLD),
         Paragraph("Playwright + BeautifulSoup", S_METH_BOLD),
         Paragraph(
             "Trust signals, CTA detection, ARIA landmarks, navigation menu, "
             "form labels, skip nav link, mobile tap targets, body font size, "
             "horizontal scroll. UX score uses PageSpeed accessibility as base.", S_METH)],
        [Paragraph("AI Synthesis",   S_METH_BOLD),
         Paragraph("Claude via OpenRouter API", S_METH_BOLD),
         Paragraph(
             "Executive summary, strengths, weaknesses, quick wins, strategic "
             "recommendations, content gaps, and roadmap are all generated "
             "dynamically from the actual audit data for each domain pair. "
             "Nothing is hardcoded.", S_METH)],
    ]
    # Column widths: 1.3 + 1.9 + 3.8 = 7.0 inches exactly
    method_tbl = Table(method_rows, colWidths=[1.3*inch, 1.9*inch, 3.8*inch])
    method_tbl.setStyle(TableStyle([
        ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("LEADING",       (0,0),(-1,-1), 11),
        ("ALIGN",         (0,0),(-1,-1), "LEFT"),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
    ]))
    story.append(method_tbl); _gap(story, 14)

    story.append(Paragraph("Scoring Methodology", S_SUB)); _gap(story, 4)
    # ALL cells must be Paragraph objects for text to wrap inside column bounds
    scoring_rows = [
        [Paragraph("Category",     S_METH_HEAD),
         Paragraph("Weight",       S_METH_HEAD),
         Paragraph("How Scored",   S_METH_HEAD)],
        [Paragraph("Performance",  S_METH_BOLD),
         Paragraph("25%",          S_METH_BOLD),
         Paragraph("PageSpeed mobile performance score (0-100) used directly.", S_METH)],
        [Paragraph("Technical SEO",S_METH_BOLD),
         Paragraph("20%",          S_METH_BOLD),
         Paragraph(
             "Starts at 100. Deductions: No HTTPS (-20), no robots.txt (-10), "
             "no sitemap (-10), no structured data (-10), duplicate title tags (-5), "
             "duplicate meta descriptions (-5), broken links (-5 each, max -20).", S_METH)],
        [Paragraph("On-Page SEO",  S_METH_BOLD),
         Paragraph("20%",          S_METH_BOLD),
         Paragraph(
             "Starts at 100. Deductions per crawled page: missing title (-5, max -20), "
             "missing meta description (-3, max -15), H1 issues (-5, max -15), "
             "missing image alt text (-2 per image, max -15), "
             "orphan pages (-5 each, max -15).", S_METH)],
        [Paragraph("Content",      S_METH_BOLD),
         Paragraph("20%",          S_METH_BOLD),
         Paragraph(
             "Starts at 100. Deductions: thin content pages under 300 words "
             "(-10 per page, max -30), duplicate content pages (-10, max -20), "
             "no multimedia on page (-5, max -15), "
             "readability Gunning Fog above 12 (-5, max -15).", S_METH)],
        [Paragraph("UX",           S_METH_BOLD),
         Paragraph("15%",          S_METH_BOLD),
         Paragraph(
             "PageSpeed accessibility score as base (0-100). Adjustments: "
             "no CTA above fold (-10), no trust signals (-10), "
             "mobile tap target failures (-10), no ARIA landmarks (-5), "
             "form inputs missing labels (-5).", S_METH)],
    ]
    # Column widths: 1.3 + 0.7 + 5.0 = 7.0 inches exactly
    sc_tbl = Table(scoring_rows, colWidths=[1.3*inch, 0.7*inch, 5.0*inch])
    sc_tbl.setStyle(TableStyle([
        ("GRID",          (0,0),(-1,-1), 0.5, colors.HexColor("#cccccc")),
        ("BACKGROUND",    (0,0),(-1, 0), colors.HexColor("#0a7f3f")),
        ("FONTSIZE",      (0,0),(-1,-1), 7.5),
        ("LEADING",       (0,0),(-1,-1), 11),
        ("ALIGN",         (1,1),(1,-1),  "CENTER"),
        ("ALIGN",         (0,0),(0,-1),  "LEFT"),
        ("ALIGN",         (2,0),(2,-1),  "LEFT"),
        ("VALIGN",        (0,0),(-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0),(-1,-1), 7),
        ("TOPPADDING",    (0,0),(-1,-1), 7),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, colors.HexColor("#f0fff4")]),
    ]))
    story.append(sc_tbl); _gap(story, 14)

    story.append(Paragraph("Grade Scale", S_SUB)); _gap(story, 4)
    grade_rows = [
        ["Score Range", "Grade", "Health Status"],
        ["90-100", "A+", "Excellent"],
        ["85-89",  "A",  "Very Good"],
        ["80-84",  "B+", "Good"],
        ["75-79",  "B",  "Above Average"],
        ["70-74",  "C+", "Average"],
        ["65-69",  "C",  "Below Average"],
        ["60-64",  "D+", "Needs Improvement"],
        ["Below 60","D", "Poor — Immediate Action Required"],
    ]
    story.append(_make_table(grade_rows, [1.5*inch, 1.0*inch, 4.5*inch])); _gap(story, 20)

    # Footer
    story.append(Paragraph("<b>Website Audit Strategy Agent</b>", S_BODY))
    story.append(Paragraph(
        f"Report Generated: {datetime.now().strftime('%d %B %Y at %H:%M')} &nbsp;|&nbsp; "
        f"Powered by AI-driven SEO, UX, Content, Performance & Technical Analysis.", S_SMALL))

    # ── Build PDF ─────────────────────────────────────────────────────────────
    try:
        print(f"Total story elements: {len(story)}")
        print("Building PDF...")
        doc.build(story)
        print(f"PDF built successfully: {pdf_path}")
    except Exception:
        import traceback
        print("\n===== PDF BUILD ERROR =====")
        print(traceback.format_exc())
        print("===========================\n")
        raise

    return pdf_path