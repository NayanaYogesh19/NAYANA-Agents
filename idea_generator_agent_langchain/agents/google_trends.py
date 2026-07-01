import os
import requests
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


def _fetch_trends(query: str) -> list:
    """Fetch rising + top related queries for a single search term."""
    try:
        resp = requests.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_trends",
                "q": query,
                "data_type": "RELATED_QUERIES",
                "api_key": SERPAPI_API_KEY,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        rq = data.get("related_queries", {})
        rising = rq.get("rising", []) if isinstance(rq, dict) else []
        top    = rq.get("top", [])    if isinstance(rq, dict) else []
        return rising + top
    except Exception:
        return []


def get_google_trends(topic: str, domain: str = "", keywords: list = None) -> dict:
    """
    Fetches Google Trends dynamically based on the actual topic, domain,
    and top keywords extracted from the website — nothing is hardcoded.

    Makes up to 3 SerpAPI calls:
      1. topic alone            (e.g. "MCA")
      2. topic + domain name    (e.g. "MCA college")  — derived from website URL
      3. top keyword from page  (e.g. "MCA admissions") — extracted from that site

    Merges all rising + top queries, deduplicates, and returns the top 20.
    """

    keywords = keywords or []

    # ── Build dynamic query list — nothing hardcoded ──
    queries = []

    # Query 1: user's topic exactly as typed
    if topic:
        queries.append(topic.strip())

    # Query 2: topic + domain name (extracted from URL, no hardcoding)
    # e.g. domain="Education" → "MCA Education"
    # e.g. domain="Customer Service" → "Customer Service outsourcing"
    if domain and domain.strip().lower() not in topic.lower():
        combined = f"{topic} {domain}".strip()
        if combined not in queries:
            queries.append(combined)

    # Query 3: first meaningful keyword extracted from the actual website HTML
    # This is fully dynamic — it comes from scraping the real page
    for kw in keywords[:5]:
        candidate = kw.strip()
        if len(candidate) > 3 and candidate.lower() not in topic.lower():
            if candidate not in queries:
                queries.append(candidate)
                break

    print(f"\n[TRENDS] Querying Google Trends for: {queries}")

    # ── Fetch trends for each query ──
    seen_queries = set()
    all_items = []

    for q in queries:
        items = _fetch_trends(q)
        for item in items:
            if not isinstance(item, dict):
                continue
            qtext = item.get("query", "").strip().lower()
            if qtext and qtext not in seen_queries:
                seen_queries.add(qtext)
                all_items.append(item)

    # ── Sort by extracted_value descending (highest trend volume first) ──
    all_items.sort(
        key=lambda x: x.get("extracted_value", 0) if isinstance(x.get("extracted_value"), (int, float)) else 0,
        reverse=True
    )

    # Keep top 20
    top_items = all_items[:20]

    print(f"[TRENDS] Collected {len(top_items)} unique trend queries:")
    for item in top_items:
        print(f"  • {item.get('query')} ({item.get('value', '')})")

    # Return in the same shape the rest of the pipeline expects
    return {
        "related_queries": {
            "rising": top_items,
            "top": []
        }
    }
