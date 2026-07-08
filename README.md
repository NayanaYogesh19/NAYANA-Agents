# InGovern Governance Agent

AI-powered proxy advisory agent for AGM, EGM, and Postal Ballot notices. Parses corporate governance notices (PDF), extracts resolutions and board/director details, and produces InGovern-style governance commentary with RAG-backed precedent search, policy review, and downloadable PDF reports.

## Features

- **PDF ingestion** — upload AGM/EGM/Postal Ballot notice PDFs (`/upload_notice`)
- **Metadata & board extraction** — company name, meeting date/venue, ISIN, e-voting details, board composition
- **Resolution extraction** — dynamically parses agenda items (ordinary/special business) from any notice format: explicit "Item No." headers, InGovern-report style, or plain numbered lists
- **AI governance commentary** — RAG-backed analysis using Supabase pgvector for historical precedent search and writing-style learning
- **Policy review** — cross-checks resolutions against governance policy knowledge base
- **PDF report generation** — downloadable, InGovern-formatted governance reports

## Tech Stack

- **Backend:** FastAPI (Python), Uvicorn
- **PDF processing:** pdfplumber, pypdf
- **AI:** OpenRouter (LLM), Supabase pgvector (embeddings/RAG)
- **Database:** Supabase
- **Reports:** ReportLab, Jinja2
- **Frontend:** Static HTML/CSS/JS (served from `/static`)

## Project Structure

```
api/                    FastAPI routers (upload, analyze, review, report, notice, board, commentary, knowledge, full_report)
config/                 App configuration & storage path settings
database/               Supabase client, RAG store, resolution persistence
pdf_processing/         PDF text/metadata/board extraction
policy_retrieval/       Governance policy knowledge base lookup
precedent_retrieval/    Historical resolution precedent search
prompts/                LLM prompt templates
recommendation_engine/  InGovern commentary generation logic
report_generator/       PDF/HTML report rendering
resolution_extractor/   Dynamic resolution/agenda-item parser
scripts/                Knowledge base seeding utilities
static/                 Frontend (HTML/CSS/JS)
templates/              Jinja2 report templates
app.py                  FastAPI app entrypoint (router registration)
run.py                  Uvicorn launcher
```

## Setup

1. **Clone and create a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   Copy `.env.example` to `.env` and fill in your credentials:
   ```bash
   cp .env.example .env
   ```

   | Variable | Description |
   |---|---|
   | `OPENROUTER_API_KEY` | API key for OpenRouter (LLM access) |
   | `OPENROUTER_MODEL` | Model identifier (e.g. `openai/gpt-4o-mini`) |
   | `SUPABASE_URL` | Supabase project URL |
   | `SUPABASE_KEY` | Supabase anon/public key |
   | `SUPABASE_SERVICE_KEY` | Supabase service_role key (bypasses RLS — server-side only) |
   | `REPORT_STORAGE` | Local storage path for generated reports (default: `storage`) |

   > **Never commit `.env`.** It is already excluded via `.gitignore`.

4. **Run the app**
   ```bash
   python run.py
   ```
   The app will be available at `http://localhost:8000` (interactive docs at `/docs`).

## Deployment

- **Railway:** `Procfile` included (`web: uvicorn app:app --host 0.0.0.0 --port $PORT`)
- **Vercel:** `vercel.json` included for serverless deployment

## Security Notes

- `.env`, credentials, service account keys, and any `*_key.json` files are git-ignored by default.
- `storage/` (uploaded notices, generated reports, session state) is git-ignored — do not commit uploaded PDFs or generated reports.
- The Supabase `service_role`/secret key bypasses Row Level Security — keep it server-side only, never expose it to a browser or client.
