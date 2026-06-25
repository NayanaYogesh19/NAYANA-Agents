"""
PDF Report Generator
--------------------
Renders the governance report as a downloadable PDF using Jinja2 + WeasyPrint.
Falls back to returning the rendered HTML when WeasyPrint is unavailable.
"""

import os
from datetime import date

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR  = "templates"
TEMPLATE_NAME = "report_template.html"
REPORTS_DIR   = "storage/reports"


def _get_jinja_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=True,
    )


def _sanitize_filename(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


def render_html(session: dict) -> str:
    """
    Render the Jinja2 template to an HTML string.
    """
    env      = _get_jinja_env()
    template = env.get_template(TEMPLATE_NAME)

    return template.render(
        company_name     = session.get("company_name", ""),
        financial_year   = session.get("financial_year", ""),
        report_date      = date.today().strftime("%d %B %Y"),
        approved_by      = session.get("approved_by", ""),
        analyst_comments = session.get("comments", ""),
        resolutions      = session.get("resolutions", []),
    )


def generate_pdf_report(session: dict) -> dict:
    """
    Generate a PDF governance report from the current session.

    Saves to: storage/reports/<Company>_<FY>_Report.pdf

    Returns:
    {
        status       : "success" | "html_only" | "error",
        filepath     : str   (absolute path),
        filename     : str,
        html_content : str   (always present as fallback),
        message      : str,
    }
    """
    os.makedirs(REPORTS_DIR, exist_ok=True)

    company_name   = session.get("company_name", "Company")
    financial_year = session.get("financial_year", "FY")
    safe_company   = _sanitize_filename(company_name)
    safe_fy        = _sanitize_filename(financial_year)
    filename       = f"{safe_company}_{safe_fy}_Report.pdf"
    filepath       = os.path.join(REPORTS_DIR, filename)

    html_content = render_html(session)

    # ── Try WeasyPrint ─────────────────────────────────────────────────────
    try:
        from weasyprint import HTML as WeasyHTML

        WeasyHTML(string=html_content, base_url=".").write_pdf(filepath)

        return {
            "status":       "success",
            "filepath":     os.path.abspath(filepath),
            "filename":     filename,
            "html_content": html_content,
            "message":      f"PDF saved to {filepath}",
        }

    except ImportError:
        # WeasyPrint not installed: save HTML as fallback
        html_filename = filename.replace(".pdf", ".html")
        html_filepath = os.path.join(REPORTS_DIR, html_filename)

        with open(html_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return {
            "status":       "html_only",
            "filepath":     os.path.abspath(html_filepath),
            "filename":     html_filename,
            "html_content": html_content,
            "message":      "WeasyPrint not installed; HTML report saved instead.",
        }

    except Exception as exc:
        return {
            "status":       "error",
            "filepath":     "",
            "filename":     "",
            "html_content": html_content,
            "message":      str(exc),
        }
