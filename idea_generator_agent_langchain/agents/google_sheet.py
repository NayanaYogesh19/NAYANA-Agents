import os

import gspread

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

TOKEN_FILE = "token.json"
OAUTH_CLIENT_FILE = os.getenv("GOOGLE_CREDENTIALS", "oauth_client.json")


def get_oauth_credentials() -> Credentials:
    """
    Returns valid OAuth2 credentials.
    - Loads saved token from token.json if it exists.
    - Refreshes automatically if expired.
    - Opens browser for authorization on first run.
    """

    creds = None

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                OAUTH_CLIENT_FILE,
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def update_google_sheet(ideas: list):
    """
    Equivalent to the n8n Google Sheets Append or Update Row node.
    Uses OAuth2 credentials from oauth_client.json.
    """

    creds = get_oauth_credentials()
    client = gspread.authorize(creds)

    sheet = client.open_by_key(
        os.getenv("GOOGLE_SHEET_ID")
    ).sheet1

    for idea in ideas:

        row = [
            idea.get("idea_id", ""),
            idea.get("idea_title", ""),
            idea.get("platform", ""),
            idea.get("content_type", ""),
            idea.get("description", ""),
            idea.get("hook", ""),
            idea.get("target_audience", ""),
            idea.get("goal", ""),
            idea.get("trend_used", ""),
            idea.get("cta", ""),
            idea.get("lead_magnet", "")
        ]

        sheet.append_row(row)