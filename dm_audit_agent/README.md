# DM Audit Agent (LangChain + FastAPI)

Generates a client-ready Digital Marketing Audit **PDF** for any company/website,
covering any combination of SEO / Performance Marketing (PPC) / Social Media (SMM).

The primary flow is a **phased, per-category review**: the user reviews and can
edit each selected category's analysis on-screen (SEO → PPC → SMM, in that
fixed order) before the final combined PDF is generated. A legacy single-shot
endpoint (`/api/dm-audit`) is also kept, unmodified, for backwards
compatibility.

## Category selection & slide structure

The user picks **any combination** of three categories on the initial screen —
SEO, Performance Marketing (PPC), Social Media (SMM). The report is built
dynamically from that selection, matching the reference "Digital Marketing
Audit Report" template:

1. **Title** — always 1 slide.
2. **Key Metrics Overview** — one slide **per selected category**, except PPC
   (PPC has no numeric-metrics slide — see below).
3. **Current Digital State** — one slide **per selected category**, with
   category-specific quadrant headings (e.g. PPC → "Ad Presence Overview" /
   "Ad Format & Platform Gaps" / "Ad Creative Gaps"; SMM → "Social Presence
   Overview" / "Platform Coverage Gaps" / "Content & Engagement Gaps").
4. **Visibility Gap** — one slide **per selected category**.
5. **Industry Best Practices** — one combined slide across selected categories.
6. **Competitive Benchmark Analysis** — one combined slide (client performance
   + industry comparison tables), with Strategic Takeaways folded into the
   same slide unless all three categories are selected, in which case
   Strategic Takeaways becomes its own slide.
7. **Growth Recommendations** — one combined slide, drawing from every
   selected category.
8. **Summary & Next Steps** — one combined slide summarizing everything above.
9. **Contact** — always 1 slide.

A single selected category produces 9 slides (8 if that category is PPC,
since PPC has no Key Metrics slide). Selecting all three produces 16 slides.

Any toggleable slide (Industry Best Practices, Benchmark Analysis, Strategic
Takeaways, Current Digital State, Visibility Gap) can be individually
excluded per run. Title, Key Metrics, Growth Recommendations, Summary & Next
Steps, and Contact are always included. Investment/pricing, monthly
retainer, and Terms & Conditions content are permanently excluded from every
generated report.

All slide/card layouts auto-fit font size and card height to the actual
content generated for that run — sparse sections render with larger text and
no dead card space instead of a fixed small font assuming worst-case density.
The content-generation prompt is also under an absolute rule: it must never
write "Data not available" or any other placeholder/absence phrase anywhere
— if a sub-section has no genuinely supported point, it's simply omitted
rather than padded with filler.

## Pipeline (phased flow)

1. **`POST /api/dm-audit/start`** — company info (name, domain, industry,
   competitors, email) + selected categories. Runs Keyword Research
   (Tavily + website parser) once, creates an in-memory run (6-hour TTL).
2. **`POST /api/dm-audit/{run_id}/category/seo`** — user enters SEO metrics
   (Health Score, Organic Traffic, Organic Keywords, Passed Checks, Crawled
   Pages, Errors, Warnings, Notices); runs the SEO Audit agent
   (PageSpeed Insights + Tavily + parser) and returns the narrative for
   on-screen review/edit.
3. **`POST /api/dm-audit/{run_id}/category/ppc`** — user enters ad-transparency
   URLs only (Google Ads Transparency Center URL, Meta Ads Library URL,
   LinkedIn advertiser/company name — LinkedIn's ad library has no stable
   per-advertiser URL). Real ad data (headline, description, platform,
   status, dates, Library ID) is scraped via Apify actors:
   - Google: `lexis-solutions/google-ads-scraper`
   - Meta: `apify/facebook-ads-scraper`
   - LinkedIn: `xtech/linkedin-adlibrary-scraper`

   No numeric PPC metrics are manually entered — the LLM derives reasonable
   PPC metrics/analysis directly from the real scraped ad data. For ads whose
   creative text isn't present in the scraper's structured data (common for
   Google Ads Transparency Center "TEXT"-format ads, where the copy only
   exists baked into the ad's rendered preview image), a vision step reads
   the literal headline/description off that image using the same shared
   vision-capable LLM — never inventing text; if nothing legible is found,
   that field is simply omitted.
4. **`POST /api/dm-audit/{run_id}/category/smm`** — user enters direct
   profile URLs (Instagram, Facebook, LinkedIn, YouTube); profiles are
   scraped via Apify, and the SMM Gap Analysis agent writes a per-platform
   narrative (all four platforms, not just LinkedIn) benchmarked against
   named competitors via Tavily/parser research.
5. **`POST /api/dm-audit/{run_id}/category/{category}/narrative`** — edit any
   category's reviewed narrative/ad-data summary; the edited text replaces
   what feeds the final report for that category.
6. **`GET /api/dm-audit/{run_id}/finalize-options`** — toggleable slide list
   for the finalize step.
7. **`POST /api/dm-audit/{run_id}/finalize`** — runs the Strategy agent, then
   the Content Generation agent (produces per-category content plus one
   combined, category-spanning set of content for Best Practices /
   Benchmarks / Growth Recommendations / Summary & Next Steps), then renders
   the PDF and returns a download link.

Category order (SEO → PPC → SMM) is enforced server-side — reviewing a
category out of order returns `409`. Failed category calls can be retried
without losing already-reviewed categories.

## Project structure

```
dm_audit_agent/
├── app.py                        # FastAPI app: phased-flow + legacy endpoints
├── config.py                     # loads .env
├── templates.py                  # category/slide resolution logic
├── metrics_schema.py              # SEO/PPC/SMM metric field definitions + validation models
├── pdf_engine.py                  # low-level PDF drawing primitives (cards, KPI tiles, tables, auto-fit sizing)
├── slide_renderers.py             # one render function per slide type (per-category + combined)
├── report_writer.py               # run folders + PDF filename convention
├── agents/
│   ├── llm.py                        # shared OpenRouter ChatOpenAI factory (vision-capable)
│   ├── keyword_research_agent.py     # Tavily + parser
│   ├── seo_audit_agent.py            # PageSpeed + Tavily + parser + manual SEO metrics
│   ├── ppc_metrics_agent.py          # orchestrates Google/Meta/LinkedIn ad scraping + vision text extraction
│   ├── smm_metrics_agent.py          # Instagram/Facebook/LinkedIn/YouTube profile scraping
│   ├── smm_gap_analysis_agent.py     # 4-platform SMM narrative vs named competitors
│   ├── strategy_agent.py             # combines SEO+PPC+SMM into a strategy narrative
│   └── content_agent.py              # per-category + combined dynamic content generator
├── tools/
│   ├── tavily_tool.py             # Tavily web search
│   ├── website_parser_tool.py     # website/URL parser
│   ├── pagespeed_tool.py          # Google PageSpeed Insights
│   ├── smm_scrapers/              # Instagram/Facebook/LinkedIn/YouTube profile scrapers (Apify)
│   └── ppc_scrapers/              # Google/Meta/LinkedIn ad-transparency scrapers (Apify)
│       ├── google_ads_scraper.py
│       ├── meta_ads_scraper.py
│       └── linkedin_ads_scraper.py
├── frontend/                       # phased-flow UI: category review → edit → finalize
│   ├── index.html
│   ├── style.css
│   └── scripts.js
├── reports/                        # generated PDFs (per run)
├── requirements.txt
└── .env                             # not committed — see Setup below
```

## Setup

```bash
cd "C:\Agents\NAYANA-Agents\dm_audit_agent"
python -m venv venv
./venv/Scripts/pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your own keys — `.env` is
git-ignored and never committed:

```
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
TAVILY_API_KEY=your_tavily_key_here
PAGESPEED_API_KEY=your_pagespeed_key_here
APIFY_API_TOKEN=your_apify_token_here
APP_HOST=0.0.0.0
APP_PORT=8010
```

`APIFY_API_TOKEN` powers both the SMM profile scrapers and the PPC
ad-transparency scrapers (Google/Meta/LinkedIn) — one shared token.

## Run

```bash
cd "C:\Agents\NAYANA-Agents\dm_audit_agent"
./venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8010
```

Then open **http://localhost:8010** — this serves the frontend directly from
the FastAPI app.

## API

- `GET  /api/health` — health check.
- `GET  /api/categories` — category metadata, toggleable slide list, and
  metric field labels per category.
- `POST /api/dm-audit/start` — begin a phased run. See Pipeline above.
- `POST /api/dm-audit/{run_id}/category/{category}` — submit that category's
  inputs and receive its reviewed narrative/ad-data summary.
- `POST /api/dm-audit/{run_id}/category/{category}/narrative` — edit a
  category's reviewed text before finalizing.
- `GET  /api/dm-audit/{run_id}/finalize-options` — toggleable slides for this run.
- `POST /api/dm-audit/{run_id}/finalize` — generate the final PDF.
- `POST /api/dm-audit` — **legacy** single-shot endpoint, unchanged: takes all
  inputs (including numeric SEO/PPC/SMM metrics) in one call and returns a
  PDF download link directly. Kept for backwards compatibility; not used by
  the current frontend.
- `GET  /api/reports/{run_id}/{filename}` — download the generated PDF.

## Notes

- No paid SEO API (e.g. SE Ranking) is used anywhere in the pipeline.
- Ad-transparency and social-profile data are fetched live via Apify actors;
  numeric PPC metrics are LLM-derived from that real scraped data rather than
  manually entered.
- Placeholder/absence phrases (e.g. "Data not available") are banned by
  design — both in the content-generation prompt and, where LLM prompting
  alone proved unreliable (e.g. dropping all-blank competitor rows in the SMM
  narrative), enforced deterministically in code as a post-processing step.
- PDF rendering uses ReportLab (pure Python) rather than WeasyPrint, since
  WeasyPrint requires system-level Pango/Cairo/GObject libraries not
  installed on this machine by default.
