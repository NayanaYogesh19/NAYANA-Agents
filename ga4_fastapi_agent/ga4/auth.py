import os

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

load_dotenv()


SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/analytics",
    "https://www.googleapis.com/auth/webmasters.readonly"

]

TOKEN_FILE = "ga4/token.json"


def get_client_config():
    return {
        "installed": {
            "client_id": os.getenv("GA4_CLIENT_ID"),
            "client_secret": os.getenv("GA4_CLIENT_SECRET"),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GA4_REDIRECT_URI", "http://localhost:8080/")]
        }
    }


def get_credentials():

    creds = None

    if os.path.exists(TOKEN_FILE):

        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:

            creds.refresh(Request())

        else:

            client_config = get_client_config()
            
            flow = InstalledAppFlow.from_client_config(
                client_config,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:

            f.write(creds.to_json())

    return creds
