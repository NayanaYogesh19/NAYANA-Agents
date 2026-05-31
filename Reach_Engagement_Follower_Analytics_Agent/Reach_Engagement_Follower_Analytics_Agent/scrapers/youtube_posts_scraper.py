import os

from apify_client import ApifyClient
from dotenv import load_dotenv

load_dotenv()


class YouTubePostsScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

    def scrape_videos(self, channel_url):

        run_input = {
            "startUrls": [
                {
                    "url": channel_url
                }
            ],
            "maxResults": 10
        }

        run = self.client.actor(
            "streamers/youtube-scraper"
        ).call(run_input=run_input)

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        print(dataset_items)

        if not dataset_items:

            return {

                "average_views": 0,

                "average_comments": 0,

                "video_types": [],

                "captions": []
            }

        total_views = 0

        total_comments = 0

        captions = []

        video_types = []

        valid_videos = 0

        for item in dataset_items:

            views = (
                item.get("viewCount")
                or 0
            )

            comments = (
                item.get("commentsCount")
                or 0
            )

            title = (
                item.get("title")
                or ""
            )

            duration = (
                item.get("duration")
                or ""
            )

            total_views += views

            total_comments += comments

            captions.append(title)

            duration_str = str(duration)

            if ":" in duration_str:

                parts = duration_str.split(":")

                if len(parts) == 1:

                    seconds = int(parts[0])

                elif len(parts) == 2:

                    minutes = int(parts[0])

                    seconds_only = int(parts[1])

                    seconds = (
                        minutes * 60
                    ) + seconds_only

                else:

                    hours = int(parts[0])

                    minutes = int(parts[1])

                    seconds_only = int(parts[2])

                    seconds = (
                        hours * 3600
                    ) + (
                        minutes * 60
                    ) + seconds_only

            else:

                try:

                    seconds = int(duration_str)

                except:

                    seconds = 0

            if seconds <= 60:

                video_types.append(
                    "Shorts"
                )

            else:

                video_types.append(
                    "Long Videos"
                )

            valid_videos += 1

        if valid_videos == 0:

            return {

                "average_views": 0,

                "average_comments": 0,

                "video_types": [],

                "captions": []
            }

        average_views = (
            total_views / valid_videos
        )

        average_comments = (
            total_comments / valid_videos
        )

        unique_video_types = list(
            set(video_types)
        )

        return {

            "average_views": round(
                average_views,
                2
            ),

            "average_comments": round(
                average_comments,
                2
            ),

            "video_types": unique_video_types,

            "captions": captions
        }