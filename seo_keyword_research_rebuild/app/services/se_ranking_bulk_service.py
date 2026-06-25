import os

import requests

from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv(
    "SE_RANKING_API_KEY"
)

HEADERS = {

    "Authorization": API_KEY,

    "Content-Type": "application/json"
}

def get_bulk_keyword_metrics(keywords):

    results = []

    for keyword in keywords:

        try:

            response = requests.post(

                "https://api.seranking.com/v1/keyword-data",

                headers=HEADERS,

                json={

                    "keyword":
                    keyword,

                    "country_code":
                    "in"
                },

                timeout=30
            )

            data = response.json()

            results.append({

                "keyword":
                keyword,

                "volume":
                data.get(
                    "search_volume",
                    0
                ),

                "kd_score":
                data.get(
                    "keyword_difficulty",
                    0
                ),

                "kd_level":
                data.get(
                    "difficulty_level",
                    "Unknown"
                ),

                "intent":
                data.get(
                    "intent",
                    "Unknown"
                ),

                "cpc":
                data.get(
                    "cpc",
                    0
                ),

                "competition":
                data.get(
                    "competition",
                    0
                ),

                "trend":
                data.get(
                    "trend",
                    "Unknown"
                )
            })

        except Exception as e:

            print(
                "SE Ranking Metrics Error:",
                e
            )

    return results