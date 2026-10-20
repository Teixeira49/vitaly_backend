"""Acceso a PostgreSQL/Supabase mediante el cliente síncrono supabase-py."""

from supabase import create_client, Client
from app.core.config import get_settings

settings = get_settings()

def get_supabase_client() -> Client:
    """Crea el cliente síncrono de supabase-py a partir de la configuración.

    Returns:
        Client: Cliente de Supabase listo para encadenar ``.table(...)``.

    Raises:
        Exception: Si la URL o la clave de Supabase son inválidas y la librería
            no puede construir el cliente.
    """
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

#: Cliente compartido por toda la aplicación. Es la única vía de acceso a datos
#: permitida: no se crean clientes ad-hoc ni se llama a la API REST directamente.
supabase = get_supabase_client()
