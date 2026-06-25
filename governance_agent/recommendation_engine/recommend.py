def generate_recommendation(resolution):

    from recommendation_engine.governance_score import calculate_score

    score = calculate_score(resolution)

    if score >= 80:
        recommendation = "FOR"
    elif score >= 60:
        recommendation = "FOR"
    else:
        recommendation = "AGAINST"

    confidence = "High"

    reasoning = []

    policy = resolution.get(
        "policy",
        {}
    )

    precedents = resolution.get(
        "precedents",
        []
    )

    if policy:

        reasoning.append(
            f"Applied policy: {policy.get('policy_name')}"
        )

    if precedents:

        reasoning.append(
            f"Found {len(precedents)} historical precedents."
        )

    else:

        reasoning.append(
            "No historical precedents found."
        )

    reasoning.append(
        "No major governance concerns identified."
    )

    return {

        "recommendation": recommendation,

        "confidence": confidence,
         "governance_score":score,

        "reasoning": reasoning

    }