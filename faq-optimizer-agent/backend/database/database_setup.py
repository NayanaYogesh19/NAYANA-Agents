from backend.database.supabase_client import supabase_client
import logging

logger = logging.getLogger(__name__)


class DatabaseSetup:
    """
    Database setup for dynamic website FAQ architecture

    Creates:
    - websites table only

    Dynamic FAQ tables are created automatically
    later inside faq_repository.py
    """

    def __init__(self):

        self.client = supabase_client.client

    def create_tables(self):

        try:

            # -----------------------------------------
            # CREATE WEBSITES TABLE
            # -----------------------------------------

            self.client.rpc(
                "exec_sql",
                {
                    "sql": """
                    CREATE TABLE IF NOT EXISTS websites (

                        id BIGSERIAL PRIMARY KEY,

                        website_name TEXT,

                        website_url TEXT UNIQUE NOT NULL,

                        table_name TEXT,

                        created_at TIMESTAMP DEFAULT NOW()

                    );
                    """
                }
            ).execute()

            logger.info(
                "websites table created successfully"
            )

            # -----------------------------------------
            # DISABLE RLS
            # -----------------------------------------

            self.client.rpc(
                "exec_sql",
                {
                    "sql": """
                    ALTER TABLE websites
                    DISABLE ROW LEVEL SECURITY;
                    """
                }
            ).execute()

            logger.info(
                "RLS disabled for websites table"
            )

            # -----------------------------------------
            # GRANT PERMISSIONS
            # -----------------------------------------

            self.client.rpc(
                "exec_sql",
                {
                    "sql": """
                    GRANT ALL PRIVILEGES
                    ON TABLE public.websites
                    TO service_role;

                    GRANT USAGE, SELECT
                    ON SEQUENCE websites_id_seq
                    TO service_role;
                    """
                }
            ).execute()

            logger.info(
                "Permissions granted successfully"
            )

        except Exception as e:

            logger.error(
                f"Database setup error: {e}"
            )