"""
tools/pdf_generator.py
ReportLab PDF report generator — fixed table alignment, proper column widths,
compact spacing, comprehensive content sections.
"""
import os
from datetime import datetime
from typing import Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from models import AgentOutput, StructurePlan


# ── Brand palette ─────────────────────────────────────────────────────────────
PURPLE_DARK  = colors.HexColor("#2E1A5C")
PURPLE_MID   = colors.HexColor("#4A2080")
PURPLE_LIGHT = colors.HexColor("#7B4FB5")
PURPLE_PALE  = colors.HexColor("#F5F3FB")
TEAL         = colors.HexColor("#0F6E56")
TEAL_LIGHT   = colors.HexColor("#E1F5EE")
AMBER_LIGHT  = colors.HexColor("#FAEEDA")
GRAY_DARK    = colors.HexColor("#333333")
GRAY_MID     = colors.HexColor("#666666")
GRAY_LIGHT   = colors.HexColor("#EEEEEE")
WHITE        = colors.white

# Page width available (A4 = 210mm, margins 15mm each side)
PW = 180 * mm


# ── Styles ────────────────────────────────────────────────────────────────────
def _styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Heading1"],
               fontSize=14, textColor=PURPLE_DARK, fontName="Helvetica-Bold",
               spaceBefore=10, spaceAfter=4, leading=18),
        "h2": ParagraphStyle("h2", parent=base["Heading2"],
               fontSize=11, textColor=PURPLE_MID, fontName="Helvetica-Bold",
               spaceBefore=8, spaceAfter=3, leading=14),
        "body": ParagraphStyle("body", parent=base["Normal"],
                fontSize=9, textColor=GRAY_DARK, fontName="Helvetica",
                spaceAfter=3, leading=13),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
                  fontSize=9, textColor=GRAY_DARK, fontName="Helvetica",
                  spaceAfter=2, leftIndent=10, leading=13),
        "th": ParagraphStyle("th", parent=base["Normal"],
              fontSize=8, textColor=WHITE, fontName="Helvetica-Bold", leading=11),
        "td": ParagraphStyle("td", parent=base["Normal"],
              fontSize=8, textColor=GRAY_DARK, fontName="Helvetica", leading=11),
        "td_bold": ParagraphStyle("td_bold", parent=base["Normal"],
                   fontSize=8, textColor=PURPLE_DARK, fontName="Helvetica-Bold", leading=11),
        "cover_title": ParagraphStyle("cover_title", parent=base["Normal"],
                       fontSize=18, textColor=WHITE, fontName="Helvetica-Bold", leading=22),
        "cover_sub": ParagraphStyle("cover_sub", parent=base["Normal"],
                     fontSize=10, textColor=GRAY_DARK, fontName="Helvetica", leading=14),
    }


