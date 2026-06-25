def evaluate_policy(

    resolution

):

    policy = resolution.get(

        "policy",

        {}

    )

    checks = policy.get(

        "checks",

        []

    )

    passed = len(checks)

    total = len(checks)

    return {

        "total":total,

        "passed":passed

    }