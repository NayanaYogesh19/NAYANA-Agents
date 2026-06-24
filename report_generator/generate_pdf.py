"""
PDF Report Generator — InGovern style
Uses ReportLab (pure Python, no GTK needed on Windows).
"""

import os
from datetime import date
from io import BytesIO

REPORTS_DIR = "storage/reports"

# ── Brand colours ──────────────────────────────────────────────────────────────
DARK_BLUE  = (0.059, 0.204, 0.376)   # #0f3460
RED_ACCENT = (0.914, 0.271, 0.376)   # #e94560
LIGHT_GREY = (0.93, 0.93, 0.93)
MID_GREY   = (0.55, 0.55, 0.55)
WHITE      = (1, 1, 1)
BLACK      = (0, 0, 0)
FOR_GREEN  = (0.063, 0.506, 0.278)
AGAINST_RED= (0.784, 0.098, 0.098)
ABSTAIN_ORANGE = (0.8, 0.4, 0.0)


def _sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def _rec_color(rec: str):
    r = str(rec).strip().upper()
    if r.startswith("FOR"):
        return FOR_GREEN
    if r.startswith("AGAINST"):
        return AGAINST_RED
    if r.startswith("ABSTAIN"):
        return ABSTAIN_ORANGE
    return DARK_BLUE