# ── Header / Footer ───────────────────────────────────────────────────────────
class _HF:
    def __init__(self, target_url, mode):
        self.target_url = target_url[:60] + ("…" if len(target_url) > 60 else "")
        self.mode       = mode
        self.date       = datetime.now().strftime("%d %B %Y")

    def __call__(self, canvas, doc):
        canvas.saveState()
        w, h = A4
        # Header bar
        canvas.setFillColor(PURPLE_DARK)
        canvas.rect(0, h - 26, w, 26, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(15, h - 17, "Website Structure Planning Agent")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(w - 15, h - 17, self.target_url)
        # Footer bar
        canvas.setFillColor(PURPLE_DARK)
        canvas.rect(0, 0, w, 20, fill=1, stroke=0)
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(15, 6, f"Generated: {self.date}  |  Claude Haiku via OpenRouter + Tavily")
        canvas.drawCentredString(w / 2, 6, f"Mode: {self.mode}")
        canvas.drawRightString(w - 15, 6, f"Page {doc.page}")
        canvas.restoreState()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _section_header(els, st, title):
    els.append(Paragraph(title, st["h1"]))
    els.append(HRFlowable(width="100%", thickness=0.8, color=PURPLE_LIGHT, spaceAfter=6))


def _table_header_row(cols, st):
    return [Paragraph(c, st["th"]) for c in cols]


def _make_table(rows, col_widths, header_rows=1):
    tbl = Table(rows, colWidths=col_widths, repeatRows=header_rows)
    style = [
        ("BACKGROUND",    (0, 0), (-1, header_rows - 1), PURPLE_DARK),
        ("ROWBACKGROUNDS", (0, header_rows), (-1, -1), [WHITE, PURPLE_PALE]),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("LINEBELOW",     (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
    ]
    tbl.setStyle(TableStyle(style))
    return tbl


# ── Cover page ────────────────────────────────────────────────────────────────
def _cover(els, st, output: AgentOutput):
    mode_label = (
        "Existing Website Audit & Recommendations"
        if output.mode == "audit_existing"
        else "New Website Structure Plan"
    )
    els.append(Spacer(1, 50))
    # Title banner
    tbl = Table([[Paragraph("Website Structure\nPlanning Agent", st["cover_title"])]],
                colWidths=[PW])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 24),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 24),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 20),
    ]))
    els.append(tbl)
    els.append(Spacer(1, 14))

    meta = [
        ["Report Type",   mode_label],
        ["Target URL",    output.target_url],
        ["Business Type", output.business_type],
        ["Business Goal", output.business_goal],
        ["AI Model",      "Claude Haiku via OpenRouter"],
        ["Scraping Tool", "Tavily Search API + BeautifulSoup"],
        ["Generated",     datetime.now().strftime("%d %B %Y, %H:%M")],
    ]
    mt = Table(meta, colWidths=[50 * mm, PW - 50 * mm])
    mt.setStyle(TableStyle([
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTNAME",      (0, 0), (0, -1),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",     (0, 0), (0, -1),  PURPLE_DARK),
        ("TEXTCOLOR",     (1, 0), (1, -1),  GRAY_DARK),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.3, GRAY_LIGHT),
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
    ]))
    els.append(mt)
    els.append(PageBreak())


