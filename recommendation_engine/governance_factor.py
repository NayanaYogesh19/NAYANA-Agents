def extract_governance_factors(resolution):

    text = resolution.get(
        "resolution_text",
        ""
    ).lower()

    return {

        "board_support":
        "board recommends" in text,

        "annexures":
        "annexure" in text,

        "ordinary_resolution":
        "ordinary resolution" in text,

        "special_resolution":
        "special resolution" in text,

        "director_information":
        (
            "qualification" in text
            or
            "experience" in text
        )

    }