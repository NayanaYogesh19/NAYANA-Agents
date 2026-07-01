# Onpage SEO Agent

A FastAPI + LangChain agent that crawls a website's product pages, pulls real keyword metrics from SE Ranking, and uses an LLM (via OpenRouter) to generate on-page SEO recommendations — titles, meta descriptions, headings, FAQs, image alt text, and internal linking ideas. Results are shown in a web UI and exported to an Excel workbook.

## Features

- Discovers product page URLs from a site's sitemap(s)
- Scrapes each matched page for existing SEO metadata (title, meta description, H1, images, internal links, schema)
- Extracts and normalizes a primary keyword per page
- Fetches keyword volume, competition, CPC, difficulty, and current ranking from SE Ranking
- Generates AI-powered SEO suggestions (title, meta, headings, FAQs, featured snippet, alt text, internal linking) via OpenRouter
- Exports all results to an Excel report (`output/seo_report.xlsx`)
- Simple web UI to run the agent and browse results per product

## Project Structure

```
Onpage_SEO/
├── app.py                     # FastAPI app: routes for UI, analyze, and Excel download
├── agents/
│   └── seo_optimizer.py       # Orchestrates the end-to-end pipeline
├── tools/
│   ├── sitemap_tool.py        # Sitemap discovery/parsing
│   ├── scraper_tool.py        # Page scraping
│   ├── keyword_extractor.py   # Keyword extraction from page content
│   ├── keyword_mapper.py      # Keyword normalization
│   ├── seranking_tool.py      # SE Ranking API integration
│   ├── seo_ai_generator.py    # LLM-based SEO content generation
│   └── excel_exporter.py      # Excel report generation
├── data/
│   └── product_master.py      # Product slug → name mapping used to filter target pages
├── prompts/
│   └── seo_prompt.py          # Prompt templates for the LLM
├── static/
│   └── index.html             # Web UI
└── output/                    # Generated Excel reports (gitignored)
```

## Setup

```bash
cd Onpage_SEO
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Create a `.env` file in this directory with:

```
OPENROUTER_API_KEY=your_openrouter_api_key
OPENROUTER_MODEL=openai/gpt-4o-mini
SERANKING_API_KEY=your_seranking_api_key
SERPAPI_KEY=your_serpapi_key
```

`.env` is gitignored and should never be committed.

## Run

```bash
uvicorn app:app --reload
```

If port 8000 is already in use:

```bash
uvicorn app:app --reload --port 8001
```

Open the UI at `http://127.0.0.1:8000/` (or your chosen port).

## API

**POST** `/analyze`

```json
{
  "website_url": "https://example.com",
  "company_name": "Example Inc",
  "max_pages": 5
}
```

Returns per-page SEO analysis plus a generated Excel file path.

**GET** `/download-excel`

Downloads the most recently generated `seo_report.xlsx`.
