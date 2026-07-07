# PR & Events Agent

Given a company URL and a date range, produces a report of that
company's Press Releases, Webinars, Events/Exhibitions, and Awards/Wins
for that period — each with a source link — matching the "PR & Events
Overview" table format used in the competitor analysis deck.

## How it works

```
Company URL + date range
        |
        +--> Crawl company site (sitemap, RSS, common paths)
        +--> Search Google News / Custom Search, per category
        |
        v
   Fetch + extract clean text + real publish date  (trafilatura, htmldate)
        v
   Filter to the target date window
        v
   GPT-4o-mini (via OpenRouter) classifies into a category + writes the title (LangChain, structured output)
        v
   Dedupe near-identical stories across outlets (rapidfuzz)
        v
   [optional] Archive each surviving source via Wayback's Save Page Now
        v
   Local .xlsx (always) + Google Sheet / email (optional)
```

Discovery and filtering are ordinary deterministic code on purpose.
The LLM is only used for the one step that genuinely needs judgement —
deciding whether a page belongs in the report and writing a clean
title for it — so the run is repeatable and debuggable rather than a
black box.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and set at minimum:

```
OPENROUTER_API_KEY=sk-or-v1-...
```

Everything else in `.env.example` is optional and degrades gracefully
if left blank — see the comments in that file for what each block
needs and where to get it for free.

## Run it

```bash
# Full calendar month
python main.py --url https://www.example.com --month 2026-06

# Custom date range
python main.py --url https://www.example.com --start 2026-06-15 --end 2026-07-05

# Also email the result (requires SMTP_* in .env)
python main.py --url https://www.example.com --month 2026-06 --output email
```

A local `.xlsx` is **always** written to `data/`, one row per found
item, with a working hyperlink in the Link column — that's the
guaranteed output even with zero optional integrations configured.

## Accuracy expectations — please read before trusting the output

This will not be 100% correct out of the box, for the same reasons
covered when we discussed the design:

- **Search indexing lag** — a press release from the last few days of
  the window may not be indexed yet.
- **Date accuracy** — not every page exposes a reliable publish date;
  items with an unknown date are still included (not silently
  dropped) and marked `confidence: unverified` in the spreadsheet, so
  a reviewer knows to double-check them rather than trust them blind.
- **Classification edge cases** — the line between "event" and "press
  release" isn't always crisp; the LLM makes a judgment call.
- **Coverage gaps** — smaller or less-covered companies will
  legitimately return fewer/no results some months; that looks
  identical to "the agent missed it," so don't assume zero results
  means zero activity without a quick manual spot-check early on.

Treat the output as a strong first draft with sources attached — the
review step before sending is part of the design, not a workaround.

## Wayback Machine — what it does and doesn't do here

It's used for exactly one thing: once an item has already survived
discovery, extraction, classification, and dedup, `agent/archiver.py`
optionally submits it to Wayback's Save Page Now so there's a
permanent, timestamped copy of what the source said — evidence, in
case the original page is later edited or taken down. It plays no
role in finding anything; that's the site-crawl and search steps.
Archiving is **off by default** (`ENABLE_ARCHIVING=false`) since it
adds real time to each run (each save can take several seconds) — turn
it on once the discovery/classification quality looks good.

## Known limitations / good next steps

- No headless browser: pages that render their content entirely via
  client-side JavaScript (no server HTML, no sitemap entry, no RSS
  item) won't be picked up by the site crawler. If a specific
  competitor's site is like this, the Google-search half of the
  pipeline is doing most of the work for that company anyway.
- Google News RSS and Google Custom Search only support a relative
  "past N days" window, not an exact start/end date — the code
  requests a generous buffer and does the real filtering itself
  against the extracted publish date (see `agent/web_search.py`).
- One report = one company per run. For a full competitor set, loop
  `main.py` over your company list (a `companies.txt` + a small
  wrapper script is the natural next addition).

## Tests

```bash
pytest
```

These are offline-only (no network, no API key needed) and check the
dedup logic, date-window filtering, and data models — the parts that
are pure code rather than depending on live search results.

## Project layout

```
pr_events_agent/
├── main.py                  # CLI entry point
├── config.py                # env var loading, all settings in one place
├── agent/
│   ├── models.py             # Pydantic schemas (ReportItem, CompanyReport)
│   ├── site_crawler.py       # discovery on the company's own site
│   ├── web_search.py         # discovery via Google News RSS / Custom Search
│   ├── extractor.py          # clean text + real publish date per page
│   ├── classifier.py         # LangChain + GPT-4o-mini (OpenRouter) structured-output classification
│   ├── dedupe.py              # fuzzy near-duplicate removal
│   ├── archiver.py            # Wayback Machine (availability, CDX, Save Page Now)
│   └── pipeline.py            # ties all of the above together
├── output/
│   ├── sheet_writer.py        # local .xlsx (default) + optional Google Sheets
│   └── email_sender.py        # optional SMTP email
└── tests/
    └── test_smoke.py          # offline tests
```
