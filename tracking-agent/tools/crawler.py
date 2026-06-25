from urllib.parse import (
    urljoin,
    urlparse
)


def crawl_website(
    page,
    base_url
):

    print(
        "\nStarting Multi-page Crawl...\n"
    )

    crawled_pages = []

    try:

        # =========================
        # FIND ALL LINKS
        # =========================
        links = page.locator("a")

        total_links = min(
            links.count(),
            50
        )

        print(
            f"Found {total_links} links"
        )

        important_keywords = [

            "product",
            "shop",
            "pricing",
            "contact",
            "cart",
            "checkout",
            "collection",
            "services",
            "category"
        ]

        visited_urls = set()

        for i in range(total_links):

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
                # IGNORE EXTERNAL LINKS
                # =========================
                if href.startswith("http"):

                    parsed_href = (
                        urlparse(href)
                    )

                    parsed_base = (
                        urlparse(base_url)
                    )

                    if (
                        parsed_href.netloc
                        !=
                        parsed_base.netloc
                    ):

                        continue

                # =========================
                # BLOCK AUTH PAGES
                # =========================
                blocked_words = [

                    "login",
                    "signup",
                    "register",
                    "auth",
                    "account"
                ]

                if any(
                    word in href.lower()
                    for word in blocked_words
                ):
                    continue

                # =========================
                # FILTER IMPORTANT PAGES
                # =========================
                should_visit = False

                for keyword in (
                    important_keywords
                ):

                    if keyword in (
                        href.lower()
                    ):

                        should_visit = True
                        break

                if not should_visit:
                    continue

                # =========================
                # BUILD FULL URL
                # =========================
                full_url = urljoin(
                    base_url,
                    href
                )

                if full_url in visited_urls:
                    continue

                visited_urls.add(
                    full_url
                )

                print(
                    f"Visiting: {full_url}"
                )

                # =========================
                # OPEN PAGE
                # =========================
                page.goto(
                    full_url,
                    timeout=10000
                )

                page.wait_for_timeout(
                    3000
                )

                crawled_pages.append(
                    full_url
                )

            except Exception:

                pass

        print(
            "\nCrawling Completed"
        )

    except Exception as e:

        print(
            f"\nCrawler Error: {e}"
        )

    return crawled_pages