# ── Site scraping section (competitor OR target) ──────────────────────────────
def _scrape_section(els, st, output: AgentOutput):
    is_audit = output.mode == "audit_existing"
    section_title = "1. Competitor Scraping & Benchmarking" if is_audit else "1. Target Site Scraping & Discovery"
    _section_header(els, st, section_title)

    sites_to_show = []
    if is_audit:
        sites_to_show = [(f"Competitor {i}", s) for i, s in enumerate(output.scraped_competitors, 1)]
        # Also add target at the end
        if output.scraped_target:
            sites_to_show.append(("Target Site", output.scraped_target))
    else:
        if output.scraped_target:
            sites_to_show = [("Target Site (Current State)", output.scraped_target)]

    for label, site in sites_to_show:
        block_items = []
        # Site header row
        hdr = Table([[Paragraph(f"{label}: {site.url}", st["th"])]], colWidths=[PW])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_MID),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        block_items.append(hdr)

        # Detail table
        rows = [
            [Paragraph("Navigation Items", st["td_bold"]),
             Paragraph(", ".join(site.nav_labels[:12]) if site.nav_labels else "Not found", st["td"])],
            [Paragraph("Estimated Pages", st["td_bold"]),
             Paragraph(str(site.page_count) if site.page_count else "Unknown", st["td"])],
            [Paragraph("Content Depth", st["td_bold"]),
             Paragraph(f"{site.content_depth} levels" if site.content_depth else "Unknown", st["td"])],
            [Paragraph("URL Patterns", st["td_bold"]),
             Paragraph(", ".join(site.url_patterns[:8]) if site.url_patterns else "Not found", st["td"])],
        ]
        # Add discovered endpoints if available
        if site.url_endpoints:
            rows.append([
                Paragraph("Discovered Endpoints", st["td_bold"]),
                Paragraph(", ".join(site.url_endpoints[:20]), st["td"]),
            ])
        # Add structural notes
        if site.structural_notes:
            for note in site.structural_notes[:5]:
                rows.append([
                    Paragraph("Structure Note", st["td_bold"]),
                    Paragraph(note, st["td"]),
                ])
        if site.error:
            rows.append([
                Paragraph("Scrape Status", st["td_bold"]),
                Paragraph(f"Partial — {site.error}", st["td"]),
            ])

        dt = Table(rows, colWidths=[42 * mm, PW - 42 * mm])
        dt.setStyle(TableStyle([
            ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_PALE),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        block_items.append(dt)
        block_items.append(Spacer(1, 6))
        els.append(KeepTogether(block_items))

    # Comparison table for audit mode
    if is_audit and output.scraped_competitors and output.scraped_target:
        els.append(Spacer(1, 4))
        els.append(Paragraph("Site Comparison", st["h2"]))
        comp_rows = [_table_header_row(["Metric", "Your Site"] + [f"Competitor {i}" for i in range(1, len(output.scraped_competitors) + 1)], st)]
        all_sites = [output.scraped_target] + output.scraped_competitors
        col_w = [38 * mm] + [(PW - 38 * mm) / len(all_sites)] * len(all_sites)

        metrics = [
            ("Est. Pages",   lambda s: str(s.page_count) if s.page_count else "?"),
            ("Nav Depth",    lambda s: f"{s.content_depth} levels" if s.content_depth else "?"),
            ("Nav Items",    lambda s: str(len(s.nav_labels))),
            ("URL Endpoints",lambda s: str(len(s.url_endpoints))),
        ]
        for metric_name, fn in metrics:
            row = [Paragraph(metric_name, st["td_bold"])]
            for s in all_sites:
                row.append(Paragraph(fn(s), st["td"]))
            comp_rows.append(row)

        comp_tbl = _make_table(comp_rows, col_w)
        els.append(comp_tbl)
    els.append(Spacer(1, 8))


# ── Audit findings section ────────────────────────────────────────────────────
def _audit_section(els, st, output: AgentOutput, sec_num: int):
    _section_header(els, st, f"{sec_num}. Audit Findings")
    af = output.audit_findings
    if not af:
        els.append(Paragraph("No audit findings provided.", st["body"]))
        return

    categories = [
        ("Crawl Errors",      af.crawl_errors,        colors.HexColor("#FCEBEB"), colors.HexColor("#C0392B")),
        ("Orphan Pages",      af.orphan_pages,        AMBER_LIGHT,                colors.HexColor("#E67E22")),
        ("Redirect Chains",   af.redirect_chains,     AMBER_LIGHT,                colors.HexColor("#E67E22")),
        ("Thin Content",      af.thin_content_pages,  GRAY_LIGHT,                 GRAY_MID),
        ("Missing Pages",     af.missing_pages,       TEAL_LIGHT,                 TEAL),
        ("Structural Issues", af.structural_issues,   PURPLE_PALE,                PURPLE_MID),
    ]

    for cat_name, items, bg, accent in categories:
        if not items:
            continue
        rows = [[Paragraph(f"• {item}", st["td"])] for item in items]
        hdr  = Table([[Paragraph(cat_name, st["th"])]], colWidths=[PW])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), accent),
            ("TOPPADDING",    (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ]))
        body = Table(rows, colWidths=[PW])
        body.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("LINEBELOW",     (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]))
        els.append(KeepTogether([hdr, body, Spacer(1, 5)]))


