import os
import sys

from dotenv import load_dotenv

from pydantic_settings import BaseSettings

from pydantic import ConfigDict

# =====================================================
# WINDOWS UTF-8 FIX
# =====================================================

if sys.platform == 'win32':

    sys.stdout.reconfigure(
        encoding='utf-8'
    )

    sys.stderr.reconfigure(
        encoding='utf-8'
    )

# =====================================================
# LOAD ENV VARIABLES
# =====================================================

load_dotenv()

# =====================================================
# SETTINGS
# =====================================================

class Settings(BaseSettings):

    """
    Application Settings
    """

    # =================================================
    # OPENROUTER
    # =================================================

    openrouter_api_key: str = os.getenv(
        "OPENROUTER_API_KEY",
        ""
    )

    # =================================================
    # LANGSMITH / LANGCHAIN
    # =================================================

    langsmith_api_key: str = os.getenv(
        "LANGSMITH_API_KEY",
        ""
    )

    # IMPORTANT FIX
    # (prevents pydantic validation error)

    langchain_api_key: str = os.getenv(
        "LANGCHAIN_API_KEY",
        ""
    )

    langchain_tracing_v2: str = os.getenv(
        "LANGCHAIN_TRACING_V2",
        "false"
    )

    langchain_endpoint: str = os.getenv(
        "LANGCHAIN_ENDPOINT",
        "https://api.smith.langchain.com"
    )

    langchain_project: str = os.getenv(
        "LANGCHAIN_PROJECT",
        "faq-optimizer-agent"
    )

    # =================================================
    # SUPABASE
    # =================================================

    supabase_url: str = os.getenv(
        "SUPABASE_URL",
        ""
    )

    supabase_key: str = os.getenv(
        "SUPABASE_KEY",
        ""
    )

    # =================================================
    # APPLICATION
    # =================================================

    app_host: str = os.getenv(
        "APP_HOST",
        "0.0.0.0"
    )

    app_port: int = int(
        os.getenv(
            "APP_PORT",
            "8000"
        )
    )

    debug: bool = (

        os.getenv(
            "DEBUG",
            "false"
        ).lower() == "true"
    )

    # =================================================
    # PYDANTIC CONFIG
    # =================================================

    model_config = ConfigDict(

        env_file=".env",

        case_sensitive=False,

        extra="allow"
    )

    # =================================================
    # VALIDATE REQUIRED KEYS
    # =================================================

    def validate_required_keys(self):

        """
        Validate required environment variables
        """

        errors = []

        # ---------------------------------------------
        # OPENROUTER
        # ---------------------------------------------

        if not self.openrouter_api_key:

            errors.append(
                "OPENROUTER_API_KEY is missing"
            )

        # ---------------------------------------------
        # SUPABASE
        # ---------------------------------------------

        if not self.supabase_url:

            errors.append(
                "SUPABASE_URL is missing"
            )

        if not self.supabase_key:

            errors.append(
                "SUPABASE_KEY is missing"
            )

        # ---------------------------------------------
        # THROW ERROR
        # ---------------------------------------------

        if errors:

            raise ValueError(

                "Missing environment variables:\n"
                + "\n".join(errors)
            )

        return True

# =====================================================
# SETTINGS INSTANCE
# =====================================================

settings = Settings()