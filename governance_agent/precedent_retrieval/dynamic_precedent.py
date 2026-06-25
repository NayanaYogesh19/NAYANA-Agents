import os
import json


def search_precedents(resolution_type):

    folder = "storage/approved"

    os.makedirs(
        folder,
        exist_ok=True
    )

    matches = []

    for file in os.listdir(folder):

        if not file.endswith(".json"):

            continue

        path = os.path.join(
            folder,
            file
        )

        try:

            with open(
                path,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

        except:

            continue

        resolutions = data.get(
            "resolutions",
            []
        )

        for r in resolutions:

            if r.get(
                "resolution_type"
            ) == resolution_type:

                matches.append({

                    "company":

                    data.get(
                        "company_name"
                    ),

                    "financial_year":

                    data.get(
                        "financial_year"
                    ),

                    "recommendation":

                    r.get(
                        "recommendation"
                    ),

                    "governance_evaluation":

                    r.get(
                        "governance_evaluation"
                    )

                })

    return matches