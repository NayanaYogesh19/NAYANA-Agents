import os

from apify_client import ApifyClient
from dotenv import load_dotenv

from services.ai_analyzer import AIAnalyzer

load_dotenv()


class LinkedInScraper:

    def __init__(self):

        self.client = ApifyClient(
            os.getenv("APIFY_API_TOKEN")
        )

        self.ai = AIAnalyzer()

    def scrape(self, url):

        if "/company/" not in url:

            return {
                "platform": "LinkedIn",
                "error": "Only LinkedIn company URLs are supported"
            }

        return self.scrape_company_profile(
            url
        )

    def scrape_company_profile(self, url):

        run_input = {

            "companies": [
                url
            ],

            "includeCompanyDetails": True
        }

        run = self.client.actor(
            "harvestapi/linkedin-company"
        ).call(
            run_input=run_input
        )

        dataset_items = list(
            self.client.dataset(
                run.default_dataset_id
            ).iterate_items()
        )

        print(dataset_items)

        if not dataset_items:

            return {
                "platform": "LinkedIn",
                "profile_type": "Company",
                "message":
                    "LinkedIn company data not accessible"
            }

        data = dataset_items[0]

        print(data)

        company_name = data.get(
            "name",
            "Unknown"
        )

        followers = data.get(
            "followerCount",
            0
        )

        description = data.get(
            "description",
            ""
        )

        company_size = data.get(
            "employeeCount",
            "Unknown"
        )

        industry = "Unknown"

        if data.get("industries"):

            industry = data[
                "industries"
            ][0].get(
                "title",
                "Unknown"
            )

        website = data.get(
            "website",
            ""
        )

        full_text = f"""
LinkedIn Company Profile

Company Name:
{company_name}

Description:
{description}

Industry:
{industry}

Company Size:
{company_size}

Website:
{website}
"""

        ai_analysis = self.ai.analyze_social_profile(
            platform="LinkedIn",
            text=full_text
        )

        return {

            "platform": "LinkedIn",

            "profile_type": "Company",

            "company_name": company_name,

            "followers": followers,

            "industry": industry,

            "company_size": company_size,

            "website": website,

            "description": description,

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
                "Business Professionals"
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