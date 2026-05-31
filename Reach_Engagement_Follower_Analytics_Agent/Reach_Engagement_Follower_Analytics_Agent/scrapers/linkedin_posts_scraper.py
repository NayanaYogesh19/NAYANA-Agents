import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


class LinkedInPostsScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

    def scrape_posts(self, url):

        run_input = {
            "profileUrls": [url],
            "postsLimit": 10
        }

        run = self.client.actor(
            "dev_fusion/linkedin-profile-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        if not dataset_items:

            return {

                "average_likes": 0,

                "average_comments": 0,

                "post_types": [],

                "captions": []
            }

        data = dataset_items[0]

        posts = data.get(
            "posts",
            []
        )

        if not posts:

            return {

                "average_likes": 0,

                "average_comments": 0,

                "post_types": [],

                "captions": []
            }

        total_likes = 0

        total_comments = 0

        captions = []

        post_types = []

        valid_posts = 0

        for post in posts:

            likes = (
                post.get("likesCount")
                or post.get("numLikes")
                or 0
            )

            comments = (
                post.get("commentsCount")
                or post.get("numComments")
                or 0
            )

            text = (
                post.get("text")
                or post.get("content")
                or ""
            )

            media_type = (
                post.get("mediaType")
                or "Text"
            )

            total_likes += likes

            total_comments += comments

            captions.append(text)

            detected_type = self.detect_post_type(
                media_type
            )

            post_types.append(
                detected_type
            )

            valid_posts += 1

        if valid_posts == 0:

            return {

                "average_likes": 0,

                "average_comments": 0,

                "post_types": [],

                "captions": []
            }

        average_likes = (
            total_likes / valid_posts
        )

        average_comments = (
            total_comments / valid_posts
        )

        unique_post_types = list(
            set(post_types)
        )

        return {

            "average_likes": round(
                average_likes,
                2
            ),

            "average_comments": round(
                average_comments,
                2
            ),

            "post_types": unique_post_types,

            "captions": captions
        }

    def detect_post_type(
        self,
        media_type
    ):

        media_type = str(
            media_type
        ).lower()

        if "video" in media_type:
            return "Videos"

        if "image" in media_type:
            return "Image Posts"

        if "document" in media_type:
            return "Carousels"

        return "Text Posts"