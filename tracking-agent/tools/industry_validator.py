from utils.constants import (
    B2C_EVENTS,
    B2B_EVENTS
)


def validate_industry_events(
    detected_events,
    industry_type
):

    required_events = []

    # Select industry standard events
    if industry_type.lower() == "b2c":

        required_events = B2C_EVENTS

    elif industry_type.lower() == "b2b":

        required_events = B2B_EVENTS

    else:

        return {
            "error": "Invalid industry type"
        }

    missing_events = []

    detected_lower = [
        event.lower()
        for event in detected_events
    ]

    # Compare required vs detected
    for event in required_events:

        if event.lower() not in detected_lower:

            missing_events.append(event)

    return {
        "industry": industry_type,
        "required_events": required_events,
        "detected_events": detected_events,
        "missing_events": missing_events
    }