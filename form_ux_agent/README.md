# Form & UX Optimisation Agent
**Trilliant Digital · AI-Powered CRO · v1.0 MVP**

> Automatically audits website forms and generates Meta Ads instant form specs — with AI diagnosis, UX scoring, GA4 analytics, and downloadable PDF briefs.

---

## Features

| Feature | Description |
|---------|-------------|
| **Website Form Audit** | Scrape any registered website, detect all forms (including JS-rendered), run 8 UX checks |
| **Create New Form** | AI generates a complete form blueprint from scratch for your site |
| **Meta Ads Form Spec** | Mirror of Meta Ads Manager — generates 5 copy options per element (Headline, Description, CTA, Ending) |
| **GA4 Real Analytics** | Connect via Google OAuth — pulls real form start/submit events from GA4 |
| **AI Diagnosis** | GPT-4o-mini via OpenRouter — root causes, quick wins, UX optimisation plan, A/B test variants |
| **PDF + CSV Export** | Downloadable redesign brief and UX audit table |
| **Glassmorphism UI** | Trilliant Design System — frosted glass cards, purple gradient, dark mode toggle |

---

## Quick Start

### 1. Clone & install dependencies
```bash
git clone https://github.com/NayanaYogesh19/NAYANA-Agents.git
cd NAYANA-Agents/form_ux_agent
pip install -r requirements.txt
```

### 2. Install Playwright (for JS-rendered page scraping)
```bash
playwright install chromium
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Open .env and fill in your real API keys
```

### 4. Run the agent
```bash
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open in browser
```
http://localhost:8000
```

---

## Folder Structure

```
form_ux_agent/
├── .env.example                    ← Copy to .env and fill keys
├── requirements.txt
├── README.md
├── data/
│   └── accounts.csv               ← Registered client accounts
├── backend/
│   ├── main.py                    ← FastAPI app + all API routes
│   ├── accounts.py                ← CSV loader + URL validator
│   └── modules/
│       ├── scraper.py             ← Website + form scraper (BS4 + Playwright fallback)
│       ├── ux_engine.py           ← 8-point UX rule engine (dynamic B2B/B2C)
│       ├── analytics.py           ← GA4 Data API + simulated fallback
│       ├── ai_engine.py           ← AI diagnosis via OpenRouter (GPT-4o-mini)
│       └── report_generator.py   ← PDF (ReportLab) + CSV generation
├── frontend/
│   ├── templates/
│   │   └── index.html             ← Main UI (Jinja2)
│   └── static/
│       ├── css/style.css          ← Glassmorphism Design System
│       └── js/app.js              ← Frontend logic
└── output/                        ← Generated PDFs/CSVs (git-ignored)
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your keys. **Never commit `.env`.**

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI (GPT-4o-mini) |
| `GOOGLE_CLIENT_ID` | For GA4 | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | For GA4 | Google OAuth Client Secret |
| `GOOGLE_REDIRECT_URI` | For GA4 | Must match your Google Console setting |
| `CLARITY_API_KEY` | Optional | Microsoft Clarity export token |
| `ACCOUNTS_CSV` | Auto | Path to accounts CSV (default: `data/accounts.csv`) |

Get keys from:
- **OpenRouter**: [openrouter.ai](https://openrouter.ai) → API Keys
- **Google OAuth**: [console.cloud.google.com](https://console.cloud.google.com) → APIs & Credentials → OAuth 2.0 Client IDs → Enable Google Analytics Data API

---

## Accounts Spreadsheet (`data/accounts.csv`)

Register every client before running analysis. The agent validates that the submitted URL belongs to a registered account.

| Column | Description | Example |
|--------|-------------|---------|
| `account_name` | Client name | Trilliant Digital |
| `account_id` | Internal numeric ID | 84297720 |
| `ga4_property_id` | GA4 Property ID (from GA4 Admin) | 343043403 |
| `website_url` | Official website URL | https://trilliantdigital.com/ |

---

## How to Use

### Website Path — Optimise Existing Form
1. Select account from the dropdown
2. Choose **Website** → **Optimise existing form**
3. Enter the form page URL and click **Scan for Forms**
4. Select a form from the discovered list
5. Set Business Goal, Audience (B2B/B2C), Device Priority
6. Optionally describe specific form requirements
7. Click **Run Form Analysis**
8. Review Diagnosis, UX Checks, Analytics tabs
9. Download PDF brief + UX CSV

### Website Path — Create New Form
1. Select account → **Website** → **Create new form**
2. Enter your website URL
3. Set goal/audience/device + description
4. Click **Generate Form Blueprint**
5. Review the AI-designed form structure in the **Form Blueprint** tab

### Meta Ads Path
1. Select account → **Paid Ads** → **Meta**
2. Set Business Goal and Audience
3. Choose Form Type (More Volume / Higher Intent / Rich Creative)
4. Select contact fields to capture; add Custom Questions if needed
5. Click **Generate Meta Form Spec with 5 Options Each**
6. Get 5 ready-to-paste copy options for every element — hover cards to copy

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Frontend UI |
| `GET` | `/api/accounts` | List all registered accounts |
| `GET` | `/api/scan-forms` | Crawl a website and return all forms |
| `POST` | `/api/analyse/website` | Run website form analysis |
| `POST` | `/api/create/form` | Generate new form blueprint |
| `POST` | `/api/analyse/meta` | Generate Meta instant form spec |
| `GET` | `/api/download/{filename}` | Download PDF or CSV output |
| `GET` | `/auth/google` | Start GA4 OAuth flow |
| `GET` | `/auth/google/callback` | GA4 OAuth callback |
| `GET` | `/auth/google/status` | Check GA4 connection status |
| `GET` | `/health` | Health check |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11 · FastAPI · Uvicorn |
| Scraping | BeautifulSoup4 · Playwright (JS fallback) |
| Analytics | Google Analytics Data API v1 (OAuth 2.0) |
| AI | GPT-4o-mini via OpenRouter |
| PDF | ReportLab |
| Frontend | Vanilla HTML/CSS/JS · Tabler Icons · Google Fonts (Inter) |
| Design | Trilliant Glassmorphism Design System |
| Data | CSV (accounts) |

---

## UX Scoring Engine (8 Checks)

The rule engine evaluates every form against 8 criteria, dynamically adjusted for B2B vs B2C:

1. **Field count** — Too many fields reduce conversion
2. **Label quality** — Placeholder-only labels fail accessibility
3. **CTA strength** — Generic "Submit" loses to action-oriented copy
4. **Progress indicator** — Multi-step forms need step counters
5. **GDPR / consent** — Required for compliance
6. **Trust signals** — SSL badges, testimonials near the form
7. **Mobile optimisation** — Correct input types, tap target sizes
8. **Error handling** — Inline validation messages

---

*Trilliant Digital · Form & UX Optimisation Agent · v1.0 MVP · 2026*