# ── Page hierarchy section ────────────────────────────────────────────────────
def _hierarchy_section(els, st, plan: StructurePlan, sec_num: int):
    _section_header(els, st, f"{sec_num}. Page Hierarchy & IA Design")

    # Column widths that sum to PW
    col_w = [52*mm, 10*mm, 44*mm, 24*mm, 16*mm, 34*mm]
    header = _table_header_row(["Page Name", "Tier", "URL Slug", "Type", "Priority", "CTA"], st)
    rows   = [header]

    for p in plan.pages:
        indent = ("    " * (p.tier - 1)) + ("→ " if p.tier > 1 else "")
        cta    = p.cta_type or "—"
        # Truncate long CTAs for table fit
        if len(cta) > 35:
            cta = cta[:33] + "…"
        rows.append([
            Paragraph(f"{indent}{p.page_name}", st["td"]),
            Paragraph(str(p.tier),              st["td"]),
            Paragraph(p.url_slug,               st["td"]),
            Paragraph(p.page_type,              st["td"]),
            Paragraph(p.priority,               st["td"]),
            Paragraph(cta,                      st["td"]),
        ])

    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  PURPLE_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PURPLE_PALE]),
        ("FONTSIZE",       (0, 0), (-1, -1), 8),
        ("TOPPADDING",     (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
        ("LEFTPADDING",    (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 4),
        ("LINEBELOW",      (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
        ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ("GRID",           (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
        # Highlight high-priority rows
    ]))
    els.append(tbl)
    els.append(Spacer(1, 8))


# ── Navigation section ────────────────────────────────────────────────────────
def _nav_section(els, st, plan: StructurePlan, sec_num: int):
    _section_header(els, st, f"{sec_num}. URL Structure & Navigation Flow")
    nav = plan.navigation

    rows = [
        [Paragraph("Primary Navigation",   st["td_bold"]),
         Paragraph(" | ".join(nav.primary_nav)   if nav.primary_nav   else "—", st["td"])],
        [Paragraph("Secondary Navigation", st["td_bold"]),
         Paragraph(" | ".join(nav.secondary_nav) if nav.secondary_nav else "—", st["td"])],
        [Paragraph("Breadcrumb Example",   st["td_bold"]),
         Paragraph(" > ".join(nav.breadcrumb_example) if nav.breadcrumb_example else "—", st["td"])],
    ]
    tbl = Table(rows, colWidths=[44 * mm, PW - 44 * mm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), PURPLE_PALE),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        ("LINEBELOW",     (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
    ]))
    els.append(tbl)
    els.append(Spacer(1, 8))

    if nav.internal_linking_rules:
        els.append(Paragraph("Internal Linking Rules", st["h2"]))
        link_rows = [[Paragraph(f"• {r}", st["td"])] for r in nav.internal_linking_rules]
        lt = Table(link_rows, colWidths=[PW])
        lt.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PURPLE_PALE]),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("TOPPADDING",     (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 3),
            ("LEFTPADDING",    (0, 0), (-1, -1), 10),
            ("LINEBELOW",      (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
        ]))
        els.append(lt)
    els.append(Spacer(1, 8))


# ── Conversion paths section ──────────────────────────────────────────────────
def _conversion_section(els, st, plan: StructurePlan, sec_num: int):
    _section_header(els, st, f"{sec_num}. Conversion Path & CTA Mapping")

    for cp in plan.conversion_paths:
        block = []
        block.append(Paragraph(f"Goal: {cp.goal}", st["h2"]))

        if cp.funnel_steps:
            funnel_text = "  →  ".join(cp.funnel_steps)
            block.append(Paragraph(funnel_text, st["body"]))

        if cp.cta_per_tier:
            hrow  = _table_header_row(["Page Tier", "CTA Recommendation"], st)
            rows  = [hrow] + [
                [Paragraph(k, st["td_bold"]), Paragraph(v, st["td"])]
                for k, v in cp.cta_per_tier.items()
            ]
            tbl = Table(rows, colWidths=[60 * mm, PW - 60 * mm])
            tbl.setStyle(TableStyle([
                ("BACKGROUND",     (0, 0), (-1, 0),  PURPLE_MID),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [TEAL_LIGHT, WHITE]),
                ("FONTSIZE",       (0, 0), (-1, -1), 8),
                ("TOPPADDING",     (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",  (0, 0), (-1, -1), 4),
                ("LEFTPADDING",    (0, 0), (-1, -1), 7),
                ("RIGHTPADDING",   (0, 0), (-1, -1), 7),
                ("LINEBELOW",      (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
                ("VALIGN",         (0, 0), (-1, -1), "TOP"),
                ("GRID",           (0, 0), (-1, -1), 0.25, GRAY_LIGHT),
            ]))
            block.append(tbl)

        if cp.key_landing_pages:
            block.append(Paragraph(
                f"Key landing pages: {', '.join(cp.key_landing_pages)}", st["body"]))
        block.append(Spacer(1, 6))
        els.append(KeepTogether(block))


# ── Recommendations + strategy ────────────────────────────────────────────────
def _recommendations_section(els, st, plan: StructurePlan, sec_num: int, mode: str):
    rec_title   = ("Recommendations — How to Fix Structural Issues"
                   if mode == "audit_existing"
                   else "Recommendations — How to Build It Correctly")
    strat_title = ("Implementation Strategy — Correcting Your Site"
                   if mode == "audit_existing"
                   else "Implementation Strategy — Phased Build Plan")

    _section_header(els, st, f"{sec_num}. {rec_title}")

    rec_rows = []
    for i, r in enumerate(plan.recommendations, 1):
        rec_rows.append([
            Paragraph(str(i), st["td_bold"]),
            Paragraph(r, st["td"]),
        ])

    if rec_rows:
        rt = Table(rec_rows, colWidths=[10 * mm, PW - 10 * mm])
        rt.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [PURPLE_PALE, WHITE]),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("TOPPADDING",     (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
            ("LEFTPADDING",    (0, 0), (0, -1),  6),
            ("LEFTPADDING",    (1, 0), (1, -1),  8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
            ("LINEBELOW",      (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ]))
        els.append(rt)

    els.append(Spacer(1, 10))
    _section_header(els, st, f"{sec_num + 1}. {strat_title}")

    strat_rows = []
    for step in plan.implementation_strategy:
        strat_rows.append([Paragraph(f"✔  {step}", st["td"])])

    if strat_rows:
        st_tbl = Table(strat_rows, colWidths=[PW])
        st_tbl.setStyle(TableStyle([
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [TEAL_LIGHT, WHITE]),
            ("FONTSIZE",       (0, 0), (-1, -1), 8),
            ("TOPPADDING",     (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 5),
            ("LEFTPADDING",    (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 6),
            ("LINEBELOW",      (0, 0), (-1, -2), 0.25, GRAY_LIGHT),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
        ]))
        els.append(st_tbl)


# ── Master builder ─────────────────────────────────────────────────────────────
def generate_pdf(output: AgentOutput, output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    ts          = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_domain = (output.target_url
                   .replace("https://", "").replace("http://", "")
                   .replace("/", "_").replace(".", "_")[:35])
    path = os.path.join(output_dir, f"structure_plan_{safe_domain}_{ts}.pdf")

    doc = SimpleDocTemplate(
        path, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=32*mm,  bottomMargin=26*mm,
    )
    st  = _styles()
    els = []
    hf  = _HF(output.target_url, output.mode)

    # Cover
    _cover(els, st, output)

    # Scraping section (competitors for audit, target for new_structure)
    if output.scraped_competitors or output.scraped_target:
        _scrape_section(els, st, output)
        els.append(Spacer(1, 6))

    if not output.structure_plan:
        doc.build(els, onFirstPage=hf, onLaterPages=hf)
        return path

    plan = output.structure_plan
    sec  = 2

    # Audit findings — only show if user actually provided audit notes
    af = output.audit_findings
    has_findings = af and any([
        af.crawl_errors, af.orphan_pages, af.redirect_chains,
        af.thin_content_pages, af.missing_pages, af.structural_issues
    ])
    if output.mode == "audit_existing" and has_findings:
        els.append(PageBreak())
        _audit_section(els, st, output, sec)
        sec += 1

    # Page hierarchy
    if plan.pages:
        els.append(PageBreak())
        _hierarchy_section(els, st, plan, sec)
        sec += 1

    # Navigation flow
    els.append(PageBreak())
    _nav_section(els, st, plan, sec)
    sec += 1

    # Conversion paths
    _conversion_section(els, st, plan, sec)
    sec += 1

    # Recommendations + strategy
    els.append(PageBreak())
    _recommendations_section(els, st, plan, sec, output.mode)

    doc.build(els, onFirstPage=hf, onLaterPages=hf)
    return path
