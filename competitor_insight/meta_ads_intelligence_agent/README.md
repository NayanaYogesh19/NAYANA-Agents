# Meta Ads Intelligence Agent

## Features

- LangGraph deterministic workflow
- Playwright browser automation
- LangChain structured extraction
- Pydantic schemas
- JSON + CSV export
- Screenshots for debugging

## Workflow

1. Open Meta Ads Library
2. Select country
3. Select category
4. Search business name
5. Collect ad cards
6. Generate structured insights
7. Export results

## Setup

### Create Virtual Environment

python -m venv .venv

### Activate

Windows:
.venv\Scripts\activate

### Install Dependencies

pip install -r requirements.txt

### Install Playwright Browsers

playwright install

### Add API Key

Copy `.env.example` to `.env`

Add your OpenAI API key.

### Run

python main.py