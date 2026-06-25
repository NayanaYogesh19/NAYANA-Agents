import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("SE_RANKING_API_KEY")

HEADERS = {
    "Authorization": f"Token {API_KEY}",
    "Content-Type": "application/json"
}

BASE_URL = "https://api.seranking.com/v1/domain/keywords"


def get_ranking_keywords(page_url, country_code):
    """Fetch keywords that a specific page URL is already ranking for in Google."""
    print(f"FETCHING RANKING KEYWORDS: {page_url} [{country_code}]")

    params = {
        "source": country_code,
        "url": page_url,
        "type": "organic",
        "limit": 100
    }

    try:
        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params=params,
            timeout=30
        )

        print(f"SE Ranking Status: {response.status_code}")

        if response.status_code != 200:
            print(f"SE Ranking Error Response: {response.text}")
            return []

        data = response.json()

        # API may return a list directly or a dict with a keywords key
        if isinstance(data, list):
            keywords = data
        else:
            keywords = data.get("keywords", data.get("data", []))

        print(f"KEYWORDS FOUND: {len(keywords)} for {page_url}")
        return keywords

    except Exception as e:
        print(f"SE Ranking Fetch Error: {e}")
        return []


def pick_top_keywords(keywords, n=15):
    """Sort by volume DESC, difficulty ASC and return top N. Raw data only — no interpretation."""
    filtered = [k for k in keywords if isinstance(k, dict)]

    sorted_keywords = sorted(
        filtered,
        key=lambda k: (
            -(k.get("volume", 0) or 0),
            (k.get("difficulty", 100) or 100)
        )
    )

    return sorted_keywords[:n]
