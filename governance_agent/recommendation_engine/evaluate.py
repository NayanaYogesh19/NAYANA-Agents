def evaluate_governance(

    factors,

    policy,

    precedents,

    risks

):

    positive = 0

    if factors["board_support"]:

        positive += 1

    if policy:

        positive += 1

    if precedents:

        positive += 1

    if len(risks) == 0:

        positive += 1

    if positive == 4:

        recommendation = "FOR"

    elif positive >= 2:

        recommendation = "FOR*"

    else:

        recommendation = "AGAINST"

    if positive >= 3:

        confidence = "High"

    elif positive == 2:

        confidence = "Medium"

    else:

        confidence = "Low"

    return {

        "recommendation":
        recommendation,

        "confidence":
        confidence

    }