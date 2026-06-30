# Competitor Ads Intelligence Agent

A multi-platform competitor ad intelligence tool that scrapes and analyzes ads from **Meta Ads Library**, **Google Ads Transparency Center**, and **LinkedIn** (via screenshot OCR). Built with LangGraph, LangChain, Selenium, and Streamlit.

---

## Features

| Feature | Description |
|---|---|
| **Meta Ads scraping** | Scrapes the Meta Ads Library using Selenium browser automation |
| **Google Ads scraping** | Pulls Google Ads Transparency data via Apify API |
| **LinkedIn Ads (OCR)** | Extracts ad data from uploaded LinkedIn screenshots using an LLM |
| **LangGraph workflow** | Deterministic multi-step graph: open → collect → analyze → export |
| **Streamlit UI** | Clean, glassmorphism-styled dashboard with sidebar controls |
| **Export** | Download results as JSON or CSV |

---

## Architecture

```
competitor_insight/
├── meta_ads_intelligence_agent/
│   ├── streamlit_app.py        # Main Streamlit UI
│   ├── main.py                 # FastAPI REST endpoints (optional)
│   ├── graph.py                # LangGraph workflow definition
│   ├── llm_extract.py          # LLM-based ad extraction logic
│   ├── schemas.py              # Pydantic data models
│   ├── utils.py                # Shared utilities
│   ├── scrapers/
│   │   ├── meta_scraper.py     # Selenium scraper — Meta Ads Library
│   │   ├── google_scraper.py   # Apify-based Google Ads scraper
│   │   └── linkedin_scraper.py # OCR scraper for LinkedIn screenshots
│   ├── requirements.txt
│   └── .env.example            # Template for required environment variables
└── README.md
```

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/NayanaYogesh19/NAYANA-Agents.git
cd NAYANA-Agents
git checkout competitor_insight
cd meta_ads_intelligence_agent
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright browsers (for Meta scraping)

```bash
playwright install chromium
```

### 5. Configure API keys

Create a `.env` file inside `meta_ads_intelligence_agent/` — **never commit this file**:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
APIFY_TOKEN=your_apify_token_here
```

> **Where to get keys:**
> - `OPENROUTER_API_KEY` — [openrouter.ai](https://openrouter.ai/)
> - `APIFY_TOKEN` — [apify.com](https://apify.com/)

---

## Running the Streamlit App

```bash
cd meta_ads_intelligence_agent
streamlit run streamlit_app.py
```

The app opens at `http://localhost:8501`.

### Usage

1. Select a platform from the sidebar: **Meta Ads**, **Google Ads**, or **LinkedIn Ads**
2. For Meta / Google — paste the Ads Library URL
3. For LinkedIn — upload one or more ad screenshots (PNG/JPG)
4. Set **Max Ads** with the slider
5. Click **Analyze Ads**
6. Download results as JSON or CSV

---

## Running the FastAPI Server (optional)

```bash
cd meta_ads_intelligence_agent
uvicorn main:app --reload
```

Endpoints:

| Method | Path | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/meta-ads` | Scrape Meta Ads Library |
| POST | `/google-ads` | Scrape Google Ads Transparency |
| POST | `/linkedin-ads` | Extract ads from uploaded screenshot |

---

## LangGraph Workflow

```
open_library_node  →  collect_ads_node  →  summarize_node  →  END
```

| Node | Action |
|---|---|
| `open_library_node` | Opens the Meta Ads Library in a browser |
| `collect_ads_node` | Scrolls and collects raw ad cards |
| `summarize_node` | Sends raw ads to LLM for structured extraction |

---

## Supported Platforms

| Platform | Method | Key Required |
|---|---|---|
| Meta Ads Library | Selenium browser automation | None |
| Google Ads Transparency | Apify API | `APIFY_TOKEN` |
| LinkedIn Ads | Screenshot OCR via LLM | `OPENROUTER_API_KEY` |

---

## Security Notes

- `.env` is listed in `.gitignore` and will **never** be committed
- No API keys are hardcoded anywhere in the source code
- Copy `.env.example` and fill in your own keys — do not share the resulting `.env` file

---

## Tech Stack

- [LangGraph](https://github.com/langchain-ai/langgraph) — agent workflow orchestration
- [LangChain](https://github.com/langchain-ai/langchain) — LLM chaining and structured extraction
- [Streamlit](https://streamlit.io/) — interactive web UI
- [Selenium](https://selenium-python.readthedocs.io/) — browser automation
- [Playwright](https://playwright.dev/python/) — headless browser (Meta scraping)
- [Apify](https://apify.com/) — Google Ads data API
- [Pydantic](https://docs.pydantic.dev/) — data validation and schemas
- [FastAPI](https://fastapi.tiangolo.com/) — optional REST API layer

---

## License

MIT
