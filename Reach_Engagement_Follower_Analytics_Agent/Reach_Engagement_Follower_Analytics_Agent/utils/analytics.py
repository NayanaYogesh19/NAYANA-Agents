
def generate_summary(results):

    summary = {
        "total_platforms_analyzed": 0,
        "platforms": [],
        "top_content_patterns": [],
        "recommended_strategy": []
    }

    for platform, data in results.items():

        if platform == "summary":
            continue

        summary["total_platforms_analyzed"] += 1

        summary["platforms"].append(
            platform
        )

        for angle in data.get(
            "content_angles",
            []
        ):

            if (
                angle
                not in summary[
                    "top_content_patterns"
                ]
            ):

                summary[
                    "top_content_patterns"
                ].append(
                    angle
                )

        for strategy in data.get(
            "recommended_strategy",
            []
        ):

            if (
                strategy
                not in summary[
                    "recommended_strategy"
                ]
            ):

                summary[
                    "recommended_strategy"
                ].append(
                    strategy
                )

    return summary