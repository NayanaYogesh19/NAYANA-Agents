"""
config.py — Centralised settings loaded from .env
"""
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    openai_api_key: str  = Field(..., validation_alias="OPENROUTER_API_KEY")
    tavily_api_key: str  = Field(..., validation_alias="TAVILY_API_KEY")
    host:           str  = Field("0.0.0.0", validation_alias="HOST")
    port:           int  = Field(8000,       validation_alias="PORT")
    debug:          bool = Field(False,      validation_alias="DEBUG")
    output_dir:     str  = Field("./output", validation_alias="OUTPUT_DIR")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
os.makedirs(settings.output_dir, exist_ok=True)
