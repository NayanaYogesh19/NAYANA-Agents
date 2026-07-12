# DM Audit Agent (LangChain + FastAPI)

Generates a client-ready Digital Marketing Audit **PDF** for any company/website,
in one of two selectable modes, with no SE Ranking (or any other paid SEO API)
dependency — SEO/PPC/SMM metrics are entered manually by the user.

## Audit modes

- **ONLY SEO** — 9 slides (mirrors the reference `vertiv_digital_audit` deck):
  Title, Key Metrics, Current Digital State, Visibility Gap, Industry Best
  Practices, Competitive Benchmark (SEO), Growth Recommendations, Summary &
  Next Steps, Contact.
- **SEO + Performance Marketing + Social Media Auditing** — 15 slides (mirrors
  the reference `karishye_audit_growth_strategy` deck, minus Investment
  Summary / Tools We Use / Terms & Conditions, which are permanently excluded):
  Title, Key Metrics, Executive Summary, Positioning Audit, Performance
  Marketing Audit, SEO & Technical Audit, Social Media Audit, Conversion
  System Audit, Industry Best Practices, Competitor Benchmarks (SEO / SMM /
  PPC as three separate slides), Strategic Recommendations, KPIs & Targets,
  Contact.

Every optional section can be individually excluded per run (e.g. dropping
"Conversion System Audit") — the report regenerates cleanly without it. A
few sections (Title, Key Metrics, Growth/Strategy summary, Contact) are
always included since they're required in every report.

## Pipeline

1. **Mode + manual metrics** — user selects a mode and types in SEO metrics
   (Health Score, Organic Traffic, Organic Keywords, Passed Checks, Crawled
   Pages, Errors, Warnings, Notices) and, in full mode, Performance Marketing
   (Ad Spend, Impressions, Clicks, CTR, CPC, Conversions, Conversion Rate,
   ROAS) and Social Media (LinkedIn Followers, Posts/Month, Engagement Rate)
   metrics. None of these are fetched from any external SEO API.
2. **Keyword Research agent** (Tavily + website parser) — builds a grounded
   research brief: real site content, named competitors, market context.
3. **SEO Audit agent** (PageSpeed Insights + Tavily + parser + the manual SEO
   metrics) — writes a unique technical/content narrative.
4. **SMM Gap Analysis agent** (Tavily + parser + manual SMM metrics, full mode
   only) — writes a unique social gap narrative vs named competitors.
5. **Strategy agent** — combines SEO + SMM + manual PPC input into a strategy
   narrative.
6. **Content agent** — produces per-section JSON text (only for the sections
   actually requested) plus benchmark/KPI table data. Explicitly instructed
   to never invent numbers and never write generic, interchangeable content —
   every section must read as specific to this company.
7. **PDF engine** (ReportLab, pure Python — no native/GTK dependency) renders
   exactly the requested slides in the fixed visual template matching the
   reference PDFs, and serves the file back for download.

## Project structure

```
dm_audit_agent/
├── app.py                     # FastAPI app + orchestration endpoint
├── config.py                  # loads .env
├── templates.py                # section/slide definitions for both modes
├── metrics_schema.py           # manual-entry metric field definitions
├── pdf_engine.py                # low-level PDF drawing primitives (cards, KPI tiles, tables)
├── slide_renderers.py           # one render function per section slug
├── report_writer.py            # run folders + PDF filename convention
├── agents/
│   ├── llm.py                  # shared OpenRouter ChatOpenAI factory
│   ├── keyword_research_agent.py  # Tavily + parser (no SE Ranking)
│   ├── seo_audit_agent.py         # PageSpeed + Tavily + parser + manual SEO metrics
│   ├── smm_gap_analysis_agent.py  # Tavily + parser + manual SMM metrics
│   ├── strategy_agent.py          # combines SEO+SMM+PPC into a strategy narrative
│   └── content_agent.py           # dynamic per-section JSON content generator
├── tools/
│   ├── tavily_tool.py           # Tavily web search
│   ├── website_parser_tool.py   # website/URL parser
│   └── pagespeed_tool.py        # Google PageSpeed Insights
├── frontend/                    # glassmorphism UI per Design.md
│   ├── index.html               # mode select → metrics form → progress → results
│   ├── style.css
│   └── scripts.js
├── reports/                     # generated PDFs (per run)
├── requirements.txt
└── .env
```

## Setup

```bash
cd "C:\Agents\NAYANA-Agents\dm_audit_agent"
python -m venv venv
./venv/Scripts/pip install -r requirements.txt
```

Fill in `.env`:

```
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
TAVILY_API_KEY=...
PAGESPEED_API_KEY=...
APP_HOST=0.0.0.0
APP_PORT=8010
```

## Run

```bash
cd "C:\Agents\NAYANA-Agents\dm_audit_agent"
./venv/Scripts/python.exe -m uvicorn app:app --host 0.0.0.0 --port 8010
```

Then open **http://localhost:8010** — this serves the frontend directly from
the FastAPI app.

## API

- `GET  /api/health` — health check
- `GET  /api/modes` — mode metadata (slide counts, toggleable sections) and
  manual metric field labels, used by the frontend to build the UI
  dynamically.
- `POST /api/dm-audit` — runs the full pipeline and returns a PDF download
  link. Body:
  ```json
  {
    "Company Name": "Acme Robotics",
    "Domain/Website": "https://acmerobotics.com/",
    "Industry": "Industrial Automation",
    "Competitors Names": "FANUC, KUKA, ABB Robotics",
    "Your Email": "you@company.com",
    "Audit Mode": "seo",
    "Excluded Sections": [],
    "SEO Metrics": {"health_score": 71, "organic_traffic": 12500, "organic_keywords": 3400, "passed_checks": 88, "crawled_pages": 540, "errors": 120, "warnings": 430, "notices": 900},
    "PPC Metrics": {},
    "SMM Metrics": {}
  }
  ```
  Response:
  ```json
  {
    "run_id": "...",
    "company_name": "Acme Robotics",
    "audit_mode": "seo",
    "included_sections": ["title", "metrics", "..."],
    "pdf_filename": "Acme Robotics Audit Report.pdf",
    "download_url": "/api/reports/{run_id}/{filename}"
  }
  ```
- `GET  /api/reports/{run_id}/{filename}` — download the generated PDF.

## Notes

- SE Ranking has been removed entirely from this project — there is no paid
  SEO API dependency anywhere in the pipeline. All SEO/PPC/SMM numbers are
  entered manually by the user in the UI and used as ground truth.
- Investment/pricing, monthly retainer, and Terms & Conditions content are
  permanently excluded from every generated report regardless of mode or
  toggle selection.
- PDF rendering uses ReportLab (pure Python) rather than WeasyPrint, since
  WeasyPrint requires system-level Pango/Cairo/GObject libraries that are not
  installed on this machine by default — ReportLab guarantees the report
  always generates without native-dependency errors.
