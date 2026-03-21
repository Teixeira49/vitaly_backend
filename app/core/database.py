from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

def get_supabase_client() -> Client:
    """Initialize and return a Supabase python client."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Global client instance
supabase = get_supabase_client()
