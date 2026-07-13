import os

from apify_client import ApifyClient
from dotenv import load_dotenv

from tools.smm_scrapers.ai_analyzer import AIAnalyzer
from tools.smm_scrapers.youtube_posts_scraper import YouTubePostsScraper

load_dotenv()


class YouTubeScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

        self.ai = AIAnalyzer()

        self.posts_scraper = (
            YouTubePostsScraper()
        )

    def scrape(self, url):

        run_input = {
            "startUrls": [
                {
                    "url": url
                }
            ]
        }

        run = self.client.actor(
            "streamers/youtube-channel-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        print(dataset_items)

        if not dataset_items:

            return {
                "platform": "YouTube",
                "subscribers": "Not Found"
            }

        data = dataset_items[0]

        print(data)

        channel_name = data.get(
            "channelName",
            "Unknown"
        )

        subscribers = (
            data.get("subscribers")
            or data.get("subscriberCount")
            or data.get("subscribersCount")
            or data.get("channelSubscriberCount")
            or data.get("numberOfSubscribers")
            or 0
        )

        description = data.get(
            "description",
            ""
        )

        videos_data = (
            self.posts_scraper.scrape_videos(
                url
            )
        )

        full_text = f"""
YouTube Channel

Channel Name:
{channel_name}

Description:
{description}

Recent Video Titles:
{videos_data["captions"]}
"""

        ai_analysis = self.ai.analyze_social_profile(
            platform="YouTube",
            text=full_text
        )

        return {

            "platform": "YouTube",

            "channel_name": channel_name,

            "subscribers": subscribers,

            "average_views": videos_data[
                "average_views"
            ],

            "average_comments": videos_data[
                "average_comments"
            ],

            "video_types": videos_data[
                "video_types"
            ],

            "content_angles": ai_analysis.get(
                "content_angles",
                []
            ),

            "target_audience": ai_analysis.get(
                "target_audience",
                "YouTube Audience"
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