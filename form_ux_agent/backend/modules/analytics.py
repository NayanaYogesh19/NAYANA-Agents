"""
analytics.py
Pulls form drop-off data from GA4 via Google OAuth (not service account).
Also fetches Microsoft Clarity heatmap/session/conversion data.
Falls back to simulated data if credentials are not configured.
"""

import os
import json
import requests
from datetime import date, timedelta
from pathlib import Path

GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
CLARITY_API_KEY      = os.getenv("CLARITY_API_KEY", "")

# ── Token store (file-based, swap for DB in production) ──────────────────────
TOKEN_FILE = Path("data/google_token.json")


def get_google_auth_url() -> str:
    """Return the OAuth URL to redirect the user to for GA4 consent."""
    scope = "https://www.googleapis.com/auth/analytics.readonly"
    return (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        "&response_type=code"
        f"&scope={scope}"
        "&access_type=offline"
        "&prompt=consent"
    )


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange OAuth auth code for access + refresh tokens. Call once after user consent."""
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    tokens = resp.json()
    TOKEN_FILE.parent.mkdir(exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens))
    return tokens


def _load_tokens() -> dict:
    if TOKEN_FILE.exists():
        return json.loads(TOKEN_FILE.read_text())
    return {}


def _refresh_access_token(refresh_token: str) -> str:
    resp = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    })
    data = resp.json()
    # Update stored tokens
    tokens = _load_tokens()
    tokens["access_token"] = data.get("access_token", "")
    TOKEN_FILE.write_text(json.dumps(tokens))
    return tokens["access_token"]


def _get_valid_access_token() -> str | None:
    tokens = _load_tokens()
    if not tokens:
        return None
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    # Try refreshing — GA4 tokens expire after 1h
    if refresh_token:
        try:
            access_token = _refresh_access_token(refresh_token)
        except Exception:
            pass
    return access_token


# ── GA4 ──────────────────────────────────────────────────────────────────────

def fetch_ga4_data(property_id: str = "", days: int = 30, form_fields: list = None) -> dict:
    """
    Fetch form-related events from GA4 using OAuth access token.
    property_id comes from accounts.csv — no .env variable needed.
    form_fields: list of field dicts from the scraper (used for simulated drop-off labels).
    """
    if not property_id:
        return _simulated_ga4_data(form_fields)

    access_token = _get_valid_access_token()
    if not access_token:
        return {
            **_simulated_ga4_data(form_fields),
            "ga4_error": "Not authenticated. Visit /auth/google to connect GA4.",
            "is_simulated": True,
            "needs_auth": True,
        }

    end   = date.today()
    start = end - timedelta(days=days)

    url = f"https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport"
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    body = {
        "dimensions": [{"name": "eventName"}, {"name": "pagePath"}],
        "metrics":    [{"name": "eventCount"}, {"name": "sessions"}],
        "dateRanges": [{"startDate": str(start), "endDate": str(end)}],
        "dimensionFilter": {
            "filter": {
                "fieldName": "eventName",
                "stringFilter": {"matchType": "BEGINS_WITH", "value": "form_"},
            }
        },
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=15)
        resp.raise_for_status()
        return _parse_ga4_response(resp.json())
    except Exception as e:
        return {**_simulated_ga4_data(form_fields), "ga4_error": str(e), "is_simulated": True}


def _parse_ga4_response(data: dict) -> dict:
    rows = []
    for row in data.get("rows", []):
        dims = row.get("dimensionValues", [])
        mets = row.get("metricValues", [])
        rows.append({
            "event":    dims[0]["value"] if dims else "",
            "page":     dims[1]["value"] if len(dims) > 1 else "",
            "count":    int(mets[0]["value"]) if mets else 0,
            "sessions": int(mets[1]["value"]) if len(mets) > 1 else 0,
        })

    form_starts  = sum(r["count"] for r in rows if "start"  in r["event"])
    form_submits = sum(r["count"] for r in rows if "submit" in r["event"])
    completion   = round(form_submits / form_starts * 100, 1) if form_starts else 0

    return {
        "is_simulated":    False,
        "form_starts":     form_starts,
        "form_submits":    form_submits,
        "completion_rate": f"{completion}%",
        "abandonment_rate":f"{round(100 - completion, 1)}%",
        "events":          rows[:20],
        "date_range":      "Last 30 days",
    }


# ── Microsoft Clarity ─────────────────────────────────────────────────────────

def fetch_clarity_data(project_id: str = "", days: int = 30) -> dict:
    """
    Fetch session, engagement and conversion data from Microsoft Clarity API.
    project_id is the Clarity Project ID — add a 'clarity_project_id' column
    to accounts.csv per account, or pass it in directly.
    API docs: https://learn.microsoft.com/en-us/clarity/setup-and-installation/clarity-api
    """
    if not CLARITY_API_KEY or not project_id:
        return _simulated_clarity_data()

    end_date   = date.today()
    start_date = end_date - timedelta(days=days)

    headers = {
        "Authorization": f"Bearer {CLARITY_API_KEY}",
        "Content-Type": "application/json",
    }

    # Clarity Dashboard API endpoint
    base_url = f"https://www.clarity.ms/api/v1/projects/{project_id}"

    try:
        # Fetch summary metrics
        summary_resp = requests.get(
            f"{base_url}/metrics",
            headers=headers,
            params={
                "startDate": str(start_date),
                "endDate":   str(end_date),
            },
            timeout=15,
        )
        summary_resp.raise_for_status()
        summary = summary_resp.json()

        # Fetch scroll depth / dead click / rage click metrics
        behaviour_resp = requests.get(
            f"{base_url}/heatmaps/summary",
            headers=headers,
            params={
                "startDate": str(start_date),
                "endDate":   str(end_date),
            },
            timeout=15,
        )
        behaviour = behaviour_resp.json() if behaviour_resp.ok else {}

        return _parse_clarity_response(summary, behaviour)

    except Exception as e:
        return {**_simulated_clarity_data(), "clarity_error": str(e), "is_simulated": True}


def _parse_clarity_response(summary: dict, behaviour: dict) -> dict:
    metrics = summary.get("metrics", {})
    return {
        "is_simulated":       False,
        "total_sessions":     metrics.get("totalSessions", 0),
        "engaged_sessions":   metrics.get("engagedSessions", 0),
        "engagement_rate":    f"{round(metrics.get('engagementRate', 0) * 100, 1)}%",
        "avg_session_duration": f"{round(metrics.get('avgSessionDuration', 0))}s",
        "pages_per_session":  round(metrics.get("pagesPerSession", 0), 1),
        "rage_clicks":        metrics.get("rageClicks", 0),
        "dead_clicks":        metrics.get("deadClicks", 0),
        "scroll_depth_avg":   f"{round(metrics.get('avgScrollDepth', 0) * 100, 1)}%",
        "bounce_rate":        f"{round(metrics.get('bounceRate', 0) * 100, 1)}%",
        "date_range":         f"Last {30} days",
        "source":             "Microsoft Clarity",
    }


def _simulated_clarity_data() -> dict:
    return {
        "is_simulated":        True,
        "note":                "Clarity not connected — showing illustrative data. Add CLARITY_API_KEY + clarity_project_id to connect.",
        "total_sessions":      3200,
        "engaged_sessions":    1440,
        "engagement_rate":     "45.0%",
        "avg_session_duration":"82s",
        "pages_per_session":   2.4,
        "rage_clicks":         187,
        "dead_clicks":         342,
        "scroll_depth_avg":    "54.0%",
        "bounce_rate":         "62.0%",
        "date_range":          "Last 30 days (simulated)",
        "source":              "Microsoft Clarity (simulated)",
    }


def _simulated_ga4_data(form_fields: list = None) -> dict:
    import hashlib, random
    # Seed randomness from field fingerprint so same form always gives same numbers
    # but different forms/sites give different numbers
    seed_str = "".join(
        (f.get("name") or f.get("label") or "") for f in (form_fields or [])
    ) or "default"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    field_count = len(form_fields) if form_fields else 5
    # Starts: varies by form complexity (more fields = fewer starts on average)
    starts = rng.randint(400, 2800)
    # Completion rate drops as field count rises
    base_completion = max(5.0, 28.0 - field_count * 2.5)
    completion = round(base_completion + rng.uniform(-3, 3), 1)
    submits = round(starts * completion / 100)
    abandonment = round(100 - completion, 1)
    mobile_pct = rng.randint(52, 78)
    desktop_pct = rng.randint(18, 100 - mobile_pct - 2)
    tablet_pct = 100 - mobile_pct - desktop_pct

    # Build drop-off per real field
    if form_fields:
        field_drop_off = []
        cumulative = 0
        for i, f in enumerate(form_fields):
            label = f.get("label") or f.get("placeholder") or f.get("name") or f"Field {i + 1}"
            # Each subsequent field loses more users; variance per field
            step = rng.randint(2, 10) + i * rng.randint(1, 4)
            cumulative += step
            field_drop_off.append({
                "field": f"Field {i + 1} ({label.strip('*').title()})",
                "drop_off_pct": f"{min(cumulative, 85)}%"
            })
    else:
        field_drop_off = []

    return {
        "is_simulated": True,
        "form_starts": starts,
        "form_submits": submits,
        "completion_rate": f"{completion}%",
        "abandonment_rate": f"{abandonment}%",
        "field_drop_off": field_drop_off,
        "device_split": {"mobile": f"{mobile_pct}%", "desktop": f"{desktop_pct}%", "tablet": f"{tablet_pct}%"},
        "date_range": "Last 30 days",
    }
