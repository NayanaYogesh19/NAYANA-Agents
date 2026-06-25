import os

import requests

from dotenv import load_dotenv

# =========================================
# LOAD ENV
# =========================================

load_dotenv()

API_KEY = os.getenv(
    "SE_RANKING_API_KEY"
)

# =========================================
# HEADERS
# =========================================

HEADERS = {

    "Authorization": API_KEY,

    "Content-Type": "application/json"
}

# =========================================
# FETCH RELATED KEYWORDS
# =========================================

def fetch_related_keywords(seed_keyword):

    print(
        "SE RANKING KEYWORDS:",
        seed_keyword
    )

    url = (
        "https://api.seranking.com/v1/"
        "keyword-suggestions"
    )

    payload = {

        "keyword":
        seed_keyword,

        "country_code":
        "in",

        "limit":
        25
    }

    try:

        response = requests.post(

            url,

            headers=HEADERS,

            json=payload,

            timeout=30
        )

        data = response.json()

        keywords = []

        for item in data.get(
            "keywords",
            []
        ):

            keyword = item.get(
                "keyword"
            )

            if keyword:

                keywords.append(
                    keyword
                )

        return list(set(keywords))

    except Exception as e:

        print(
            "SE Ranking Keyword Error:",
            e
        )

        return []

# =========================================
# DYNAMIC CATEGORY INFERENCE
# =========================================

def infer_category_from_keywords(
    keywords
):

    combined = " ".join(
        keywords
    ).lower()

    # =====================================
    # CATEGORY DETECTION
    # =====================================

    if "pickle" in combined:
        return "Pickles"

    elif "powder" in combined:
        return "Powders"

    elif "snack" in combined:
        return "Snacks"

    elif "sweet" in combined:
        return "Sweets"

    elif "masala" in combined:
        return "Masala"

    elif "rice" in combined:
        return "Rice"

    elif "oil" in combined:
        return "Oils"

    elif "coffee" in combined:
        return "Coffee"

    elif "tea" in combined:
        return "Tea"

    elif "chocolate" in combined:
        return "Chocolate"

    return "General"