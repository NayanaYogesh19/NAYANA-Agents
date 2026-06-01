from collections import Counter


def check_duplicates(requests):

    platforms = []

    for req in requests:
        platforms.append(req["platform"])

    counts = Counter(platforms)

    duplicates = []

    for platform, count in counts.items():

        if count > 1:

            duplicates.append({
                "platform": platform,
                "count": count
            })

    return duplicates