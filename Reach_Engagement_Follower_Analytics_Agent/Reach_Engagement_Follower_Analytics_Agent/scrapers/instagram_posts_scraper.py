import os
from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


class InstagramPostsScraper:

    def __init__(self):
        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

    def scrape_posts(self, username):

        run_input = {
            "usernames": [username],
            "resultsLimit": 10
        }

        run = self.client.actor(
            "apify/instagram-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        print(dataset_items)

        valid_posts = []

        for item in dataset_items:

            if (
                isinstance(item, dict)
                and item.get("likesCount") is not None
            ):
                valid_posts.append(item)

        if not valid_posts:
            return {
                "average_likes": 0,
                "average_comments": 0,
                "post_types": ["Unknown"],
                "content_angles": ["Branding"]
            }

        total_likes = 0
        total_comments = 0

        post_types = []

        captions = []

        for post in valid_posts:

            likes = post.get("likesCount", 0) or 0
            comments = post.get("commentsCount", 0) or 0

            total_likes += likes
            total_comments += comments

            media_type = post.get("type", "Unknown")

            post_types.append(media_type)

            caption = post.get("caption", "")

            captions.append(caption)

        count = len(valid_posts)

        avg_likes = total_likes / count
        avg_comments = total_comments / count

        unique_post_types = list(set(post_types))

        content_angles = self.detect_content_angles(
            captions
        )

        return {
            "average_likes": round(avg_likes, 2),
            "average_comments": round(avg_comments, 2),
            "post_types": unique_post_types,
            "content_angles": content_angles
        }

    def detect_content_angles(self, captions):

        combined = " ".join(captions).lower()

        angles = []

        if "offer" in combined or "buy" in combined:
            angles.append("Promotional")

        if "tips" in combined or "how" in combined:
            angles.append("Educational")

        if (
            "recipe" in combined
            or "food" in combined
            or "pickle" in combined
        ):
            angles.append("Food Content")

        if (
            "customer" in combined
            or "testimonial" in combined
            or "review" in combined
        ):
            angles.append("Social Proof")

        angles.append("Branding")

        return list(set(angles))