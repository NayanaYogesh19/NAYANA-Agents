# SMM Idea Generator Agent

An AI-powered Social Media Marketing Idea Generator built with **FastAPI + LangChain**, replicating and enhancing an n8n workflow. It analyses any live website, fetches real-time Google Trends, and generates 15 unique, high-quality SMM content ideas tailored specifically to that business.

---

## Features

- Live website analysis — scrapes headings, services, CTAs, navigation, and meta data
- Real-time Google Trends — fetches rising trend queries dynamically based on topic, domain, and site keywords
- AI-generated ideas — 15 unique, funnel-aware (TOFU/MOFU/BOFU) content ideas via OpenRouter (GPT-4o-mini)
- Platform distribution — Instagram, LinkedIn, Ads, Any Platform
- PDF download — download all ideas as a branded PDF with one click
- Glassmorphism UI — Trilliant Digital design system
- URL validation — rejects invalid or offline website URLs immediately
- Unique per run — random seed ensures fresh ideas every generation, even for the same website

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| AI / LLM | LangChain + OpenRouter (GPT-4o-mini) |
| Trends | SerpAPI (Google Trends — RELATED_QUERIES) |
| Web Scraping | Requests + BeautifulSoup4 + lxml |
| Frontend | Single-file HTML (inline CSS + JS) |
| PDF Export | jsPDF (browser-side) |

---

## Project Structure

```
idea_generator_agent_langchain/
├── app.py                   # FastAPI app — 9-step pipeline
├── agents/
│   ├── input_parser.py      # URL validation + field parsing
│   ├── website_fetcher.py   # Live website HTML fetch (SSL fallback)
│   ├── html_extractor.py    # Rich content extraction from HTML
│   ├── keyword_extractor.py # Keyword extraction + website context
│   ├── google_trends.py     # Dynamic Google Trends (3 query angles)
│   ├── merge.py             # Merge keyword + trends data
│   ├── content_generator.py # LLM call with full context
│   ├── json_validator.py    # JSON repair + normalisation
│   └── google_sheet.py      # Optional Google Sheets write (non-blocking)
├── prompts/
│   └── prompt.py            # System + user prompt templates
├── services/
│   └── openrouter.py        # OpenRouter LLM client
├── templates/
│   └── index.html           # Full UI (Glassmorphism, inline CSS+JS)
├── .env.example             # Environment variable template
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/NayanaYogesh19/NAYANA-Agents.git
cd NAYANA-Agents/idea_generator_agent_langchain
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your keys:

```env
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=openai/gpt-4o-mini
SERPAPI_API_KEY=your_serpapi_key_here
GOOGLE_SHEET_ID=your_google_sheet_id_here
GOOGLE_CREDENTIALS=oauth_client.json
```

### 3. Run

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 9000 --reload
```

Open `http://127.0.0.1:9000` in your browser.

---

## How It Works

```
User Input (website URL + domain + topic + lead magnet)
        ↓
Step 1  Validate URL — rejects invalid / offline sites immediately
        ↓
Step 2  Fetch live HTML from the website
        ↓
Step 3  Extract: headings, meta, navigation, services, CTAs, paragraphs
        ↓
Step 4  Extract 30 meaningful keywords from the page content
        ↓
Step 5  Google Trends — 3 dynamic queries:
          • topic alone
          • topic + domain
          • top keyword from the actual page
        → Merges + deduplicates → top 20 rising trends
        ↓
Step 6  Merge all data into one context dict
        ↓
Step 7  AI generates 15 unique ideas using:
          • Live website context
          • Real trend queries
          • Random seed (different ideas every run)
        ↓
Step 8  JSON validation + repair (tolerates partial LLM output)
        ↓
Step 9  Return ideas to UI — filter by platform, download as PDF
```

---

## Sample Inputs

| Website | Domain | Topic | Lead Magnet |
|---|---|---|---|
| `https://suranacollege.edu.in` | Education | MCA Admissions | Free Counselling Session |
| `https://hrhnext.com` | Customer Services | Inbound Call Center | Free Process Audit |
| `https://trilliantdigital.in` | Digital Marketing | SEO and Lead Generation | Free SEO Audit |
| `https://zoho.com` | SaaS CRM | CRM Software for Small Business | Free 15-Day Trial |
| `https://nykaa.com` | Beauty and Skincare | Skincare Products | none |

---

## API

### `POST /generate-ideas`

**Request body:**
```json
{
  "website_url": "https://example.com",
  "domain": "Education",
  "topic": "MCA Admissions",
  "lead_magnet": "Free Counselling"
}
```

**Response:**
```json
{
  "status": "success",
  "total_ideas": 15,
  "ideas": [
    {
      "idea_id": 1,
      "idea_title": "...",
      "platform": "Instagram",
      "content_type": "Reel",
      "description": "...",
      "hook": "...",
      "target_audience": "...",
      "goal": "Lead Generation",
      "trend_used": "...",
      "cta": "..."
    }
  ],
  "sheet_status": "skipped"
}
```

---

## Built by

**Trilliant Digital** — AI & Automation Team  
Powered by LangChain + OpenRouter + SerpAPI
