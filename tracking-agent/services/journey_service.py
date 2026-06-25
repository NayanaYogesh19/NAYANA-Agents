def build_customer_journey(

    interaction_logs,

    detected_events
):

    print(
        "\nBuilding Customer Journey...\n"
    )

    customer_journey = []

    # =========================
    # INTERACTION LOGS
    # =========================
    for log in interaction_logs:

        customer_journey.append(log)

    # =========================
    # EVENT MAPPING
    # =========================
    event_mapping = {

        "PageView":
        "PageView Event Fired",

        "ViewContent":
        "ViewContent Event Fired",

        "AddToCart":
        "AddToCart Event Fired",

        "BeginCheckout":
        "BeginCheckout Event Fired",

        "Purchase":
        "Purchase Event Fired",

        "Lead":
        "Lead Event Fired",

        "FormSubmit":
        "FormSubmit Event Fired",

        "SocialClick":
        "SocialClick Event Fired"
    }

    # =========================
    # ADD EVENTS TO JOURNEY
    # =========================
    for event in detected_events:

        if event in event_mapping:

            customer_journey.append(

                event_mapping[event]
            )

    print(
        "\nCustomer Journey Built"
    )

    return customer_journey