from tools.industry_validator import (
    validate_industry_events
)


# Simulated detected events
detected_events = [
    "PageView",
    "ViewContent",
    "AddToCart"
]


result = validate_industry_events(
    detected_events,
    "b2c"
)


print("\nIndustry Event Validation:\n")

print(
    f"Industry Type: {result['industry']}"
)

print("\nDetected Events:")

for event in result["detected_events"]:

    print(f"✔ {event}")


print("\nMissing Events:")

if result["missing_events"]:

    for event in result["missing_events"]:

        print(f"❌ {event}")

else:

    print("No Missing Events")