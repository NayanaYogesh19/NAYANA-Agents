import json
import pandas as pd


def save_json(data, path):

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False
        )


def save_csv(data, path):

    ads = data.get("ads", [])

    if ads:

        df = pd.DataFrame(ads)

        df.to_csv(
            path,
            index=False,
            encoding="utf-8"
        )