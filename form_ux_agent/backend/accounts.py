"""
accounts.py
Loads the accounts CSV and validates that a submitted URL
belongs to a registered account.
"""

import csv
import os
from pathlib import Path


ACCOUNTS_CSV = os.getenv("ACCOUNTS_CSV", "data/accounts.csv")


def load_accounts() -> list[dict]:
    """Return all rows from the accounts CSV as a list of dicts."""
    path = Path(ACCOUNTS_CSV)
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_all_accounts() -> list[dict]:
    """Return simplified account list for the frontend dropdown."""
    accounts = load_accounts()
    return [
        {
            "account_name": row["account_name"],
            "account_id": row["account_id"],
            "ga4_property_id": row["ga4_property_id"],
            "website_url": row["website_url"],
        }
        for row in accounts
    ]


def find_account_by_url(url: str) -> dict | None:
    """
    Match a submitted URL against registered accounts.
    Strips protocol, query params, and trailing slashes for a loose match.
    Returns the matching account row or None.
    """
    def normalise(u: str) -> str:
        # Remove protocol
        u = u.lower().replace("https://", "").replace("http://", "")
        # Remove query parameters and fragments
        u = u.split("?")[0].split("#")[0]
        # Remove trailing slashes
        return u.rstrip("/")

    target = normalise(url)
    for row in load_accounts():
        registered = normalise(row["website_url"])
        if registered in target or target in registered:
            return row
    return None


def find_account_by_name(name: str) -> dict | None:
    """Find account by exact account name (case-insensitive)."""
    for row in load_accounts():
        if row["account_name"].lower() == name.lower():
            return row
    return None
