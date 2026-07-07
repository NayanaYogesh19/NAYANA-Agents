"""Offline tests only — no network calls, no API keys required.
Run with: pytest
"""

from datetime import date

from agent.dedupe import dedupe_items
from agent.extractor import within_window, _parse_date
from agent.models import CandidatePage, CompanyReport, ReportItem


def test_dedupe_removes_exact_url_duplicates():
    items = [
        ReportItem(category="press_release", title="A", url="https://x.com/a"),
        ReportItem(category="press_release", title="A", url="https://x.com/a"),
    ]
    assert len(dedupe_items(items)) == 1


def test_dedupe_removes_near_duplicate_titles_same_category():
    items = [
        ReportItem(
            category="press_release",
            title="Acme launches new AI chip for edge devices",
            url="https://outlet1.com/a",
        ),
        ReportItem(
            category="press_release",
            title="Acme Launches New AI Chip For Edge Devices",
            url="https://outlet2.com/b",
        ),
    ]
    assert len(dedupe_items(items)) == 1


def test_dedupe_keeps_similar_titles_in_different_categories():
    items = [
        ReportItem(category="press_release", title="Acme wins big award", url="https://a.com/1"),
        ReportItem(category="award", title="Acme wins big award", url="https://b.com/2"),
    ]
    assert len(dedupe_items(items)) == 2


def test_within_window_true_for_date_inside_range():
    c = CandidatePage(url="https://x.com", published_date=date(2026, 6, 15))
    assert within_window(c, date(2026, 6, 1), date(2026, 6, 30)) is True


def test_within_window_false_for_date_outside_range():
    c = CandidatePage(url="https://x.com", published_date=date(2026, 5, 20))
    assert within_window(c, date(2026, 6, 1), date(2026, 6, 30)) is False


def test_within_window_false_when_date_unknown():
    # An item with no discoverable date can't be verified as belonging
    # to the requested window, so it's excluded rather than shown with
    # a blank/"Unknown" date — the report should only ever contain
    # items confirmed to fall between the user's input dates.
    c = CandidatePage(url="https://x.com", published_date=None)
    assert within_window(c, date(2026, 6, 1), date(2026, 6, 30)) is False


def test_parse_date_handles_valid_and_invalid_input():
    assert _parse_date("2026-06-15") == date(2026, 6, 15)
    assert _parse_date(None) is None
    assert _parse_date("not-a-date") is None


def test_company_report_add_sorts_into_correct_bucket():
    report = CompanyReport(
        company_name="Acme",
        company_url="https://acme.com",
        period_start=date(2026, 6, 1),
        period_end=date(2026, 6, 30),
    )
    report.add(ReportItem(category="webinar", title="W", url="https://acme.com/w"))
    assert len(report.webinars) == 1
    assert len(report.press_releases) == 0
