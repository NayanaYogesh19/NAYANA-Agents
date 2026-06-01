from apify_client import ApifyClient
from dotenv import load_dotenv
import os
import time
import uuid


# ---------------------------------------------------
# LOAD ENV
# ---------------------------------------------------

load_dotenv()


class GoogleAdsScraper:

    # ---------------------------------------------------
    # INIT
    # ---------------------------------------------------

    def __init__(self):

        print("APIFY GOOGLE SCRAPER LOADED")

        token = os.getenv("APIFY_TOKEN")

        print("TOKEN:", token)

        if not token:

            raise Exception(
                "APIFY_TOKEN not found in .env file"
            )

        self.client = ApifyClient(token)

        self.url = None

    # ---------------------------------------------------
    # OPEN URL
    # ---------------------------------------------------

    def open(self, url):

        self.url = url

    # ---------------------------------------------------
    # COLLECT ADS
    # ---------------------------------------------------

    def collect_ads(self, max_ads=20):

        ads = []

        # ---------------------------------------------------
        # UNIQUE SIGNATURE STORAGE
        # ---------------------------------------------------

        collected_texts = set()

        # ---------------------------------------------------
        # ACTOR INPUT
        # ---------------------------------------------------

        run_input = {

            "startUrls": [

                {
                    "url": self.url
                }
            ],

            "maxItems": max_ads
        }

        print("RUN INPUT:")
        print(run_input)

        # ---------------------------------------------------
        # RUN ACTOR
        # ---------------------------------------------------

        run = self.client.actor(
            "lexis-solutions/google-ads-scraper"
        ).call(

            run_input=run_input
        )

        print("ACTOR RUN COMPLETED")

        # ---------------------------------------------------
        # GET DATASET
        # ---------------------------------------------------

        dataset_items = list(

            self.client.dataset(
                run["defaultDatasetId"]
            ).iterate_items()
        )

        print(
            f"TOTAL ADS SCRAPED: {len(dataset_items)}"
        )

        # ---------------------------------------------------
        # FORMAT ADS
        # ---------------------------------------------------

        for item in dataset_items:

            print("RAW ITEM:")
            print(item)
            print("--------------------------------")

            # ---------------------------------------------------
            # MEDIA DETECTION
            # ---------------------------------------------------

            media_type = "image"

            video_url = None

            image_url = None

            # ---------------------------------------------------
            # VIDEO FIELDS
            # ---------------------------------------------------

            possible_video_fields = [

                item.get("videoUrl"),
                item.get("videoURL"),
                item.get("video"),
                item.get("videoUrls"),
                item.get("video_urls"),
                item.get("mediaUrl"),
                item.get("media_url"),
                item.get("creativeUrl")
            ]

            # ---------------------------------------------------
            # IMAGE FIELDS
            # ---------------------------------------------------

            possible_image_fields = [

                item.get("imageUrl"),
                item.get("imageURL"),
                item.get("image"),
                item.get("thumbnail"),
                item.get("thumbnailUrl")
            ]

            # ---------------------------------------------------
            # DETECT VIDEO
            # ---------------------------------------------------

            for field in possible_video_fields:

                if not field:
                    continue

                field_str = str(field).lower()

                if any(

                    ext in field_str

                    for ext in [

                        ".mp4",
                        ".webm",
                        ".mov",
                        "video",
                        "youtube"
                    ]
                ):

                    video_url = field

                    media_type = "video"

                    break

            # ---------------------------------------------------
            # DETECT IMAGE
            # ---------------------------------------------------

            for field in possible_image_fields:

                if field:

                    image_url = field

                    break

            # ---------------------------------------------------
            # CAROUSEL DETECTION
            # ---------------------------------------------------

            if item.get("carousel"):

                media_type = "carousel"

            # ---------------------------------------------------
            # TYPE FIELD DETECTION
            # ---------------------------------------------------

            possible_type_fields = [

                item.get("mediaType"),
                item.get("creativeType"),
                item.get("assetType"),
                item.get("type"),
                item.get("format")
            ]

            for field in possible_type_fields:

                if not field:
                    continue

                field_str = str(field).lower()

                if "video" in field_str:

                    media_type = "video"

                elif "carousel" in field_str:

                    media_type = "carousel"

            # ---------------------------------------------------
            # EXTRACT IMPORTANT FIELDS
            # ---------------------------------------------------

            advertiser_name = item.get(
                "advertiserName"
            ) or item.get(
                "advertiser"
            ) or "Unknown Advertiser"

            headline = item.get(
                "headline"
            )

            landing_url = item.get(
                "landingPage"
            ) or item.get(
                "landingUrl"
            )

            # ---------------------------------------------------
            # CREATE UNIQUE SIGNATURE
            # ---------------------------------------------------

            signature = (

                str(advertiser_name)
                + str(headline)
                + str(landing_url)
                + str(media_type)
            )

            # ---------------------------------------------------
            # REMOVE TRUE DUPLICATES ONLY
            # ---------------------------------------------------

            if signature in collected_texts:
                continue

            collected_texts.add(signature)

            # ---------------------------------------------------
            # BUILD AD OBJECT
            # ---------------------------------------------------

            ad = {

                "ad_library_id": str(
                    uuid.uuid4()
                ),

                "advertiser_name": advertiser_name,

                "ad_status": item.get(
                    "status",
                    "Active"
                ),

                "date_started": item.get(
                    "firstShown"
                ) or item.get(
                    "dateShown"
                ),

                "date_scraped": time.strftime(
                    "%Y-%m-%d"
                ),

                "platforms": item.get(
                    "platforms",
                    ["Google"]
                ),

                "primary_text": (

                    item.get("primaryText")

                    or item.get("adText")

                    or item.get("description")

                    or item.get("headline")
                ),

                "headline": headline,

                "description": item.get(
                    "description"
                ),

                "cta_text": item.get(
                    "cta"
                ),

                "landing_url": landing_url,

                "media_type": media_type,

                "creative_image_url": image_url,

                "creative_video_url": video_url,

                "ad_snapshot_url": item.get(
                    "adUrl"
                ) or self.url
            }

            ads.append(ad)

        print(f"FINAL GOOGLE ADS: {len(ads)}")

        return ads

    # ---------------------------------------------------
    # CLOSE
    # ---------------------------------------------------

    def close(self):

        pass