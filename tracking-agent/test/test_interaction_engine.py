from urllib.parse import (
    urljoin
)


def interact_with_website(

    page,

    base_url
):

    interaction_logs = []

    print(
        "\nStarting Behavioral Journey Engine...\n"
    )

    try:

        # =========================
        # HOMEPAGE
        # =========================
        interaction_logs.append(
            "Homepage Opened"
        )

        # =========================
        # SCROLL PAGE
        # =========================
        print("Scrolling Page...")

        page.mouse.wheel(0, 3000)

        page.wait_for_timeout(2000)

        interaction_logs.append(
            "Scrolled Homepage"
        )

        # =========================
        # BUTTON INTERACTION
        # =========================
        buttons = page.locator(

            "button"
        )

        button_count = min(
            buttons.count(),
            5
        )

        print(
            f"Found {button_count} buttons"
        )

        for i in range(button_count):

            try:

                button = buttons.nth(i)

                button_text = (
                    button.inner_text()
                    .strip()
                )

                if not button_text:
                    continue

                print(
                    f"Clicking Button: {button_text}"
                )

                button.click(
                    timeout=2000
                )

                page.wait_for_timeout(
                    1500
                )

                interaction_logs.append(

                    f"Clicked Button: {button_text}"
                )

            except Exception:

                pass

        # =========================
        # FORM DETECTION
        # =========================
        forms = page.locator("form")

        form_count = forms.count()

        print(
            f"Found {form_count} forms"
        )

        if form_count > 0:

            interaction_logs.append(
                "Contact Form Detected"
            )

        # =========================
        # INPUT FIELDS
        # =========================
        inputs = page.locator("input")

        input_count = min(
            inputs.count(),
            3
        )

        for i in range(input_count):

            try:

                input_box = inputs.nth(i)

                input_type = (
                    input_box.get_attribute(
                        "type"
                    )
                )

                if input_type in [

                    "text",

                    "email",

                    "tel"
                ]:

                    input_box.fill(
                        "test"
                    )

                    interaction_logs.append(

                        f"Filled {input_type} Field"
                    )

            except Exception:

                pass

        # =========================
        # SOCIAL / WHATSAPP
        # =========================
        links = page.locator("a")

        link_count = min(
            links.count(),
            30
        )

        visited_links = set()

        for i in range(link_count):

            try:

                link = links.nth(i)

                href = (
                    link.get_attribute(
                        "href"
                    )
                )

                if not href:
                    continue

                href_lower = (
                    href.lower()
                )

                # =========================
                # WHATSAPP
                # =========================
                if "wa.me" in href_lower or (
                    "whatsapp"
                    in href_lower
                ):

                    interaction_logs.append(
                        "Clicked WhatsApp"
                    )

                # =========================
                # SOCIAL LINKS
                # =========================
                social_platforms = [

                    "facebook",

                    "instagram",

                    "linkedin",

                    "twitter",

                    "youtube"
                ]

                for platform in (
                    social_platforms
                ):

                    if platform in href_lower:

                        interaction_logs.append(

                            f"Clicked {platform.title()}"
                        )

                # =========================
                # PRODUCT PAGES
                # =========================
                if "product" in href_lower:

                    full_url = urljoin(
                        base_url,
                        href
                    )

                    if full_url in visited_links:
                        continue

                    visited_links.add(
                        full_url
                    )

                    print(
                        f"Opening Product: {full_url}"
                    )

                    page.goto(
                        full_url,
                        timeout=10000
                    )

                    page.wait_for_timeout(
                        2000
                    )

                    interaction_logs.append(
                        "Opened Product Page"
                    )

                # =========================
                # CHECKOUT
                # =========================
                if "checkout" in href_lower:

                    interaction_logs.append(
                        "Opened Checkout Page"
                    )

            except Exception:

                pass

        print(
            "\nBehavioral Journey Completed"
        )

    except Exception as e:

        print(
            f"\nInteraction Error: {e}"
        )

    return interaction_logs