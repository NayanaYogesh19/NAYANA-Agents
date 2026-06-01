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
        # SCROLL PAGE
        # =========================
        print("Scrolling Page...")

        page.mouse.wheel(0, 3000)

        page.wait_for_timeout(2000)

        interaction_logs.append(
            "User Scrolled Homepage"
        )

        # =========================
        # BUTTON INTERACTION
        # =========================
        buttons = page.locator("button")

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

                button_text_lower = (
                    button_text.lower()
                )

                # Ignore useless popup buttons
                blocked_buttons = [

                    "×",
                    "close",
                    "cancel"
                ]

                if any(
                    word in button_text_lower
                    for word in blocked_buttons
                ):
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

                # =========================
                # SEMANTIC LOGS
                # =========================
                if "subscribe" in button_text_lower:

                    interaction_logs.append(
                        "User interacted with newsletter popup"
                    )

                elif "cart" in button_text_lower:

                    interaction_logs.append(
                        "User clicked Add To Cart"
                    )

                elif "buy" in button_text_lower:

                    interaction_logs.append(
                        "User clicked Buy Now"
                    )

                elif "checkout" in button_text_lower:

                    interaction_logs.append(
                        "User opened Checkout"
                    )

                else:

                    interaction_logs.append(
                        f"User clicked button: {button_text}"
                    )

            except Exception:

                pass

        # =========================
        # FORM DETECTION
        # =========================
        forms = page.locator("form")

        form_count = forms.count()

        if form_count > 0:

            interaction_logs.append(
                "Contact Form Detected"
            )

        # =========================
        # INPUT INTERACTION
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
                        f"User filled {input_type} field"
                    )

            except Exception:

                pass

        # =========================
        # LINK INTERACTION
        # =========================
        links = page.locator("a")

        link_count = min(
            links.count(),
            20
        )

        print(
            f"\nChecking {link_count} links"
        )

        important_keywords = [

            "product",
            "shop",
            "pricing",
            "contact",
            "cart",
            "checkout",
            "collection",
            "services"
        ]

        visited_links = set()

        for i in range(link_count):

            try:

                link = links.nth(i)

                href = (
                    link.get_attribute(
                        "href",
                        timeout=2000
                    )
                )

                if not href:
                    continue

                # =========================
                # REMOVE FAKE LINKS
                # =========================
                if href == "#":
                    continue

                if "javascript:" in (
                    href.lower()
                ):
                    continue

                href_lower = (
                    href.lower()
                )

                # =========================
                # WHATSAPP DETECTION
                # =========================
                if "wa.me" in href_lower or (
                    "whatsapp"
                    in href_lower
                ):

                    interaction_logs.append(
                        "User clicked WhatsApp contact"
                    )

                # =========================
                # SOCIAL MEDIA
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

                            f"User opened {platform.title()} page"
                        )

                # =========================
                # IGNORE EXTERNAL LINKS
                # =========================
                if href.startswith("http"):

                    if base_url not in href:
                        continue

                # =========================
                # BLOCK AUTH PAGES
                # =========================
                blocked_words = [

                    "signup",
                    "login",
                    "account",
                    "auth"
                ]

                if any(
                    word in href_lower
                    for word in blocked_words
                ):
                    continue

                link_text = (
                    link.inner_text()
                    .strip()
                    .lower()
                )

                should_open = False

                for keyword in (
                    important_keywords
                ):

                    if keyword in (
                        href_lower
                    ) or keyword in (
                        link_text
                    ):

                        should_open = True
                        break

                if not should_open:
                    continue

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
                    f"Opening Link: {full_url}"
                )

                page.goto(
                    full_url,
                    timeout=8000
                )

                page.wait_for_timeout(
                    2500
                )

                # =========================
                # SEMANTIC PAGE LOGS
                # =========================
                if "product" in href_lower:

                    interaction_logs.append(
                        "User viewed Product Page"
                    )

                elif "checkout" in href_lower:

                    interaction_logs.append(
                        "User reached Checkout Page"
                    )

                elif "contact" in href_lower:

                    interaction_logs.append(
                        "User opened Contact Page"
                    )

                elif "cart" in href_lower:

                    interaction_logs.append(
                        "User opened Cart"
                    )

                else:

                    interaction_logs.append(
                        f"User opened page: {full_url}"
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