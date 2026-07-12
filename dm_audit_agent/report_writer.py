"""
report_writer.py — persists each stage's output as a text file, replacing the
n8n "Create a document" / "Update a document" (Google Docs) + "Share file"
(Google Drive) nodes. Each run gets its own folder under reports/, and every
document produced during the run (SEO Audit, Social Media Audit, SEO
Strategy, Customer Presentable Audit) is saved there and served back via the
FastAPI download endpoint instead of a Google Docs link.
"""

from __future__ import annotations

import os
import re
import uuid
from datetime import datetime

from config import Config


def _slug(text: str) -> str:
    text = re.sub(r"^https?://", "", text.strip().lower())
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    return text[:60] or "domain"


def create_run(domain: str) -> tuple[str, str]:
    """Create a new run folder. Returns (run_id, run_dir)."""
    run_id = f"{_slug(domain)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    run_dir = os.path.join(Config.REPORTS_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    return run_id, run_dir


def save_document(run_dir: str, filename: str, title: str, body: str) -> str:
    """Save a plain-text intermediate-stage document (used for the internal
    per-stage debug artifacts, not the final client-facing PDF)."""
    path = os.path.join(run_dir, filename)
    content = f"{title}\n" + "-" * 29 + f"\n{body}\n" + "-" * 30 + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def pdf_filename(company_name: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9 _-]+", "", company_name).strip() or "Company"
    return f"{safe_name} Audit Report.pdf"
