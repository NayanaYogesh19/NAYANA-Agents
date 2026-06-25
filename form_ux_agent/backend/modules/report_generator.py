"""
report_generator.py
Generates the final PDF redesign brief and UX improvement table (CSV).
Uses ReportLab for PDF generation.
"""

import os
import csv
import json
from datetime import date
from pathlib import Path

OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# Brand colours matching Trilliant Digital theme
PURPLE_DARK = (59 / 255, 15 / 255, 78 / 255)   # #3B0F4E
PURPLE_MID = (92 / 255, 26 / 255, 110 / 255)    # #5C1A6E
WHITE = (1, 1, 1)
GREY_LIGHT = (0.95, 0.95, 0.95)
GREY_TEXT = (0.3, 0.3, 0.3)
GREEN = (0.1, 0.6, 0.2)
RED = (0.8, 0.1, 0.1)


def generate_pdf_report(
    account_name: str,
    url: str,
    audience: str,
    business_goal: str,
    ux_results: dict,
    diagnosis: dict,
    conversion_loss: dict,
    analytics: dict,
    report_summary: str,
    filename: str = "",
) -> str:
    """Generate PDF and return the output file path."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, PageBreak,
        )

        if not filename:
            safe = account_name.replace(" ", "_").lower()
            filename = f"form_audit_{safe}_{date.today()}.pdf"

        filepath = OUTPUT_DIR / filename
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        rl_purple = colors.Color(*PURPLE_DARK)
        rl_purple_mid = colors.Color(*PURPLE_MID)
        rl_grey = colors.Color(*GREY_TEXT)

        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=rl_purple, fontSize=20, spaceAfter=8)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=rl_purple_mid, fontSize=14, spaceAfter=6)
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, textColor=rl_grey, leading=15, spaceAfter=6)
        label = ParagraphStyle("label", parent=styles["Normal"], fontSize=9, textColor=colors.white, leading=12)

        story = []

        # ── Cover ────────────────────────────────────────────
        story.append(Paragraph("Form &amp; UX Optimisation Agent", h1))
        story.append(Paragraph("Redesign Brief &amp; UX Improvement Report", h2))
        story.append(HRFlowable(width="100%", thickness=2, color=rl_purple))
        story.append(Spacer(1, 0.3 * cm))

        meta = [
            ["Account", account_name],
            ["URL Audited", url],
            ["Audience", audience.upper()],
            ["Business Goal", business_goal],
            ["Report Date", str(date.today())],
            ["UX Score", f"{ux_results.get('ux_score', 0)}/100  (Grade {ux_results.get('ux_grade', 'N/A')})"],
        ]
        meta_table = Table(meta, colWidths=[4 * cm, 13 * cm])
        meta_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), rl_purple),
            ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (1, 0), (1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.8, 0.8, 0.8)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 0.5 * cm))

        # ── Executive Summary ────────────────────────────────
        story.append(Paragraph("Executive Summary", h2))
        summary_text = report_summary or diagnosis.get("executive_summary", "Analysis complete. See findings below.")
        story.append(Paragraph(str(summary_text).replace("\n", "<br/>"), body))
        story.append(Spacer(1, 0.4 * cm))

        # ── UX Score Card ────────────────────────────────────
        story.append(Paragraph("UX Score Breakdown", h2))
        checks = ux_results.get("checks", {})
        score_data = [["Check", "Score", "Max", "Status", "Finding"]]
        for key, chk in checks.items():
            status = "✓ Pass" if chk.get("passed") else "✗ Fail"
            score_data.append([
                chk.get("name", key),
                str(chk.get("score", 0)),
                str(chk.get("max_score", 10)),
                status,
                chk.get("finding", "")[:60],
            ])

        score_table = Table(score_data, colWidths=[3.5 * cm, 1.5 * cm, 1.2 * cm, 1.8 * cm, 9 * cm])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_purple),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.4 * cm))

        # ── Conversion Lift ──────────────────────────────────
        story.append(Paragraph("Conversion Lift Estimate", h2))
        lift_data = [
            ["Metric", "Value"],
            ["Current Estimated Conversion Rate", conversion_loss.get("current_estimated_rate", "N/A")],
            ["Projected Rate After Fixes", conversion_loss.get("projected_rate_after_fixes", "N/A")],
            ["Estimated Lift", conversion_loss.get("estimated_lift", "N/A")],
            ["Assumptions", conversion_loss.get("assumptions", "")],
        ]
        lift_table = Table(lift_data, colWidths=[7 * cm, 10 * cm])
        lift_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), rl_purple),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(lift_table)
        story.append(Spacer(1, 0.4 * cm))

        # ── Key Issues ────────────────────────────────────────
        key_issues = diagnosis.get("key_issues", [])
        if key_issues:
            story.append(Paragraph("Key Issues Identified", h2))
            for issue in key_issues:
                story.append(Paragraph(f"• {issue}", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── Root Causes ───────────────────────────────────────
        root_causes = diagnosis.get("root_causes", [])
        if root_causes:
            story.append(Paragraph("Root Causes (Ranked by Impact)", h2))
            for i, cause in enumerate(root_causes, 1):
                story.append(Paragraph(f"{i}. {cause}", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── Quick Wins ────────────────────────────────────────
        story.append(Paragraph("Quick Wins (Fix in &lt; 1 Hour)", h2))
        quick_wins = diagnosis.get("quick_wins", ["See UX check findings above."])
        for i, win in enumerate(quick_wins, 1):
            story.append(Paragraph(f"{i}. {win}", body))
        story.append(Spacer(1, 0.3 * cm))

        # ── UX Optimisation Plan ──────────────────────────────
        ux_plan = diagnosis.get("ux_optimisation_plan", [])
        if ux_plan:
            story.append(Paragraph("UX Optimisation Plan", h2))
            for i, step in enumerate(ux_plan, 1):
                story.append(Paragraph(f"{i}. {step}", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── Form Redesign Recommendations ─────────────────────
        redesign = diagnosis.get("form_redesign_recommendations", [])
        if redesign:
            story.append(Paragraph("Form Redesign Recommendations", h2))
            for i, rec in enumerate(redesign, 1):
                story.append(Paragraph(f"{i}. {rec}", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── Strategic Fixes ───────────────────────────────────
        strategic = diagnosis.get("strategic_fixes", [])
        if strategic:
            story.append(Paragraph("Strategic Fixes (Require Dev Work)", h2))
            for i, fix in enumerate(strategic, 1):
                story.append(Paragraph(f"{i}. {fix}", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── CTA Variants ─────────────────────────────────────
        cta_variants = diagnosis.get("cta_variants", [])
        if cta_variants:
            story.append(Paragraph("CTA Button Variants to A/B Test", h2))
            for i, cta in enumerate(cta_variants, 1):
                story.append(Paragraph(f"Variant {i}: <b>{cta}</b>", body))
            story.append(Spacer(1, 0.3 * cm))

        # ── A/B Test Plan ─────────────────────────────────────
        ab_plan = diagnosis.get("ab_test_plan", [])
        if ab_plan:
            story.append(PageBreak())
            story.append(Paragraph("A/B Test Plan", h2))
            ab_data = [["Test", "Hypothesis", "Control", "Variant", "Metric", "Duration"]]
            for test in ab_plan:
                ab_data.append([
                    test.get("test_id", ""),
                    test.get("hypothesis", "")[:40],
                    test.get("control", "")[:25],
                    test.get("variant", "")[:25],
                    test.get("metric", "")[:25],
                    f"{test.get('duration_days', 14)}d",
                ])
            ab_table = Table(ab_data, colWidths=[1.2 * cm, 5 * cm, 3 * cm, 3 * cm, 3 * cm, 1.8 * cm])
            ab_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), rl_purple),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.Color(0.96, 0.96, 0.96)]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.Color(0.85, 0.85, 0.85)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("WORDWRAP", (0, 0), (-1, -1), True),
            ]))
            story.append(ab_table)

        # ── Footer ────────────────────────────────────────────
        story.append(Spacer(1, 1 * cm))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_purple))
        story.append(Paragraph("Generated by Form &amp; UX Optimisation Agent · Trilliant Digital", body))

        doc.build(story)
        return str(filepath)

    except ImportError:
        return _generate_text_report(account_name, url, ux_results, diagnosis, conversion_loss, filename)


def generate_ux_table_csv(
    ux_results: dict,
    diagnosis: dict,
    filename: str = "",
) -> str:
    """Generate the prioritised UX improvement table as CSV."""
    if not filename:
        filename = f"ux_improvement_table_{date.today()}.csv"

    filepath = OUTPUT_DIR / filename
    checks = ux_results.get("checks", {})

    rows = []
    # Failed UX rule checks
    for key, chk in checks.items():
        if not chk.get("passed"):
            rows.append({
                "Category": "UX Rule",
                "Issue": chk.get("name", key),
                "Severity": "High" if chk.get("max_score", 0) >= 10 else "Medium",
                "Finding": chk.get("finding", ""),
                "Fix / Recommendation": chk.get("fix", ""),
                "Dev Effort": "Low" if "label" in key or "cta" in key else "Medium",
                "Expected Lift %": "+5-15%" if chk.get("max_score", 0) >= 10 else "+3-8%",
            })

    # UX optimisation plan steps
    for i, step in enumerate(diagnosis.get("ux_optimisation_plan", []), 1):
        rows.append({
            "Category": "UX Optimisation",
            "Issue": f"UX Plan Step {i}",
            "Severity": "Medium",
            "Finding": step,
            "Fix / Recommendation": step,
            "Dev Effort": "Medium",
            "Expected Lift %": "+2-5%",
        })

    # Form redesign recommendations
    for i, rec in enumerate(diagnosis.get("form_redesign_recommendations", []), 1):
        rows.append({
            "Category": "Form Redesign",
            "Issue": f"Redesign Recommendation {i}",
            "Severity": "Medium",
            "Finding": rec,
            "Fix / Recommendation": rec,
            "Dev Effort": "Medium",
            "Expected Lift %": "+3-8%",
        })

    # Strategic fixes
    for i, fix in enumerate(diagnosis.get("strategic_fixes", []), 1):
        rows.append({
            "Category": "Strategic Fix",
            "Issue": f"Strategic Fix {i}",
            "Severity": "High",
            "Finding": fix,
            "Fix / Recommendation": fix,
            "Dev Effort": "High",
            "Expected Lift %": "+5-15%",
        })

    fieldnames = ["Category", "Issue", "Severity", "Finding", "Fix / Recommendation", "Dev Effort", "Expected Lift %"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return str(filepath)


def generate_new_form_pdf(
    account_name: str,
    website_url: str,
    business_goal: str,
    audience: str,
    blueprint: dict,
    filename: str = "",
) -> str:
    """Generate a PDF blueprint for a newly designed form."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

        if not filename:
            safe = account_name.replace(" ", "_").lower()
            filename = f"new_form_blueprint_{safe}_{date.today()}.pdf"

        filepath = OUTPUT_DIR / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        rl_purple = colors.Color(*PURPLE_DARK)
        rl_purple_mid = colors.Color(*PURPLE_MID)
        rl_grey = colors.Color(*GREY_TEXT)
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=rl_purple, fontSize=20, spaceAfter=8)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=rl_purple_mid, fontSize=13, spaceAfter=6)
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, textColor=rl_grey, leading=15, spaceAfter=4)
        bullet = ParagraphStyle("bullet", parent=styles["Normal"], fontSize=10, textColor=rl_grey, leading=14, leftIndent=12, spaceAfter=3)

        story = []
        story.append(Paragraph("Form &amp; UX Optimisation Agent", h1))
        story.append(Paragraph("New Form Blueprint", h2))
        story.append(HRFlowable(width="100%", thickness=2, color=rl_purple))
        story.append(Spacer(1, 0.3*cm))

        meta = [
            ["Account", account_name],
            ["Website", website_url],
            ["Business Goal", business_goal],
            ["Audience", audience.upper()],
            ["Report Date", str(date.today())],
            ["Projected UX Score", f"{blueprint.get('projected_ux_score', '—')}/100"],
            ["Projected Conversion Rate", blueprint.get("projected_conversion_rate", "—")],
        ]
        mt = Table(meta, colWidths=[4*cm, 13*cm])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), rl_purple),
            ("TEXTCOLOR", (0,0), (0,-1), colors.white),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (1,0), (1,-1), [colors.white, colors.Color(0.96,0.96,0.96)]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.Color(0.8,0.8,0.8)),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.4*cm))

        # Form title & description
        story.append(Paragraph("Recommended Form", h2))
        story.append(Paragraph(f"<b>Title:</b> {blueprint.get('form_title', '')}", body))
        story.append(Paragraph(f"<b>Description:</b> {blueprint.get('form_description', '')}", body))
        story.append(Paragraph(f"<b>CTA Button:</b> {blueprint.get('cta_button_text', '')}", body))
        story.append(Paragraph(f"<b>Position:</b> {blueprint.get('form_position_recommendation', '')}", body))
        story.append(Spacer(1, 0.3*cm))

        # Recommended fields table
        story.append(Paragraph("Recommended Form Fields", h2))
        fields = blueprint.get("recommended_fields", [])
        if fields:
            fdata = [["#", "Label", "Type", "Required", "Why Include"]]
            for i, f in enumerate(fields, 1):
                fdata.append([
                    str(i),
                    f.get("label", ""),
                    f.get("type", "text"),
                    "Yes" if f.get("required") else "No",
                    f.get("why_include", "")[:60],
                ])
            ft = Table(fdata, colWidths=[0.7*cm, 3.5*cm, 2*cm, 1.8*cm, 9*cm])
            ft.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), rl_purple),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 8),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.96,0.96,0.96)]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.Color(0.85,0.85,0.85)),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
            ]))
            story.append(ft)
        story.append(Spacer(1, 0.3*cm))

        def _section(title, items):
            if not items:
                return
            story.append(Paragraph(title, h2))
            for i, item in enumerate(items, 1):
                story.append(Paragraph(f"{i}. {item}", bullet))
            story.append(Spacer(1, 0.2*cm))

        _section("Why This Form Works", blueprint.get("why_this_works", []))
        _section("What Happens When Someone Submits", blueprint.get("what_happens_next", []))
        _section("Optimisation Strategies", blueprint.get("optimization_strategies", []))
        _section("Field Optimisation Tips", blueprint.get("field_optimization_tips", []))
        _section("Trust Signals to Add", blueprint.get("trust_signals_to_add", []))
        _section("Implementation Plan", blueprint.get("implementation_plan", []))

        story.append(Paragraph("GDPR Consent Text", h2))
        story.append(Paragraph(blueprint.get("gdpr_consent_text", ""), body))
        story.append(Spacer(1, 0.3*cm))

        ab = blueprint.get("ab_test_plan", [])
        if ab:
            story.append(Paragraph("A/B Test Plan", h2))
            ab_data = [["Test", "Hypothesis", "Control", "Variant", "Metric", "Days"]]
            for t in ab:
                ab_data.append([t.get("test_id",""), t.get("hypothesis","")[:40],
                                 t.get("control","")[:25], t.get("variant","")[:25],
                                 t.get("metric","")[:20], str(t.get("duration_days",14))])
            abt = Table(ab_data, colWidths=[1.2*cm, 5*cm, 3*cm, 3*cm, 2.5*cm, 1.3*cm])
            abt.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), rl_purple),
                ("TEXTCOLOR", (0,0), (-1,0), colors.white),
                ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE", (0,0), (-1,-1), 7),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.Color(0.96,0.96,0.96)]),
                ("GRID", (0,0), (-1,-1), 0.5, colors.Color(0.85,0.85,0.85)),
                ("VALIGN", (0,0), (-1,-1), "TOP"),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(abt)

        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_purple))
        story.append(Paragraph("Generated by Form &amp; UX Optimisation Agent · Trilliant Digital", body))
        doc.build(story)
        return str(filepath)
    except ImportError:
        return str(OUTPUT_DIR / filename)


