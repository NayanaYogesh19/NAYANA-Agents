def generate_report(resolutions):

    report = []

    for r in resolutions:

        item = {

            "resolution_number":

            r.get(
                "resolution_number"
            ),

            "resolution_type":

            r.get(
                "resolution_type"
            ),

            "recommendation":

            r.get(
                "recommendation",
                {}
            ).get(
                "recommendation"
            ),

            "confidence":

            r.get(
                "recommendation",
                {}
            ).get(
                "confidence"
            ),

            "reasoning":

            r.get(
                "recommendation",
                {}
            ).get(
                "reasoning"
            )

        }

        report.append(item)

    return report