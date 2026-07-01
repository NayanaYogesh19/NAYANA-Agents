# Website Audit Strategy Agent

An automated pipeline that crawls a target website and a competitor, runs multi-dimensional analysis (Performance, Technical SEO, On-Page SEO, Content, UX), and uses Claude (via OpenRouter) to synthesise the findings into an actionable strategy report — delivered as a PDF.

## Features

- **Web Crawling** — up to 50 pages per domain (requests + BeautifulSoup), robots.txt respected
- **Performance** — Google PageSpeed Insights API v5 (mobile), Core Web Vitals
- **Technical SEO** — HTTPS/SSL, robots.txt, sitemap, canonical tags, structured data, duplicate titles/meta descriptions
- **On-Page SEO** — title/meta coverage, H1 health, image alt coverage, orphan page detection
- **Content Analysis** — word count, readability, duplicate content detection, Keep/Update/Merge/Delete action classification
- **UX & Accessibility** — trust signals, CTA detection, ARIA landmarks, mobile tap targets, PageSpeed accessibility
- **AI Synthesis** — executive summary, strengths/weaknesses, quick wins, strategic recommendations, and a phased roadmap, generated dynamically per audit run
- **PDF Report Generation** — full report with scoring breakdown and methodology appendix
- **FastAPI backend + simple web frontend** for running audits from the browser

## Project Structure

```
website_audit_agent/
├── agents/              # Crawler, analysis, scoring, and AI synthesis modules
├── frontend/            # Static HTML/CSS/JS UI
├── report/              # PDF generation
├── output/              # Generated audit PDFs (gitignored)
├── main.py              # CLI entry point
├── api.py               # FastAPI server
├── config.py            # Central config, loaded from .env
└── requirements.txt
```

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   playwright install
   ```

2. Copy the example environment file and fill in your own keys:
   ```
   cp .env.example .env
   ```

3. Configure `.env`:
   ```
   PAGESPEED_API_KEY=your_google_pagespeed_api_key
   OPENROUTER_API_KEY=your_openrouter_api_key   # starts with sk-or-v1-
   OPENROUTER_MODEL=openai/gpt-4o-mini          # or any model available on OpenRouter

   # Optional overrides (defaults shown)
   CRAWL_MAX_PAGES=50
   CRAWL_DELAY_SECONDS=1.0
   CRAWL_TIMEOUT=10
   PLAYWRIGHT_TIMEOUT=30000
   REPORT_OUTPUT_DIR=./output
   ```

   **Never commit your real `.env` file** — it holds live API keys. `.env` is gitignored; only `.env.example` (no real secrets) should be committed.

## Usage

### CLI

```
python main.py --target https://example.com --competitor https://rival.com
```

The generated PDF is written to `output/` and its path is printed to stdout.

### Web UI

```
python -m uvicorn api:app --reload
```

Then open `http://127.0.0.1:8000` in a browser, enter a target and competitor URL, and download the generated report.

## Notes

- If `OPENROUTER_API_KEY` is missing or invalid, the AI synthesis sections (executive summary, quick wins, strategic recommendations, roadmap) will show "No data returned" — all crawl-based scoring (Performance, Technical SEO, On-Page SEO, Content, UX) still runs and is unaffected.
- PageSpeed accessibility/best-practices/SEO categories can show `N/A` when Lighthouse can't fully render a page (bot detection, JS errors, API rate limits) — the Performance score itself is unaffected and always accurate.
