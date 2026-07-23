from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralized application configuration powered by Pydantic Settings.
    
    Reads from environment variables and an optional .env file.
    Validates configuration types on startup so missing or malformed variables fail fast.
    """
    APP_NAME: str = "AI Customer Support Platform"
    ENVIRONMENT: str = "development"

    # Database Configuration
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ai_support_db"

    # Security & Authentication
    SECRET_KEY: str = "super-secret-production-jwt-key-change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 3600

    # AI Configuration (Gemini)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the Settings class.
    Using @lru_cache prevents re-reading the .env file on every dependency call.
    """
    return Settings()


settings = get_settings()
