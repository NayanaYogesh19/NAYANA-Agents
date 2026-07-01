# Dynamic SEO Keyword Research Agent (Rebuild)

A FastAPI web app that generates an SEO keyword research report for a website
and its competitors. Given a main website URL and a comma-separated list of
competitor URLs, it discovers and crawls each site's sitemap, pulls related
keyword data and metrics from the SE Ranking API, matches keywords against
competitor products, and exports the results as a downloadable Excel report.

## Features

- Sitemap discovery and crawling for the main website and competitors
- Related keyword lookup and category inference via SE Ranking
- Bulk keyword metrics (volume, KD score/level, intent, CPC, competition,
  trend, SERP features)
- Competitor product/keyword matching
- Excel export of the final keyword research report

## Project Structure

```
seo_keyword_research_rebuild/
├── app/
│   ├── main.py                  # FastAPI app and routes (active entry point)
│   ├── new_main.py              # WIP rebuild entry point
│   ├── services/
│   │   ├── sitemap_discovery.py
│   │   ├── sitemap_crawler.py
│   │   ├── sitemap_parser.py
│   │   ├── se_ranking_keyword_service.py
│   │   ├── se_ranking_bulk_service.py
│   │   ├── competitor_matcher.py
│   │   ├── excel_export_service.py
│   │   ├── product_classifier.py
│   │   ├── new_se_ranking_service.py
│   │   ├── new_sitemap_service.py
│   │   └── new_excel_service.py
│   ├── static/                  # CSS assets
│   └── templates/                # Jinja2 HTML templates
├── reports/                      # Generated Excel reports
├── requirements.txt
└── .env                          # SE_RANKING_API_KEY (not committed)
```

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # Windows PowerShell
   .\venv\Scripts\Activate.ps1
   # Git Bash
   source venv/Scripts/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in this directory with your SE Ranking API key:

   ```
   SE_RANKING_API_KEY=your_api_key_here
   ```

## Running the Agent

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Usage

1. Open the app in your browser.
2. Enter the main website URL and a comma-separated list of competitor URLs.
3. Submit the form to trigger `/generate-report`.
4. The app crawls sitemaps, fetches keyword data, matches competitor
   products, and returns an Excel file (`SEO_keyword_research.xlsx`) for
   download.
