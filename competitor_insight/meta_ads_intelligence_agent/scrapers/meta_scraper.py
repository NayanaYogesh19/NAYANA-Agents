from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager

import time
import uuid


class AdsLibraryBrowser:

    # ---------------------------------------------------
    # INIT
    # ---------------------------------------------------

    def __init__(self, headless=False):

        options = webdriver.ChromeOptions()

        if headless:

            options.add_argument("--headless")

        options.add_argument("--start-maximized")

        # ---------------------------------------------------
        # REDUCE SELENIUM DETECTION
        # ---------------------------------------------------

        options.add_argument(
            "--disable-blink-features=AutomationControlled"
        )

        options.add_experimental_option(
            "excludeSwitches",
            ["enable-automation"]
        )

        options.add_experimental_option(
            "useAutomationExtension",
            False
        )

        self.driver = webdriver.Chrome(

            service=Service(
                ChromeDriverManager().install()
            ),

            options=options
        )

        self.url = None

    # ---------------------------------------------------
    # OPEN URL
    # ---------------------------------------------------

    def open(self, url):

        self.url = url

        self.driver.get(url)

        time.sleep(10)

        # ---------------------------------------------------
        # INITIAL SCROLLS
        # ---------------------------------------------------

        for _ in range(3):

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(4)

        self.driver.execute_script(
            "window.scrollTo(0, 0);"
        )

        time.sleep(3)

    # ---------------------------------------------------
    # DETECT MEDIA TYPE
    # ---------------------------------------------------

    def detect_media_type(self, text):

        text = text.lower()

        if any(

            keyword in text

            for keyword in [

                "0:00 /",
                "video"
            ]
        ):

            return "video"

        if any(

            keyword in text

            for keyword in [

                "carousel",
                "multiple images"
            ]
        ):

            return "carousel"

        return "image"

    # ---------------------------------------------------
    # EXTRACT ADVERTISER
    # ---------------------------------------------------

    def extract_advertiser(self, lines):

        advertiser = None

        for i, line in enumerate(lines):

            clean_line = line.strip()

            if not clean_line:
                continue

            if "Sponsored" in clean_line and i > 0:

                possible_advertiser = lines[i - 1].strip()

                possible_advertiser = possible_advertiser.replace(
                    "\u200b",
                    ""
                ).strip()

                invalid_words = [

                    "Library ID",
                    "Started running",
                    "Platforms",
                    "Active",
                    "Filters",
                    "Sort by",
                    "Meta",
                    "See summary details"
                ]

                invalid = False

                for word in invalid_words:

                    if word.lower() in possible_advertiser.lower():

                        invalid = True
                        break

                if not invalid and len(possible_advertiser) > 1:

                    advertiser = possible_advertiser
                    break

        if not advertiser:

            advertiser = "Unknown Advertiser"

        return advertiser

    # ---------------------------------------------------
    # EXTRACT AD TEXT
    # ---------------------------------------------------

    def extract_ad_text(self, lines, advertiser):

        ad_copy_candidates = []

        skip_phrases = [

            "Sponsored",
            "Library ID",
            "Started running",
            "Platforms",
            "Open Drop-down",
            "See summary details",
            "Active",
            "Filters",
            "Sort by"
        ]

        for line in lines:

            skip = False

            for phrase in skip_phrases:

                if phrase.lower() in line.lower():

                    skip = True
                    break

            if skip:
                continue

            if line == advertiser:
                continue

            if len(line) > 20:

                ad_copy_candidates.append(line)

        if len(ad_copy_candidates) > 0:

            return " ".join(
                ad_copy_candidates[:4]
            )

        return None

    # ---------------------------------------------------
    # COLLECT ADS
    # ---------------------------------------------------

    def collect_ads(self, max_ads=20):

        ads = []

        collected_texts = set()

        selectors = [

            # Meta visible ad cards

            "//div[@role='button'][contains(., 'Sponsored')]",

            "//div[contains(@aria-label, 'Sponsored')]",

            "//div[contains(., 'Sponsored') and contains(., 'Library ID')]",

            "//div[contains(., 'Sponsored') and string-length(text()) > 100]"
        ]

        detected_selector = None

        # ---------------------------------------------------
        # DETECT SELECTOR
        # ---------------------------------------------------

        for selector in selectors:

            try:

                cards = self.driver.find_elements(
                    By.XPATH,
                    selector
                )

                print(f"Trying selector: {selector}")

                print(f"Cards found: {len(cards)}")

                if len(cards) > 0:

                    detected_selector = selector
                    break

            except Exception as e:

                print(e)

        if not detected_selector:

            print("No selector detected.")

            return ads

        # ---------------------------------------------------
        # SCROLL LOOP
        # ---------------------------------------------------

        previous_count = 0
        stagnant_rounds = 0

        while len(ads) < max_ads and stagnant_rounds < 5:

            cards = self.driver.find_elements(
                By.XPATH,
                detected_selector
            )

            print(f"Detected cards: {len(cards)}")

            for card in cards:

                try:

                    self.driver.execute_script(
                        "arguments[0].scrollIntoView(true);",
                        card
                    )

                    time.sleep(1)

                    raw_text = self.driver.execute_script(
                        "return arguments[0].innerText;",
                        card
                    )

                    if not raw_text:
                        continue

                    raw_text = raw_text.strip()

                    # ---------------------------------------------------
                    # IGNORE HUGE PAGE CONTAINERS
                    # ---------------------------------------------------

                    if len(raw_text.split("\n")) > 80:
                        continue

                    # ---------------------------------------------------
                    # REMOVE DUPLICATES
                    # ---------------------------------------------------

                    if raw_text in collected_texts:
                        continue

                    if len(raw_text) < 30:
                        continue

                    collected_texts.add(raw_text)

                    # ---------------------------------------------------
                    # SPLIT LINES
                    # ---------------------------------------------------

                    lines = [

                        line.strip()

                        for line in raw_text.split("\n")

                        if line.strip()
                    ]

                    # ---------------------------------------------------
                    # EXTRACT FIELDS
                    # ---------------------------------------------------

                    advertiser = self.extract_advertiser(
                        lines
                    )

                    ad_text = self.extract_ad_text(
                        lines,
                        advertiser
                    )

                    media_type = self.detect_media_type(
                        raw_text
                    )

                    # ---------------------------------------------------
                    # BUILD AD OBJECT
                    # ---------------------------------------------------

                    ad = {

                        "ad_library_id": str(
                            uuid.uuid4()
                        ),

                        "advertiser_name": advertiser,

                        "ad_status": "Active",

                        "date_started": None,

                        "date_scraped": time.strftime(
                            "%Y-%m-%d"
                        ),

                        "platforms": [
                            "Facebook",
                            "Instagram"
                        ],

                        "primary_text": ad_text,

                        "headline": None,

                        "description": None,

                        "cta_text": None,

                        "landing_url": None,

                        "media_type": media_type,

                        "creative_image_url": None,

                        "creative_video_url": None,

                        "ad_snapshot_url": self.driver.current_url,

                        "raw_card_text": raw_text
                    }

                    ads.append(ad)

                    print(
                        f"Collected ad #{len(ads)}: {advertiser}"
                    )

                    if len(ads) >= max_ads:
                        break

                except Exception as e:

                    print(
                        f"Extraction failed: {e}"
                    )

            # ---------------------------------------------------
            # SCROLL MORE
            # ---------------------------------------------------

            self.driver.execute_script(
                "window.scrollTo(0, document.body.scrollHeight);"
            )

            time.sleep(4)

            current_count = len(cards)

            if current_count == previous_count:

                stagnant_rounds += 1

            else:

                stagnant_rounds = 0

            previous_count = current_count

        print(f"FINAL META ADS: {len(ads)}")

        return ads

    # ---------------------------------------------------
    # SCREENSHOT
    # ---------------------------------------------------

    def save_screenshot(self, path):

        self.driver.save_screenshot(path)

    # ---------------------------------------------------
    # CLOSE
    # ---------------------------------------------------

    def close(self):

        self.driver.quit()