# Tracking Tags Hygiene Agent

An automated tracking audit tool that crawls websites, detects analytics tags, validates events, checks for duplicates, and generates a PDF report — all through a FastAPI web interface.

## Features

- Detects tracking tags: Google Tag Manager, Google Analytics, Meta Pixel, LinkedIn Insight Tag, TikTok Pixel
- Monitors network requests to capture fired events
- Validates events against B2B / B2C industry standards
- Identifies duplicate tag firing
- Simulates real user behavior (scrolling, clicking, form detection)
- Builds a customer interaction journey
- Generates a downloadable PDF audit report

## Project Structure

```
tracking-agent/
├── main.py                        # FastAPI app entry point
├── requirements.txt               # Python dependencies
├── reports/                       # Generated PDF reports
├── services/
│   ├── audit_service.py           # Runs audit in subprocess
│   ├── audit_worker.py            # Full Playwright audit logic
│   ├── journey_service.py         # Builds customer journey
│   └── pdf_service.py             # Generates PDF report
├── tools/
│   ├── browser_tool.py            # Opens website with Playwright
│   ├── crawler.py                 # Multi-page crawler
│   ├── tag_detector.py            # Detects tracking tags from HTML
│   ├── network_monitor.py         # Monitors network requests
│   ├── event_validator.py         # Extracts events from requests
│   ├── duplicate_checker.py       # Checks for duplicate tag firing
│   ├── industry_validator.py      # Validates against industry standards
│   └── interaction_engine.py      # Simulates user interactions
├── utils/
│   └── constants.py               # B2B / B2C event constants
└── templates/
    ├── index.html
    └── report.html
```

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Playwright browser

```bash
python -m playwright install chromium
```

### 3. Run the agent

```bash
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### 4. Open in browser

```
http://localhost:8001
```

## Usage

1. Enter a website URL (e.g. `https://example.com`)
2. Select industry type: **B2B** or **B2C**
3. Click **Run Audit**
4. View the dashboard showing detected tags, events, missing events, duplicates, and user journey
5. Click **Download PDF Report** to save the full audit report

## Requirements

- Python 3.11+
- Chromium (installed via Playwright)

## Dependencies

| Package | Purpose |
|---|---|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `playwright` | Browser automation |
| `beautifulsoup4` | HTML parsing for tag detection |
| `reportlab` | PDF report generation |
