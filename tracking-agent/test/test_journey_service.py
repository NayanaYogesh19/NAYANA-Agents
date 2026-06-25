from services.journey_service import (
    build_customer_journey
)


interaction_logs = [

    "Homepage Opened",

    "Clicked Product Page",

    "Opened Checkout Page"
]


detected_events = [

    "PageView",

    "ViewContent",

    "BeginCheckout"
]


journey = build_customer_journey(

    interaction_logs,

    detected_events
)


print("\nCustomer Journey:\n")

for step in journey:

    print(f"✔ {step}")