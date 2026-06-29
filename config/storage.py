import os

# On Railway/cloud: set STORAGE_DIR=/tmp/ingovern in env vars
# Locally defaults to ./storage (persistent)
STORAGE_DIR = os.environ.get("STORAGE_DIR", "storage")

NOTICES_DIR = os.path.join(STORAGE_DIR, "notices")
REPORTS_DIR = os.path.join(STORAGE_DIR, "reports")
SESSION_PATH = os.path.join(STORAGE_DIR, "session.json")

# Create dirs on import so the app never crashes on missing folders
os.makedirs(NOTICES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)
