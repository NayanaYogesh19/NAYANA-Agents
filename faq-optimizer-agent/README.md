# FAQ Optimizer Agent

An AI-powered FAQ generation agent that scrapes a website and produces SEO, GEO, and AEO optimized FAQ content using LLMs via OpenRouter.

---

## Features

- **Website Scraping** — Extracts content from any public website
- **Topic Generation** — Auto-generates product and application topics from scraped content
- **Question Generation** — Produces 20 buyer-intent questions per topic (SEO / GEO / AEO)
- **Answer Generation** — Generates concise, factual, website-specific answers
- **Duplicate Detection** — Filters semantically duplicate questions before returning results
- **Admin Dashboard** — View saved FAQs, websites, and analytics
- **Supabase Storage** — All generated FAQs are persisted to a Supabase database
- **LangSmith Tracing** — Optional LLM call tracing via LangChain

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| LLM | OpenRouter (`openai/gpt-4o-mini`) |
| Database | Supabase (PostgreSQL) |
| Scraper | Requests + BeautifulSoup |
| Tracing | LangSmith / LangChain |
| Frontend | Vanilla HTML + CSS + JS |

---

## Project Structure

```
faq-optimizer-agent/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings loaded from .env
│   ├── models.py                # Pydantic request/response models
│   ├── routes/
│   │   ├── questions.py         # POST /api/generate-questions
│   │   ├── answers.py           # POST /api/generate-answers
│   │   ├── topics.py            # POST /api/generate-topics
│   │   └── admin.py             # Admin login, websites, analytics
│   ├── services/
│   │   ├── llm_service.py       # OpenRouter LLM calls
│   │   ├── scraper.py           # Website scraper
│   │   └── duplicate_checker.py # Semantic duplicate filter
│   └── database/
│       ├── supabase_client.py   # Supabase connection
│       ├── faq_repository.py    # FAQ CRUD
│       ├── website_repository.py
│       └── analytics_repository.py
├── frontend/
│   ├── index.html               # Main UI
│   ├── admin.html               # Admin dashboard
│   ├── styles.css
│   └── scripts/app.js
├── database/
│   └── schema.sql               # Supabase table definitions
├── logs/                        # Runtime logs (git-ignored)
├── .env                         # API keys (git-ignored)
├── .gitignore
└── requirements.txt
```

---

## Setup

### 1. Clone and navigate
```bash
cd faq-optimizer-agent
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
LANGCHAIN_API_KEY=your-langsmith-key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=faq-optimizer-agent
ADMIN_PASSWORD=your-admin-password
```

> Get a free OpenRouter key at https://openrouter.ai/keys

### 4. Set up Supabase database

Run the SQL in `database/schema.sql` in your Supabase SQL editor.

### 5. Start the server
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8001
```

---

## Usage

| URL | Description |
|---|---|
| `http://localhost:8001` | Main UI |
| `http://localhost:8001/admin` | Admin dashboard |
| `http://localhost:8001/docs` | Swagger API docs |
| `http://localhost:8001/health` | Health check |

### API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/generate-topics` | Generate FAQ topics from a website |
| POST | `/api/generate-questions` | Generate questions for a topic |
| POST | `/api/generate-answers` | Generate answers for questions |
| POST | `/api/admin/login` | Admin authentication |
| GET | `/api/admin/websites` | List all scraped websites |
| GET | `/api/admin/faqs/{website_url}` | Get FAQs for a website |
| GET | `/api/admin/analytics` | View usage analytics |

---

## FAQ Generation Flow

```
Website URL
    ↓
Scrape website content (BeautifulSoup)
    ↓
Extract structured business context (LLM)
    ↓
Generate product + application topics (LLM)
    ↓
Generate 20 questions per topic — SEO / GEO / AEO (LLM)
    ↓
Filter semantic duplicates
    ↓
Generate concise answers (LLM)
    ↓
Save to Supabase
```

---

## Notes

- `.env` is git-ignored — never commit API keys
- Logs are written to `logs/app.log` (git-ignored)
- Some websites block scrapers (Cloudflare, bot protection) — this is expected
- OpenRouter free tier has monthly limits; replace the key if you hit a 403
