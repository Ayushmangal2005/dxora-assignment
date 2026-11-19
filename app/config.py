"""Application configuration settings."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application configuration loaded from environment variables."""

    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "4000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

    # Google Gemini Settings (Primary Recommended)
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    # OpenAI Settings (Alternative Fallback)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Scraper Settings
    SCRAPE_TIMEOUT_SECONDS: float = float(os.getenv("SCRAPE_TIMEOUT_SECONDS", "15"))
    MAX_EXTRACTED_CHARACTERS: int = int(os.getenv("MAX_EXTRACTED_CHARACTERS", "18000"))


settings = Settings()
