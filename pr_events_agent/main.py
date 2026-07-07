"""CLI entry point.

Examples:
    python main.py --url https://www.tenstorrent.com --start 2026-06-01 --end 2026-06-30
    python main.py --url https://www.tenstorrent.com --month 2026-06
    python main.py --url https://www.tenstorrent.com --month 2026-06 --output email
"""

from __future__ import annotations

import argparse
import calendar
import logging
import sys
from datetime import date, datetime

from agent.pipeline import run
from output.sheet_writer import write_local_xlsx, write_google_sheet
from output.email_sender import send_report_email


def _parse_month(month_str: str) -> tuple[date, date]:
    year, month = (int(p) for p in month_str.split("-"))
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])
    return start, end


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PR & Events competitor report agent")
    parser.add_argument("--url", required=True, help="Company website URL, e.g. https://example.com")

    period = parser.add_mutually_exclusive_group(required=True)
    period.add_argument("--month", help="Report a full calendar month, format YYYY-MM")
    period.add_argument("--start", help="Custom period start date, format YYYY-MM-DD")

    parser.add_argument("--end", help="Custom period end date, format YYYY-MM-DD "
                                       "(required if --start is used)")
    parser.add_argument(
        "--output",
        choices=["sheet", "email", "both"],
        default="sheet",
        help="Where to send the finished report (default: sheet). "
             "A local .xlsx is always written regardless of this choice.",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")

    args = parser.parse_args()
    if args.start and not args.end:
        parser.error("--end is required when using --start")
    return args


def main() -> int:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    )

    if args.month:
        start, end = _parse_month(args.month)
    else:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
        end = datetime.strptime(args.end, "%Y-%m-%d").date()

    try:
        report = run(args.url, start, end)
    except Exception:
        logging.exception("Pipeline run failed")
        return 1

    # The local spreadsheet is always written — it's the guaranteed
    # output even if every optional integration is unconfigured.
    xlsx_path = write_local_xlsx(report)
    print(f"\nReport written to: {xlsx_path}")

    if args.output in ("sheet", "both"):
        if write_google_sheet(report):
            print("Also appended to configured Google Sheet.")

    if args.output in ("email", "both"):
        if send_report_email(report):
            print(f"Emailed to {report.company_name}'s reviewer.")

    total = sum(len(v) for v in report.items_by_category().values())
    print(f"\nFound {total} items for {report.company_name} "
          f"({report.period_start} to {report.period_end}).")
    print("Review before sending anywhere external — see README, 'Accuracy expectations'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
