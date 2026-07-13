# DM Audit Agent (LangChain + FastAPI)

Generates a client-ready Digital Marketing Audit **PDF** for any company/website,
covering any combination of SEO / Performance Marketing (PPC) / Social Media (SMM),
with no SE Ranking (or any other paid SEO API) dependency — SEO/PPC/SMM
metrics are entered manually by the user.

## Category selection & slide structure

The user picks **any combination** of three categories on the initial screen —
SEO, Performance Marketing (PPC), Social Media (SMM). The report is built
dynamically from that selection, matching the reference "Digital Marketing
Audit Report" template exactly:

1. **Title** — always 1 slide.
2. **Key Metrics Overview** — one slide **per selected category** (e.g. all
   three selected → 3 metrics slides, one each for SEO/PPC/SMM).
3. **Current Digital State** — one slide **per selected category**.
4. **Visibility Gap** — one slide **per selected category**.
5. **Industry Best Practices** — one combined slide; content adapts to span
   whichever categories are selected.
6. **Competitive Benchmark Analysis** — one combined slide (two tables:
   client performance + industry comparison), with Strategic Takeaways
   folded into the same slide **unless all three categories are selected**,
   in which case Strategic Takeaways becomes its own slide.
7. **Growth Recommendations** — one combined slide (Search & Technical
   Optimization + Brand Authority & Engagement), adapted to draw from every
   selected category.
8. **Summary & Next Steps** — one combined slide summarizing everything above.
9. **Contact** — always 1 slide.

**A single selected category always produces exactly 9 slides.** Selecting
all three categories always produces exactly **16 slides** (9 + 6 extra from
the tripled Metrics/Current State/Visibility Gap slides + 1 extra from the
split-out Strategic Takeaways slide).

Any toggleable slide (Industry Best Practices, Benchmark Analysis, Strategic
Takeaways, Current Digital State, Visibility Gap) can be individually
excluded per run — the report regenerates cleanly without it. Title, Key
Metrics, Growth Recommendations, Summary & Next Steps, and Contact are always
included.

Investment/pricing, monthly retainer, and Terms & Conditions content are
permanently excluded from every generated report, regardless of selection.

## Pipeline

1. **Category selection + manual metrics** — user picks SEO/PPC/SMM (any
   combination) and types in metrics for each selected category (SEO: Health
   Score, Organic Traffic, Organic Keywords, Passed Checks, Crawled Pages,
   Errors, Warnings, Notices; PPC: Ad Spend, Impressions, Clicks, CTR, CPC,
   Conversions, Conversion Rate, ROAS; SMM: LinkedIn Followers, Posts/Month,
   Engagement Rate). None of these are fetched from any external SEO API.
2. **Keyword Research agent** (Tavily + website parser) — builds a grounded
   research brief: real site content, named competitors, market context.
3. **SEO Audit agent** (PageSpeed Insights + Tavily + parser + manual SEO
   metrics) — writes a unique technical/content narrative. Only runs if SEO
   is selected.
4. **SMM Gap Analysis agent** (Tavily + parser + manual SMM metrics) — writes
   a unique social gap narrative vs named competitors. Only runs if SMM is
   selected.
5. **Strategy agent** — combines SEO + SMM + manual PPC input into a strategy
   narrative.
6. **Content agent** — produces independent content for Current Digital
   State / Visibility Gap **per selected category**, plus one combined,
   category-spanning set of content for Best Practices / Benchmarks /
   Growth Recommendations / Summary & Next Steps. Explicitly instructed to
   never invent numbers and never write generic, interchangeable content.
7. **PDF engine** (ReportLab, pure Python — no native/GTK dependency) renders
   exactly the resolved slides in the fixed visual template matching the
   reference PDF, and serves the file back for download.

## Project structure

```
dm_audit_agent/
├── app.py                     # FastAPI app + orchestration endpoint
├── config.py                  # loads .env
├── templates.py                # category/slide resolution logic
├── metrics_schema.py           # manual-entry metric field definitions (per category)
├── pdf_engine.py                # low-level PDF drawing primitives (cards, KPI tiles, tables, numbered cards, benefit lines)
├── slide_renderers.py           # one render function per slide type (per-category + combined)
├── report_writer.py            # run folders + PDF filename convention
├── agents/
│   ├── llm.py                  # shared OpenRouter ChatOpenAI factory
│   ├── keyword_research_agent.py  # Tavily + parser (no SE Ranking)
│   ├── seo_audit_agent.py         # PageSpeed + Tavily + parser + manual SEO metrics
│   ├── smm_gap_analysis_agent.py  # Tavily + parser + manual SMM metrics
│   ├── strategy_agent.py          # combines SEO+SMM+PPC into a strategy narrative
│   └── content_agent.py           # per-category + combined dynamic content generator
├── tools/
│   ├── tavily_tool.py           # Tavily web search
│   ├── website_parser_tool.py   # website/URL parser
│   └── pagespeed_tool.py        # Google PageSpeed Insights
├── frontend/                    # glassmorphism UI per Design.md
│   ├── index.html               # category select → metrics form → progress → results
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
- `GET  /api/categories` — category metadata, toggleable slide list, and
  manual metric field labels per category, used by the frontend to build the
  UI dynamically.
- `POST /api/dm-audit` — runs the full pipeline and returns a PDF download
  link. Body:
  ```json
  {
    "Company Name": "Acme Robotics",
    "Domain/Website": "https://acmerobotics.com/",
    "Industry": "Industrial Automation",
    "Competitors Names": "FANUC, KUKA, ABB Robotics",
    "Your Email": "you@company.com",
    "Categories": ["seo"],
    "Excluded Sections": [],
    "SEO Metrics": {"health_score": 71, "organic_traffic": 12500, "organic_keywords": 3400, "passed_checks": 88, "crawled_pages": 540, "errors": 120, "warnings": 430, "notices": 900},
    "PPC Metrics": {},
    "SMM Metrics": {}
  }
  ```
  `"Categories"` accepts any combination of `"seo"`, `"ppc"`, `"smm"` (at
  least one is required). Response:
  ```json
  {
    "run_id": "...",
    "company_name": "Acme Robotics",
    "categories": ["seo"],
    "slide_count": 9,
    "included_slides": ["title", "metrics.seo", "current_state.seo", "..."],
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
  permanently excluded from every generated report regardless of category
  selection or toggle choices.
- PDF rendering uses ReportLab (pure Python) rather than WeasyPrint, since
  WeasyPrint requires system-level Pango/Cairo/GObject libraries that are not
  installed on this machine by default — ReportLab guarantees the report
  always generates without native-dependency errors.