def generate_meta_form_pdf(
    account_name: str,
    business_goal: str,
    audience: str,
    meta_spec: dict,
    filename: str = "",
) -> str:
    """Generate a PDF for the Meta instant form specification."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

        if not filename:
            safe = account_name.replace(" ", "_").lower()
            filename = f"meta_form_spec_{safe}_{date.today()}.pdf"

        filepath = OUTPUT_DIR / filename
        doc = SimpleDocTemplate(str(filepath), pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)

        rl_purple = colors.Color(*PURPLE_DARK)
        rl_purple_mid = colors.Color(*PURPLE_MID)
        rl_grey = colors.Color(*GREY_TEXT)
        meta_blue = colors.Color(0.094, 0.463, 0.973)  # Meta brand blue
        styles = getSampleStyleSheet()
        h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=rl_purple, fontSize=20, spaceAfter=8)
        h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=rl_purple_mid, fontSize=13, spaceAfter=6)
        h3 = ParagraphStyle("h3", parent=styles["Heading3"], textColor=meta_blue, fontSize=11, spaceAfter=4)
        body = ParagraphStyle("body", parent=styles["Normal"], fontSize=10, textColor=rl_grey, leading=15, spaceAfter=4)
        opt = ParagraphStyle("opt", parent=styles["Normal"], fontSize=9, textColor=colors.Color(0.4,0.4,0.4), leading=13, leftIndent=16, spaceAfter=2)

        story = []
        story.append(Paragraph("Form &amp; UX Optimisation Agent", h1))
        story.append(Paragraph("Meta Instant Form Specification", h2))
        story.append(HRFlowable(width="100%", thickness=2, color=rl_purple))
        story.append(Spacer(1, 0.3*cm))

        meta_info = [
            ["Account", account_name],
            ["Business Goal", business_goal],
            ["Audience", audience.upper()],
            ["Form Name", meta_spec.get("form_name", "")],
            ["Form Type", meta_spec.get("form_type", "")],
            ["Report Date", str(date.today())],
        ]
        mt = Table(meta_info, colWidths=[4*cm, 13*cm])
        mt.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (0,-1), rl_purple),
            ("TEXTCOLOR", (0,0), (0,-1), colors.white),
            ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (1,0), (1,-1), [colors.white, colors.Color(0.96,0.96,0.96)]),
            ("GRID", (0,0), (-1,-1), 0.5, colors.Color(0.8,0.8,0.8)),
            ("TOPPADDING", (0,0), (-1,-1), 5),
            ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        story.append(mt)
        story.append(Spacer(1, 0.4*cm))

        def _options_section(section_title, field_label, chosen, options):
            story.append(Paragraph(section_title, h3))
            story.append(Paragraph(f"<b>Recommended:</b> {chosen}", body))
            if options:
                story.append(Paragraph("<i>All options to choose from:</i>", opt))
                for i, o in enumerate(options, 1):
                    story.append(Paragraph(f"  {i}. {o}", opt))
            story.append(Spacer(1, 0.15*cm))

        # Intro Card
        story.append(Paragraph("Intro Screen", h2))
        intro = meta_spec.get("intro_card", {})
        _options_section("Headline", "headline", intro.get("headline",""), intro.get("headline_options",[]))
        _options_section("Description", "description", intro.get("description",""), intro.get("description_options",[]))
        story.append(Paragraph(f"<b>Background Image:</b> {intro.get('image_recommendation','')}", body))
        story.append(Spacer(1, 0.3*cm))

        # Questions
        story.append(Paragraph("Questions Screen", h2))
        qs = meta_spec.get("questions_section", {})
        _options_section("Contact Info Description", "description", qs.get("description",""), qs.get("description_options",[]))
        story.append(Paragraph(f"<b>Pre-fill Fields:</b> {', '.join(qs.get('pre_fill_fields', []))}", body))
        story.append(Spacer(1, 0.3*cm))

        # Privacy
        story.append(Paragraph("Privacy Policy Screen", h2))
        pp = meta_spec.get("privacy_policy", {})
        _options_section("Privacy Link Text", "link_text", pp.get("link_text",""), pp.get("link_text_options",[]))
        story.append(Paragraph(f"<b>URL:</b> {pp.get('url','')}", body))
        story.append(Spacer(1, 0.3*cm))

        # Thank You
        story.append(Paragraph("Thank You Screen", h2))
        ty = meta_spec.get("thank_you_screen", {})
        _options_section("Headline", "headline", ty.get("headline",""), ty.get("headline_options",[]))
        _options_section("Description", "description", ty.get("description",""), ty.get("description_options",[]))
        _options_section("CTA Button", "cta", ty.get("cta_button_text",""), ty.get("cta_options",[]))
        story.append(Spacer(1, 0.3*cm))

        # How this helps
        how = meta_spec.get("how_this_helps", [])
        if how:
            story.append(Paragraph("How This Form Helps Your Business", h2))
            for i, h in enumerate(how, 1):
                story.append(Paragraph(f"{i}. {h}", body))
            story.append(Spacer(1, 0.2*cm))

        # Optimisation tips
        tips = meta_spec.get("optimisation_tips", [])
        if tips:
            story.append(Paragraph("Optimisation Tips", h2))
            for i, t in enumerate(tips, 1):
                story.append(Paragraph(f"{i}. {t}", body))
            story.append(Spacer(1, 0.2*cm))

        # CRM & email validation
        story.append(Paragraph("CRM &amp; Email Validation Setup", h2))
        story.append(Paragraph(meta_spec.get("crm_sync_note", ""), body))
        ev = meta_spec.get("email_validation", {})
        story.append(Paragraph(f"<b>Email Tool:</b> {ev.get('tool_recommended','')} — {ev.get('setup_note','')}", body))

        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=rl_purple))
        story.append(Paragraph("Generated by Form &amp; UX Optimisation Agent · Trilliant Digital", body))
        doc.build(story)
        return str(filepath)
    except ImportError:
        return str(OUTPUT_DIR / filename)


def _generate_text_report(account_name, url, ux_results, diagnosis, conversion_loss, filename) -> str:
    """Text fallback when ReportLab is not installed."""
    if not filename:
        filename = f"form_audit_{date.today()}.txt"
    filepath = OUTPUT_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("FORM & UX OPTIMISATION REPORT\n")
        f.write(f"Account: {account_name}\n")
        f.write(f"URL: {url}\n")
        f.write(f"UX Score: {ux_results.get('ux_score')}/100\n\n")
        f.write("KEY ISSUES\n")
        for issue in diagnosis.get("key_issues", []):
            f.write(f"• {issue}\n")
        f.write("\nROOT CAUSES\n")
        for i, cause in enumerate(diagnosis.get("root_causes", []), 1):
            f.write(f"{i}. {cause}\n")
        f.write("\nQUICK WINS\n")
        for i, win in enumerate(diagnosis.get("quick_wins", []), 1):
            f.write(f"{i}. {win}\n")
        f.write("\nUX OPTIMISATION PLAN\n")
        for i, step in enumerate(diagnosis.get("ux_optimisation_plan", []), 1):
            f.write(f"{i}. {step}\n")
        f.write("\nFORM REDESIGN RECOMMENDATIONS\n")
        for i, rec in enumerate(diagnosis.get("form_redesign_recommendations", []), 1):
            f.write(f"{i}. {rec}\n")
        f.write("\nSTRATEGIC FIXES\n")
        for i, fix in enumerate(diagnosis.get("strategic_fixes", []), 1):
            f.write(f"{i}. {fix}\n")
        f.write("\nCTA VARIANTS TO A/B TEST\n")
        for i, cta in enumerate(diagnosis.get("cta_variants", []), 1):
            f.write(f"Variant {i}: {cta}\n")
        f.write("\nCONVERSION LIFT\n")
        f.write(f"Current: {conversion_loss.get('current_estimated_rate')}\n")
        f.write(f"Projected: {conversion_loss.get('projected_rate_after_fixes')}\n")
        f.write(f"Lift: {conversion_loss.get('estimated_lift')}\n")
    return str(filepath)
