def calculate_score(resolution):

    score = 50

    policy = resolution.get(
        "policy",
        {}
    )

    checks = policy.get(
        "checks",
        []
    )

    score += len(checks) * 10

    precedents = resolution.get(
        "precedents",
        []
    )

    score += len(precedents) * 5

    if score > 100:

        score = 100

    return score