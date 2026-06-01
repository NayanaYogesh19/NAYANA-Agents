from backend.database.supabase_client import supabase_client
import logging
import re

logger = logging.getLogger(__name__)


class WebsiteRepository:

    def __init__(self):

        self.client = supabase_client.client

    # =================================================
    # GENERATE TABLE NAME
    # =================================================

    def generate_table_name(
        self,
        website_url: str
    ):

        clean = re.sub(
            r'https?://',
            '',
            website_url
        )

        clean = clean.replace(
            'www.',
            ''
        )

        clean = re.sub(
            r'[^a-zA-Z0-9]',
            '_',
            clean
        )

        clean = clean.strip("_")

        return f"{clean.lower()}_faqs"

    # =================================================
    # GET OR CREATE WEBSITE
    # =================================================

    def get_or_create_website(
        self,
        website_name: str,
        website_url: str
    ):

        try:

            print("\n====================")
            print("CHECKING WEBSITE")
            print("====================")
            print(website_url)

            # -----------------------------------------
            # CHECK EXISTING
            # -----------------------------------------

            existing = (
                self.client
                .table("websites")
                .select("*")
                .eq(
                    "website_url",
                    website_url
                )
                .execute()
            )

            print("\nEXISTING RESPONSE:")
            print(existing)

            # -----------------------------------------
            # WEBSITE EXISTS
            # -----------------------------------------

            if existing.data:

                print("\nWEBSITE EXISTS")

                logger.info(
                    f"Website exists: "
                    f"{website_url}"
                )

                return existing.data[0]

            # -----------------------------------------
            # CREATE TABLE NAME
            # -----------------------------------------

            table_name = self.generate_table_name(
                website_url
            )

            print("\nTABLE NAME:")
            print(table_name)

            # -----------------------------------------
            # INSERT WEBSITE
            # -----------------------------------------

            data = {

                "website_name": website_name,

                "website_url": website_url,

                "table_name": table_name
            }

            print("\nINSERTING WEBSITE:")
            print(data)

            response = (
                self.client
                .table("websites")
                .insert(data)
                .execute()
            )

            print("\nINSERT RESPONSE:")
            print(response)

            logger.info(
                f"Website created: "
                f"{website_url}"
            )

            return response.data[0]

        except Exception as e:

            print("\nWEBSITE REPOSITORY ERROR:")
            print(str(e))

            logger.error(
                f"Website repository error: {e}"
            )

            return None