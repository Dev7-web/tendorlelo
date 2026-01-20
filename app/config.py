"""
Application Configuration
"""

from __future__ import annotations

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_NAME: str = "tender-matching-system"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Database
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "tender_db"

    # API Keys
    GEMINI_API_KEY: str = ""

    # File Storage
    TENDER_PDF_DIR: str = "data/pdfs/tenders"
    PROFILE_UPLOAD_DIR: str = "data/pdfs/profiles"
    MAX_UPLOAD_SIZE: int = 52428800  # 50MB

    # Scraping
    SCRAPE_MAX_PAGES: int = 10
    SCRAPE_MAX_BIDS: int = 200
    SCRAPE_MIN_DELAY: int = 2
    SCRAPE_MAX_DELAY: int = 5
    SCRAPER_HEADLESS: bool = True

    # LLM
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Embedding
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # Scheduler
    ENABLE_SCHEDULER: bool = True
    SCRAPE_INTERVAL_HOURS: int = 6
    PROCESS_INTERVAL_MINUTES: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()

# Create directories for local storage
os.makedirs(settings.TENDER_PDF_DIR, exist_ok=True)
os.makedirs(settings.PROFILE_UPLOAD_DIR, exist_ok=True)
