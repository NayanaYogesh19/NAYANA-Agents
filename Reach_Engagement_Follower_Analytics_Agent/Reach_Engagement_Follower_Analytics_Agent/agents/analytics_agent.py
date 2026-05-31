from scrapers.instagram_scraper import InstagramScraper
from scrapers.facebook_scraper import FacebookScraper
from scrapers.linkedin_scraper import LinkedInScraper
from scrapers.youtube_scraper import YouTubeScraper

from utils.analytics import generate_summary


class ReachAnalyticsAgent:

    def __init__(self):

        self.instagram = InstagramScraper()

        self.facebook = FacebookScraper()

        self.linkedin = LinkedInScraper()

        self.youtube = YouTubeScraper()

    def run(
        self,
        instagram_url="",
        facebook_url="",
        linkedin_url="",
        youtube_url=""
    ):

        final_result = {}

        if instagram_url:

            final_result["instagram"] = (
                self.instagram.scrape(
                    instagram_url
                )
            )

        if facebook_url:

            final_result["facebook"] = (
                self.facebook.scrape(
                    facebook_url
                )
            )

        if linkedin_url:

            final_result["linkedin"] = (
                self.linkedin.scrape(
                    linkedin_url
                )
            )

        if youtube_url:

            final_result["youtube"] = (
                self.youtube.scrape(
                    youtube_url
                )
            )

        final_result["summary"] = (
            generate_summary(
                final_result
            )
        )

        return final_result