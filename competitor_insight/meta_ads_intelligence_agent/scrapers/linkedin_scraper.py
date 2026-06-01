import uuid
import time
import easyocr


class LinkedInAdsScraper:

    # ---------------------------------------------------
    # INIT
    # ---------------------------------------------------

    def __init__(self):

        print("LINKEDIN IMAGE ADS SCRAPER LOADED")

        self.reader = easyocr.Reader(
            ['en']
        )

        self.image_paths = []

    # ---------------------------------------------------
    # OPEN IMAGES
    # ---------------------------------------------------

    def open(self, image_paths):

        # support single image

        if isinstance(image_paths, str):

            image_paths = [image_paths]

        self.image_paths = image_paths

    # ---------------------------------------------------
    # OCR EXTRACT
    # ---------------------------------------------------

    def extract_text(self, image_path):

        results = self.reader.readtext(

            image_path,

            detail=0
        )

        return results

    # ---------------------------------------------------
    # DETECT CTA
    # ---------------------------------------------------

    def detect_cta(self, text):

        cta_keywords = [

            "Learn more",
            "Apply now",
            "Sign up",
            "Download",
            "Contact us",
            "Visit website",
            "Book now",
            "Register",
            "Subscribe",
            "Get started"
        ]

        for cta in cta_keywords:

            if cta.lower() in text.lower():

                return cta

        return None

    # ---------------------------------------------------
    # DETECT MEDIA TYPE
    # ---------------------------------------------------

    def detect_media_type(self, text):

        text = text.lower()

        if any(

            keyword in text

            for keyword in [

                "video",
                "watch",
                "play",
                "0:00"
            ]
        ):

            return "video"

        if any(

            keyword in text

            for keyword in [

                "carousel",
                "swipe"
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

            if (

                "Promoted" in clean_line

                or "Sponsored" in clean_line

            ) and i > 0:

                advertiser = lines[i - 1].strip()

                advertiser = advertiser.replace(
                    "\u200b",
                    ""
                ).strip()

                break

        if not advertiser:

            advertiser = "Unknown Advertiser"

        return advertiser

    # ---------------------------------------------------
    # EXTRACT PRIMARY TEXT
    # ---------------------------------------------------

    def extract_primary_text(self, lines, advertiser):

        skip_words = [

            advertiser,
            "Promoted",
            "Sponsored"
        ]

        candidates = []

        for line in lines:

            skip = False

            for word in skip_words:

                if word.lower() in line.lower():

                    skip = True
                    break

            if skip:
                continue

            if len(line) > 20:

                candidates.append(line)

        if len(candidates) > 0:

            return " ".join(
                candidates[:3]
            )

        return None

    # ---------------------------------------------------
    # PARSE SINGLE IMAGE
    # ---------------------------------------------------

    def parse_single_image(

        self,
        image_path,
        text_lines
    ):

        if len(text_lines) == 0:

            return None

        print("OCR TEXT:")
        print(text_lines)

        advertiser = self.extract_advertiser(
            text_lines
        )

        primary_text = self.extract_primary_text(

            text_lines,
            advertiser
        )

        full_text = " ".join(text_lines)

        media_type = self.detect_media_type(
            full_text
        )

        cta = self.detect_cta(
            full_text
        )

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
                "LinkedIn"
            ],

            "primary_text": primary_text,

            "headline": None,

            "description": None,

            "cta_text": cta,

            "landing_url": None,

            "media_type": media_type,

            "creative_image_url": image_path,

            "creative_video_url": None,

            "ad_snapshot_url": image_path,

            "raw_card_text": full_text
        }

        return ad

    # ---------------------------------------------------
    # COLLECT ADS
    # ---------------------------------------------------

    def collect_ads(self, max_ads=20):

        ads = []

        for image_path in self.image_paths:

            try:

                text_lines = self.extract_text(
                    image_path
                )

                ad = self.parse_single_image(

                    image_path,
                    text_lines
                )

                if ad:

                    ads.append(ad)

                if len(ads) >= max_ads:
                    break

            except Exception as e:

                print(e)

        print(f"FINAL LINKEDIN ADS: {len(ads)}")

        return ads

    # ---------------------------------------------------
    # CLOSE
    # ---------------------------------------------------

    def close(self):

        pass