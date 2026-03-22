import os
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Dict

class Settings(BaseSettings):
    """Application settings defined dynamically."""
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SECRET_KEY: str = "default-insecure-secret-key"  # Override in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    API_V1_STR: str = "/api/v1"

    # Classroom level limits per category_id.
    # Keys are the category_id values stored in the DB:
    #   1 = Preescolar  (niveles 1-3)
    #   2 = Primaria    (niveles 1-6)
    #   3 = Bachillerato (niveles 1-5)
    CLASSROOM_LEVEL_LIMITS: Dict[int, int] = {
        1: 3,   # Preescolar
        2: 6,   # Primaria
        3: 5,   # Bachillerato
    }

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
