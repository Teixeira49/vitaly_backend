import os
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings defined dynamically."""
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SECRET_KEY: str = "default-insecure-secret-key"  # Override in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    API_V1_STR: str = "/api/v1"

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
