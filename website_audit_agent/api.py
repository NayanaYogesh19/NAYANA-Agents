from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import os
from urllib.parse import urlparse
from fastapi.staticfiles import StaticFiles
import sys

app = FastAPI(title="Website Audit Strategy Agent")

# ── Resolve the project root directory once at startup ───────────────────────
# This is the directory where api.py lives — and where main.py and output/ live.
# We use this as the cwd for subprocess so all relative paths resolve correctly
# regardless of where uvicorn was launched from.
PROJECT_ROOT  = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR    = os.path.join(PROJECT_ROOT, "output")
FRONTEND_DIR  = os.path.join(PROJECT_ROOT, "frontend")

# Ensure output directory exists before mounting
os.makedirs(OUTPUT_DIR, exist_ok=True)

app.mount(
    "/output",
    StaticFiles(directory=OUTPUT_DIR),
    name="output"
)

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)


@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuditRequest(BaseModel):
    target_url: str
    competitor_url: str


@app.post("/audit")
def run_audit(request: AuditRequest):

    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "main.py"),
        "--target",
        request.target_url,
        "--competitor",
        request.competitor_url,
    ]

    print(f"\n[api] Running audit for: {request.target_url} vs {request.competitor_url}")
    print(f"[api] Project root: {PROJECT_ROOT}")
    print(f"[api] Python executable: {sys.executable}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,          # KEY FIX: subprocess runs from project root
                                   # so output/xxx.pdf resolves correctly
    )

    print("\n[api] STDOUT:")
    print(result.stdout)

    print("\n[api] STDERR:")
    print(result.stderr)

    # ── Step 1: Parse the exact PDF path printed by main.py ──────────────────
    # main.py prints: "PDF location: output/xxx_vs_yyy_audit.pdf"
    # We extract that line and resolve it to an absolute path.
    latest_pdf = None

    for line in result.stdout.splitlines():
        stripped = line.strip()
        if stripped.startswith("PDF location:"):
            raw_path = stripped.replace("PDF location:", "").strip()

            # Resolve to absolute path relative to project root
            if not os.path.isabs(raw_path):
                abs_path = os.path.join(PROJECT_ROOT, raw_path)
            else:
                abs_path = raw_path

            if os.path.exists(abs_path):
                latest_pdf = abs_path
                print(f"\n[api] PDF resolved from stdout: {latest_pdf}")
            else:
                print(f"\n[api] WARNING: PDF path from stdout not found on disk: {abs_path}")
            break

    # ── Step 2: Fallback — build expected path from domain slugs ─────────────
    # Constructs the exact filename pdf_generator.py would have written.
    # Deterministic — avoids mtime picking wrong old file.
    if latest_pdf is None:
        print("\n[api] Trying deterministic path fallback from domain slugs...")

        def _slug(url: str) -> str:
            host = urlparse(url).netloc.lower()
            if host.startswith("www."):
                host = host[4:]
            return host.replace(".", "_").replace("-", "_")

        expected_prefix = (
            f"{_slug(request.target_url)}_vs_{_slug(request.competitor_url)}_audit"
        )
        candidates = [
            f for f in os.listdir(OUTPUT_DIR)
            if f.startswith(expected_prefix) and f.endswith(".pdf")
        ]

        if candidates:
            latest_pdf = max(
                [os.path.join(OUTPUT_DIR, f) for f in candidates],
                key=os.path.getmtime
            )
            print(f"[api] PDF resolved from slug fallback: {latest_pdf}")
        else:
            print(f"[api] Slug fallback path not found for prefix: {expected_prefix}")

    # ── Step 3: Last resort — newest file in output dir ──────────────────────
    # Only if both above methods fail.
    if latest_pdf is None:
        print("\n[api] Last resort: scanning output dir by mtime...")
        if os.path.exists(OUTPUT_DIR):
            pdf_files = [
                f for f in os.listdir(OUTPUT_DIR)
                if f.endswith(".pdf")
            ]
            if pdf_files:
                latest_pdf = max(
                    [os.path.join(OUTPUT_DIR, f) for f in pdf_files],
                    key=os.path.getmtime
                )
                print(f"[api] PDF resolved from mtime (last resort): {latest_pdf}")

    # ── Return result ─────────────────────────────────────────────────────────
    if latest_pdf is None:
        return {
            "success": False,
            "error": "No PDF report was generated. Check stderr for details.",
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    pdf_filename = os.path.basename(latest_pdf)

    return {
        "success": True,
        "report_url": f"http://127.0.0.1:8000/output/{pdf_filename}",
        "stdout": result.stdout,
        "stderr": result.stderr
    }