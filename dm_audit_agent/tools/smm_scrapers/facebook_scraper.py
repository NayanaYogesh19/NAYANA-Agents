import os

from apify_client import ApifyClient
from dotenv import load_dotenv

from tools.smm_scrapers.ai_analyzer import AIAnalyzer

load_dotenv()


class FacebookScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

        self.ai = AIAnalyzer()

    def scrape(self, url):

        page_name = self.extract_page_name(url)

        if not page_name:

            return {
                "platform": "Facebook",
                "error": "Invalid Facebook page URL"
            }

        run_input = {
            "startUrls": [
                {
                    "url": url
                }
            ],
            "resultsLimit": 5
        }

        run = self.client.actor(
            "apify/facebook-pages-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        if not dataset_items:

            return {
                "platform": "Facebook",
                "followers": "Not Found"
            }

        data = dataset_items[0]

        followers = (
            data.get("followers")
            or data.get("followersCount")
            or data.get("likes")
            or data.get("likesCount")
            or 0
        )

        description = (
            data.get("info")
            or data.get("description")
            or ""
        )

        full_text = f"""
        Facebook Page Name: {page_name}

        Description:
        {description}

        Followers:
        {followers}
        """

        ai_analysis = self.ai.analyze_social_profile(
            platform="Facebook",
            text=full_text
        )

        return {

            "platform": "Facebook",

            "page_name": page_name,

            "followers": followers,

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

    def extract_page_name(self, url):

        url = url.strip()

        if "facebook.com" not in url:
            return url

        cleaned = (
            url
            .replace("https://", "")
            .replace("http://", "")
            .replace("www.", "")
        )

        parts = cleaned.split("/")

        try:

            page_name = parts[1]

            return page_name.split("?")[0]

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