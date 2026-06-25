# Website Structure Planning Agent
**LangChain · OpenAI GPT-4o-mini · Tavily Search API · ReportLab PDF**

---

## Changes from v1
| Item | v1 | v2 (this version) |
|---|---|---|
| AI Model | Claude (Anthropic) | **OpenAI GPT-4o-mini** |
| API Key needed | ANTHROPIC_API_KEY | **OPENAI_API_KEY** |
| Input #1 | Target URL only | **Target URL + Competitor URLs together** |

---

## What the Agent Does

### Mode 1 — Audit Existing Website (`audit_existing`)
You provide your **live website URL and competitor URLs together** (Input #1). The agent:
1. Scrapes all competitor websites via Tavily API
2. Scrapes your target site to analyse its current structure
3. Processes any audit notes you paste (from Screaming Frog, Ahrefs, etc.)
4. GPT-4o-mini analyses everything and designs a **corrected structure**
5. Gives specific **recommendations to fix what's wrong**
6. Gives a **step-by-step implementation strategy** to correct your site
7. Outputs a professional PDF report

### Mode 2 — New Website Structure (`new_structure`)
You provide your **planned domain and competitor URLs together**. The agent:
1. Scrapes competitor websites via Tavily API
2. GPT-4o-mini designs an **optimal page hierarchy from scratch**
3. Generates SEO-clean URL slugs for every page
4. Maps navigation menus, breadcrumbs, internal linking rules
5. Defines conversion funnels with CTA placement per tier
6. Gives **best-practice recommendations** to build it correctly
7. Gives a **phased build strategy** in logical execution order
8. Outputs a professional PDF report

---

## Inputs (as per Slide 8 of the spec)

| # | Input | Required | Description |
|---|---|---|---|
| 1 | Target URL + Competitor URLs | ✅ | Your site URL AND competitor URLs — entered together |
| 2 | Business Type + Business Goal | ✅ | B2B/B2C + Lead Gen/Demo/Ecommerce/Brand Awareness |
| 3 | Audit Notes | ❌ | Paste existing audit findings (Screaming Frog, Ahrefs, etc.) |
| 4 | API Keys | ✅ | Stored in `.env` — OPENAI_API_KEY + TAVILY_API_KEY |

## Outputs

| Output | Description |
|---|---|
| Visual Sitemap (PDF) | All pages, hierarchy levels, URL slugs, page types |
| Page Hierarchy Table | page name · tier · URL slug · type · priority · CTA |
| Navigation Flow | Primary/secondary nav · breadcrumbs · internal linking rules |
| Conversion Path Map | Goal-specific funnels · CTA per tier · key landing pages |
| Recommendations | Specific fixes (audit) or build guidelines (new structure) |
| Implementation Strategy | Phased plan in logical execution order |

---

## Setup

```bash
# 1. Go into the project folder
cd website_structure_agent_v2

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up your API keys
cp .env.example .env
# Edit .env and fill in:
#   OPENAI_API_KEY  →  https://platform.openai.com/api-keys
#   TAVILY_API_KEY  →  https://app.tavily.com  (free: 1,000 req/month)
```

Your `.env` file:
```
OPENAI_API_KEY=sk-...
TAVILY_API_KEY=tvly-...
```

---

## Running

### Web Interface (recommended)
```bash
python main.py
# Open http://localhost:8000
```

### Command Line
```bash
# Audit existing website:
python run_cli.py \
  --mode audit_existing \
  --target https://yoursite.com \
  --competitors https://comp1.com https://comp2.com https://comp3.com \
  --type B2B \
  --goal "Lead Generation"

# Plan new website:
python run_cli.py \
  --mode new_structure \
  --target https://mynewbrand.com \
  --competitors https://comp1.com https://comp2.com \
  --type B2C \
  --goal "E-commerce"

# With audit notes from file:
python run_cli.py \
  --mode audit_existing \
  --target https://yoursite.com \
  --competitors https://comp1.com \
  --type B2B \
  --goal "Lead Generation" \
  --audit-file ./my_audit_notes.txt
```

---

## How It Works Internally

```
User Inputs (together in Step 1):
  ├── Target URL
  └── Competitor URLs (1–5)
         ↓
Step 1  Tavily scrapes all competitor sites
        BeautifulSoup extracts nav labels + URL patterns
        GPT-4o-mini structures the benchmark data
         ↓
Step 2  [audit_existing] Scrape target site too
        [both modes]     GPT-4o-mini extracts audit issues from pasted notes
         ↓
Steps   GPT-4o-mini receives:
3-5       competitor benchmark + target scrape + audit issues + business type + goal
        Designs:
          • Page hierarchy  (Home → Category → Sub-cat → Detail)
          • SEO URL slugs   (lowercase, hyphen-separated, logical nesting)
          • Navigation      (primary nav, secondary nav, breadcrumbs, internal links)
          • Conversion paths (funnels + CTA per tier for B2B or B2C)
          • Recommendations (fix issues OR build correctly)
          • Strategy        (step-by-step implementation)
         ↓
Step 6  ReportLab builds PDF:
          Cover → Competitor Benchmarks → Audit Findings →
          Page Hierarchy → Navigation Flow → Conversion Paths →
          Recommendations → Implementation Strategy
        PDF saved to ./output/
```

---

## Tech Stack

| Component | Tool |
|---|---|
| AI Framework | LangChain (`langchain-openai`) |
| AI Model | OpenAI GPT-4o-mini (`gpt-4o-mini`) |
| Scraping | Tavily Search API + BeautifulSoup4 |
| PDF Generation | ReportLab |
| API Server | FastAPI + Uvicorn |

## Project Files

```
website_structure_agent_v2/
├── main.py                      ← FastAPI server + web UI
├── run_cli.py                   ← Command-line runner
├── config.py                    ← Settings (reads .env)
├── models.py                    ← Pydantic data models
├── requirements.txt             ← Dependencies
├── .env.example                 ← API key template
├── agents/
│   └── structure_agent.py       ← Main LangChain orchestrator (GPT-4o-mini)
├── tools/
│   ├── scraper.py               ← Tavily + BeautifulSoup scraper
│   └── pdf_generator.py         ← ReportLab PDF builder
├── prompts/
│   └── templates.py             ← All GPT-4o-mini prompt templates
├── frontend/
│   └── index.html               ← Web UI
└── output/                      ← Generated PDFs saved here
```
