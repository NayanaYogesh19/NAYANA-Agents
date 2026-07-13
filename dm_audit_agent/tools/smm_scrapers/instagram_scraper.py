import os

from apify_client import ApifyClient
from dotenv import load_dotenv

from tools.smm_scrapers.ai_analyzer import AIAnalyzer

load_dotenv()


class InstagramScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

        self.ai = AIAnalyzer()

    def scrape(self, url):

        username = self.extract_username(url)

        if not username:

            return {
                "platform": "Instagram",
                "error": "Invalid Instagram profile URL"
            }

        run_input = {
            "usernames": [username]
        }

        run = self.client.actor(
            "apify/instagram-profile-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        if not dataset_items:

            return {
                "platform": "Instagram",
                "followers": "Not Found"
            }

        data = dataset_items[0]

        followers = data.get(
            "followersCount",
            0
        )

        posts = data.get(
            "postsCount",
            0
        )

        following = (
            data.get("followsCount")
            or data.get("followingCount")
            or "Not Public"
        )

        biography = data.get(
            "biography",
            ""
        )

        full_text = f"""
        Instagram Username: {username}

        Biography:
        {biography}

        Followers:
        {followers}

        Posts:
        {posts}
        """

        ai_analysis = self.ai.analyze_social_profile(
            platform="Instagram",
            text=full_text
        )

        return {

            "platform": "Instagram",

            "followers": followers,

            "following": following,

            "posts": posts,

            "estimated_average_likes": self.estimate_likes(
                followers
            ),

            "estimated_average_comments": self.estimate_comments(
                followers
            ),

            "post_types": ai_analysis.get(
                "post_types",
                []
            ),

            "content_angles": ai_analysis.get(
                "content_angles",
                []
            ),

            "target_audience": ai_analysis.get(
                "target_audience",
                "Unknown"
            ),

            "brand_tone": ai_analysis.get(
                "brand_tone",
                "Professional"
            ),

            "recommended_strategy": ai_analysis.get(
                "recommended_strategy",
                []
            )
        }

    def extract_username(self, url):

        url = url.strip()

        if "instagram.com" not in url:
            return url

        cleaned = (
            url
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
        )

        parts = cleaned.split("/")

        try:

            username = parts[1]

            invalid_parts = [
                "reel",
                "p",
                "tv",
                "stories"
            ]

            if username in invalid_parts:
                return None

            return username.split("?")[0]

        except:
            return None

    def estimate_likes(self, followers):

        try:

            followers = int(followers)

        except:

            return "Unknown"

        if followers < 1000:
            return "20-50"

        elif followers < 10000:
            return "50-300"

        elif followers < 50000:
            return "300-1500"

        return "1500+"

    def estimate_comments(self, followers):

        try:

            followers = int(followers)

        except:

            return "Unknown"

        if followers < 1000:
            return "2-10"

        elif followers < 10000:
            return "10-40"

        elif followers < 50000:
            return "40-150"

        return "150+"