def detect_risks(resolution):

    text = resolution.get(
        "resolution_text",
        ""
    ).lower()

    risks = []

    if "related party" in text:

        risks.append(
            "Related Party"
        )

    if "litigation" in text:

        risks.append(
            "Pending Litigation"
        )

    if "conflict of interest" in text:

        risks.append(
            "Conflict of Interest"
        )

    return risks