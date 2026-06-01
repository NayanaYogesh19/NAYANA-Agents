from backend.database.supabase_client import supabase_client

import logging
import re
import time

logger = logging.getLogger(__name__)


class FAQRepository:

    def __init__(self):

        self.client = supabase_client.client

    # =================================================
    # GENERATE SAFE TABLE NAME
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

        table_name = (
            f"{clean.lower()}_faqs"
        )

        return table_name

    # =================================================
    # CREATE WEBSITE FAQ TABLE
    # =================================================

    def create_website_table(
        self,
        table_name: str
    ):

        try:

            print("\n====================")
            print("CREATING TABLE")
            print("====================")
            print(table_name)

            # -----------------------------------------
            # USE DYNAMIC SQL FUNCTION
            # -----------------------------------------

            response = self.client.rpc(

                "create_dynamic_faq_table",

                {
                    "table_name": table_name
                }

            ).execute()

            print("\nTABLE CREATE RESPONSE:")
            print(response)

            logger.info(
                f"Table ready: {table_name}"
            )

            # -----------------------------------------
            # WAIT FOR SUPABASE SCHEMA CACHE
            # -----------------------------------------

            time.sleep(2)

            return True

        except Exception as e:

            print("\nTABLE CREATE ERROR:")
            print(str(e))

            logger.error(
                f"Create table error: {e}"
            )

            return False

    # =================================================
    # CHECK TABLE EXISTS
    # =================================================

    def check_table_exists(
        self,
        table_name: str
    ):

        try:

            response = (

                self.client

                .table(table_name)

                .select("*")

                .limit(1)

                .execute()
            )

            return True

        except Exception as e:

            logger.error(
                f"Table existence check failed: {e}"
            )

            return False

    # =================================================
    # INSERT FAQ
    # =================================================

    def create_faq(
        self,
        website_url: str,
        topic: str,
        question: str,
        answer: str,
        category: str
    ):

        try:

            # -----------------------------------------
            # GENERATE TABLE NAME
            # -----------------------------------------

            table_name = self.generate_table_name(
                website_url
            )

            print("\n====================")
            print("TABLE NAME")
            print("====================")
            print(table_name)

            # -----------------------------------------
            # CREATE TABLE
            # -----------------------------------------

            table_created = (

                self.create_website_table(
                    table_name
                )
            )

            if not table_created:

                logger.error(
                    "Failed to create table"
                )

                return None

            # -----------------------------------------
            # VERIFY TABLE EXISTS
            # -----------------------------------------

            table_exists = (

                self.check_table_exists(
                    table_name
                )
            )

            if not table_exists:

                logger.error(
                    f"Table not found: {table_name}"
                )

                return None

            # -----------------------------------------
            # FAQ DATA
            # -----------------------------------------

            data = {

                "topic": topic,

                "question": question,

                "answer": answer,

                "category": category,

                "impressions": 0,

                "clicks": 0,

                "ctr": 0.00
            }

            print("\n====================")
            print("INSERTING FAQ")
            print("====================")
            print(data)

            # -----------------------------------------
            # INSERT FAQ
            # -----------------------------------------

            response = (

                self.client

                .table(table_name)

                .insert(data)

                .execute()
            )

            print("\nINSERT RESPONSE:")
            print(response)

            logger.info(
                f"FAQ stored successfully "
                f"in {table_name}"
            )

            # -----------------------------------------
            # RETURN INSERTED DATA
            # -----------------------------------------

            if response.data:

                return response.data[0]

            return None

        except Exception as e:

            print("\nFAQ INSERT ERROR:")
            print(str(e))

            logger.error(
                f"FAQ insert error: {e}"
            )

            return None

    # =================================================
    # GET FAQS FROM WEBSITE TABLE
    # =================================================

    def get_faqs(
        self,
        website_url: str
    ):

        try:

            table_name = self.generate_table_name(
                website_url
            )

            response = (

                self.client

                .table(table_name)

                .select("*")

                .execute()
            )

            return response.data

        except Exception as e:

            logger.error(
                f"Get FAQs error: {e}"
            )

            return []

    # =================================================
    # GET FAQ COUNT
    # =================================================

    def get_faq_count(
        self,
        website_url: str
    ):

        try:

            faqs = self.get_faqs(
                website_url
            )

            return len(faqs)

        except Exception as e:

            logger.error(
                f"FAQ count error: {e}"
            )

            return 0

    # =================================================
    # GET FAQS BY COMPANY
    # =================================================

    def get_faqs_by_company(
        self,
        company_name: str
    ):

        try:

            table_name = self.generate_table_name(
                company_name
            )

            print("\n====================")
            print("FETCHING FAQS")
            print("====================")
            print(table_name)

            # -----------------------------------------
            # CHECK TABLE EXISTS
            # -----------------------------------------

            table_exists = (

                self.check_table_exists(
                    table_name
                )
            )

            if not table_exists:

                logger.info(
                    f"No table found for "
                    f"{table_name}"
                )

                return []

            # -----------------------------------------
            # FETCH FAQS
            # -----------------------------------------

            response = (

                self.client

                .table(table_name)

                .select("*")

                .execute()
            )

            if response.data:

                logger.info(
                    f"Fetched "
                    f"{len(response.data)} FAQs "
                    f"from {table_name}"
                )

                return response.data

            return []

        except Exception as e:

            print("\nFETCH FAQ ERROR:")
            print(str(e))

            logger.error(
                f"Fetch FAQs error: {e}"
            )

            return []