def _para_text(text: str) -> str:
    """Escape XML special chars for ReportLab Paragraph."""
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf_report(session: dict) -> dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)

    company_name   = session.get("company_name", "Company")
    financial_year = session.get("financial_year", "FY")
    notice_meta    = session.get("notice_metadata", {})
    notice_type    = notice_meta.get("notice_type", "AGM")
    isin           = notice_meta.get("isin", "")
    meeting_date   = notice_meta.get("meeting_date", "")
    meeting_venue  = notice_meta.get("meeting_venue", "")
    evoting        = notice_meta.get("evoting_platform", "")
    resolutions    = session.get("resolutions", [])
    approved_by    = session.get("approved_by", "")
    report_date    = date.today().strftime("%d %B %Y")

    safe_company = _sanitize_filename(company_name)
    safe_fy      = _sanitize_filename(financial_year)
    filename     = f"{safe_company}_{safe_fy}_InGovern_Report.pdf"
    filepath     = os.path.join(REPORTS_DIR, filename)

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm, cm
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak, KeepTogether,
        )

        W, H = A4
        L, R, T, B = 20*mm, 20*mm, 20*mm, 20*mm

        buf = BytesIO()
        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            leftMargin=L, rightMargin=R, topMargin=T, bottomMargin=B,
            title=f"{company_name} – InGovern Vote Recommendations",
            author="InGovern Research",
        )

        # ── Styles ──────────────────────────────────────────────────────────
        base = getSampleStyleSheet()

        def S(name, **kw):
            return ParagraphStyle(name, parent=base["Normal"], **kw)

        style_brand = S("brand",
            fontSize=20, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f3460"),
            spaceAfter=2,
        )
        style_subtitle = S("subtitle",
            fontSize=11, fontName="Helvetica",
            textColor=colors.HexColor("#e94560"),
            spaceAfter=6,
        )
        style_meta_label = S("metaLabel",
            fontSize=9, fontName="Helvetica",
            textColor=colors.HexColor("#555555"),
        )
        style_meta_value = S("metaValue",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#1a1a2e"),
        )
        style_section = S("section",
            fontSize=10, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f3460"),
            spaceBefore=14, spaceAfter=6,
            borderPadding=(0, 0, 0, 8),
        )
        style_body = S("body",
            fontSize=9.5, fontName="Helvetica",
            textColor=colors.HexColor("#1a1a2e"),
            leading=14, spaceAfter=6,
            alignment=TA_JUSTIFY,
        )
        style_bullet = S("bullet",
            fontSize=9.5, fontName="Helvetica",
            textColor=colors.HexColor("#1a1a2e"),
            leading=14, spaceAfter=4,
            leftIndent=12, bulletIndent=0,
        )
        style_footer = S("footer",
            fontSize=8, fontName="Helvetica",
            textColor=colors.HexColor("#888888"),
            alignment=TA_CENTER,
        )
        style_res_title = S("resTitle",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f3460"),
            spaceBefore=18, spaceAfter=4,
        )
        style_rec_label = S("recLabel",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#555555"),
            spaceAfter=2,
        )

        story = []

        # ── PAGE 1 : Cover ───────────────────────────────────────────────────
        story.append(Spacer(1, 10*mm))

        # Brand header
        story.append(Paragraph("InGovern", style_brand))
        story.append(Paragraph(
            "Corporate Governance Advisory Services",
            style_subtitle,
        ))
        story.append(HRFlowable(width="100%", thickness=2,
                                color=colors.HexColor("#0f3460"), spaceAfter=10))

        # Company name + notice type title block
        company_style = S("companyTitle",
            fontSize=16, fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f3460"),
            spaceBefore=20, spaceAfter=4, alignment=TA_CENTER,
        )
        story.append(Paragraph(_para_text(company_name.upper()), company_style))
        story.append(Paragraph(
            f"VOTE RECOMMENDATIONS FOR {financial_year} {notice_type.upper()}",
            S("noticeType", fontSize=12, fontName="Helvetica-Bold",
              textColor=colors.HexColor("#e94560"), alignment=TA_CENTER, spaceAfter=20),
        ))

        # Metadata table
        meta_rows = []
        if isin:
            meta_rows.append(["ISIN:", isin])
        if meeting_date:
            meta_rows.append(["Meeting date & time:", meeting_date])
        if meeting_venue:
            meta_rows.append(["Meeting venue:", meeting_venue])
        if evoting:
            meta_rows.append(["E-voting details:", evoting])
        if report_date:
            meta_rows.append(["Report date:", report_date])
        if approved_by:
            meta_rows.append(["Prepared by:", approved_by])

        if meta_rows:
            mt = Table(meta_rows, colWidths=[50*mm, None])
            mt.setStyle(TableStyle([
                ("FONTNAME",    (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME",    (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE",    (0, 0), (-1, -1), 9),
                ("TEXTCOLOR",   (0, 0), (0, -1), colors.HexColor("#555555")),
                ("TEXTCOLOR",   (1, 0), (1, -1), colors.HexColor("#1a1a2e")),
                ("VALIGN",      (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1),
                 [colors.HexColor("#f5f5f5"), colors.white]),
                ("TOPPADDING",  (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(mt)
            story.append(Spacer(1, 10*mm))

        # ── Summary table ────────────────────────────────────────────────────
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#dddddd"), spaceAfter=8))
        story.append(Paragraph("Proposals — InGovern Recommendations", style_section))

        tbl_header = ["Res", "Resolution Title", "Type", "InGovern"]
        tbl_data = [tbl_header]
        for r in resolutions:
            comm     = r.get("ingovern_commentary", {}) or {}
            ig_rec   = comm.get("ingovern_recommendation", "FOR")
            res_type = "Special" if r.get("special_resolution") else "Ordinary"
            title    = r.get("resolution_title") or r.get("title") or r.get("resolution_type", "")
            tbl_data.append([
                str(r.get("resolution_number", "")),
                _para_text(title),
                res_type,
                ig_rec,
            ])

        col_widths = [12*mm, None, 22*mm, 22*mm]
        tbl = Table(tbl_data, colWidths=col_widths, repeatRows=1)

        tbl_style = [
            # Header
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#0f3460")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8.5),
            ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
            # Body
            ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, -1), 8.5),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (0, 1), (0, -1), "CENTER"),
            ("ALIGN",         (2, 1), (3, -1), "CENTER"),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#cccccc")),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1),
             [colors.white, colors.HexColor("#f9f9f9")]),
        ]
        # Colour the InGovern recommendation cells
        for i, r in enumerate(resolutions, start=1):
            comm   = r.get("ingovern_commentary", {}) or {}
            ig_rec = str(comm.get("ingovern_recommendation", "FOR")).upper()
            if ig_rec.startswith("FOR"):
                tbl_style.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor("#0d5c32")))
                tbl_style.append(("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"))
            elif ig_rec.startswith("AGAINST"):
                tbl_style.append(("TEXTCOLOR", (3, i), (3, i), colors.HexColor("#c81919")))
                tbl_style.append(("FONTNAME",  (3, i), (3, i), "Helvetica-Bold"))

        tbl.setStyle(TableStyle(tbl_style))
        story.append(tbl)

        # Footer note
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph(
            "FOR*: Shareholders seek clarifications / raise concerns while voting FOR the resolution.",
            S("footNote", fontSize=8, fontName="Helvetica-Oblique",
              textColor=colors.HexColor("#555555")),
        ))
        story.append(Spacer(1, 4*mm))
        story.append(HRFlowable(width="100%", thickness=1,
                                color=colors.HexColor("#dddddd")))
        story.append(Paragraph(
            "InGovern  ·  www.ingovern.com  ·  © InGovern Research  ·  For Limited Circulation",
            style_footer,
        ))

        # ── RESOLUTION DETAIL PAGES ──────────────────────────────────────────
        for r in resolutions:
            story.append(PageBreak())
            comm     = r.get("ingovern_commentary", {}) or {}
            res_num  = r.get("resolution_number", "")
            title    = r.get("resolution_title") or r.get("title") or r.get("resolution_type", "")
            res_type = "Special" if r.get("special_resolution") else "Ordinary"
            mgmt_rec = comm.get("management_recommendation", r.get("board_recommendation", "FOR"))
            ig_rec   = comm.get("ingovern_recommendation", "FOR")

            # Resolution heading
            story.append(Paragraph(
                _para_text(f"Resolution No. {res_num}: {title}"),
                style_res_title,
            ))
            story.append(HRFlowable(width="100%", thickness=1.5,
                                    color=colors.HexColor("#e94560"), spaceAfter=8))

            # Rec row
            rec_data = [[
                Paragraph(f"Type of Resolution: <b>{res_type}</b>", style_rec_label),
                Paragraph(f"Management Recommendation: <b>{mgmt_rec}</b>", style_rec_label),
                Paragraph(
                    f"InGovern Recommendation: <b><font color='{'#0d5c32' if str(ig_rec).upper().startswith('FOR') else '#c81919'}'>{ig_rec}</font></b>",
                    style_rec_label,
                ),
            ]]
            rec_tbl = Table(rec_data, colWidths=["33%", "33%", "34%"])
            rec_tbl.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, -1), colors.HexColor("#f0f4f8")),
                ("TOPPADDING",  (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(rec_tbl)
            story.append(Spacer(1, 6))

            def section_header(text):
                story.append(Spacer(1, 4))
                story.append(Table(
                    [[Paragraph(text.upper(), S("sh",
                        fontSize=8.5, fontName="Helvetica-Bold",
                        textColor=colors.HexColor("#0f3460"),
                    ))]],
                    colWidths=["100%"],
                    style=TableStyle([
                        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#eef2f7")),
                        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
                        ("TOPPADDING",    (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("LINEAFTER",     (0, 0), (0, -1), 3, colors.HexColor("#e94560")),
                    ]),
                ))
                story.append(Spacer(1, 4))

            def add_paragraphs(paragraphs):
                for p in (paragraphs or []):
                    txt = str(p).strip()
                    if not txt:
                        continue
                    for line in txt.split("\n"):
                        line = line.strip()
                        if not line:
                            continue
                        if line.startswith(("•", "-", "*")):
                            story.append(Paragraph(
                                "• " + _para_text(line.lstrip("•-* ")),
                                style_bullet,
                            ))
                        else:
                            story.append(Paragraph(_para_text(line), style_body))

            # Introduction
            intro = comm.get("introduction", "")
            if intro:
                section_header("Introduction")
                story.append(Paragraph(_para_text(intro), style_body))

            # Summary
            summ = comm.get("summary_paragraphs", [])
            if summ:
                section_header("Summary")
                add_paragraphs(summ)

            # InGovern Commentary
            ig_comm = comm.get("ingovern_commentary", [])
            if ig_comm:
                section_header("InGovern Commentary")
                if isinstance(ig_comm, list):
                    add_paragraphs(ig_comm)
                else:
                    story.append(Paragraph(_para_text(str(ig_comm)), style_body))

            # Governance Concerns
            concerns = comm.get("governance_concerns", [])
            if concerns:
                section_header("Governance Concerns")
                for i, c in enumerate(concerns, 1):
                    txt = str(c).strip()
                    story.append(Paragraph(
                        f"<b>{i}.</b> {_para_text(txt)}",
                        style_body,
                    ))

            # Conclusion / Closing Recommendation
            closing = comm.get("closing_recommendation", "")
            if closing:
                section_header("Conclusion")
                story.append(Paragraph(_para_text(closing), style_body))

            # Page footer
            story.append(Spacer(1, 8*mm))
            story.append(HRFlowable(width="100%", thickness=0.5,
                                    color=colors.HexColor("#dddddd"), spaceAfter=4))
            story.append(Paragraph(
                f"© InGovern Research  ·  www.ingovern.com  ·  For Limited Circulation  ·  Page",
                style_footer,
            ))

        # ── Build PDF ────────────────────────────────────────────────────────
        def _add_page_numbers(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#888888"))
            canvas.drawCentredString(W / 2, 10*mm, f"Page {doc.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=_add_page_numbers, onLaterPages=_add_page_numbers)

        with open(filepath, "wb") as f:
            f.write(buf.getvalue())

        return {
            "status":       "success",
            "filepath":     os.path.abspath(filepath),
            "filename":     filename,
            "html_content": "",
            "message":      f"PDF saved to {filepath}",
        }

    except Exception as exc:
        import traceback
        return {
            "status":       "error",
            "filepath":     "",
            "filename":     "",
            "html_content": "",
            "message":      f"{exc}\n{traceback.format_exc()}",
        }
