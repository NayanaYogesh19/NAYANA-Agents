# Competitor Insight

A collection of competitor intelligence agents for scraping and analyzing ads across multiple platforms.

## Agents

### [`meta_ads_intelligence_agent/`](meta_ads_intelligence_agent/)

A multi-platform competitor ad intelligence tool that scrapes and analyzes ads from **Meta Ads Library**, **Google Ads Transparency Center**, and **LinkedIn** (via screenshot OCR).

**Tech Stack:** LangGraph · LangChain · Selenium · Playwright · Apify · Streamlit

**Run:**
```bash
cd meta_ads_intelligence_agent
pip install -r requirements.txt
playwright install chromium
streamlit run streamlit_app.py
```

**Platforms supported:**

| Platform | Method | API Key Required |
|---|---|---|
| Meta Ads Library | Selenium browser automation | None |
| Google Ads Transparency | Apify API | `APIFY_TOKEN` |
| LinkedIn Ads | Screenshot OCR via LLM | `OPENROUTER_API_KEY` |

## Setup

1. Copy `.env.example` to `.env` inside the agent folder
2. Fill in your API keys — see each agent's README for details
3. **Never commit `.env`** — it is listed in `.gitignore`
