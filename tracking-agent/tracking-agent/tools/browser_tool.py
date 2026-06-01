from playwright.sync_api import (
    sync_playwright
)


def open_website(url):

    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(

        headless=False,

        slow_mo=500
    )

    context = browser.new_context()

    page = context.new_page()

    try:

        print(
            f"\nOpening: {url}"
        )

        # =========================
        # OPEN WEBSITE
        # =========================
        page.goto(

            url,

            wait_until="domcontentloaded",

            timeout=30000
        )

        # =========================
        # WAIT SAFELY
        # =========================
        try:

            page.wait_for_load_state(
                "networkidle",
                timeout=10000
            )

        except Exception:

            pass

        # =========================
        # SAFE WAIT
        # =========================
        try:

            page.wait_for_timeout(3000)

        except Exception:

            pass

        # =========================
        # GET HTML
        # =========================
        try:

            html = page.content()

        except Exception:

            html = ""

        return {

            "playwright": playwright,

            "browser": browser,

            "page": page,

            "html": html
        }

    except Exception as e:

        print(
            f"\nBrowser Error: {e}"
        )

        browser.close()

        playwright.stop()

        return None