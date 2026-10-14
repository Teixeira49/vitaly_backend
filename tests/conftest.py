"""Configure isolated settings before test modules import the application.

Supabase and ImageKit calls must be mocked by tests. pytest-socket blocks
outbound connections; Unix sockets remain available for TestClient's event loop.
"""

import os

from app.core.config import Settings, get_settings


# Never read local credentials, even when a developer has a populated .env.
Settings.model_config["env_file"] = None
os.environ.update(
    {
        "SUPABASE_URL": "http://127.0.0.1:54321",
        "SUPABASE_KEY": "test-supabase-key",
        "SECRET_KEY": "test-secret-key-not-for-production",
        "IMAGEKIT_PUBLIC_KEY": "",
        "IMAGEKIT_PRIVATE_KEY": "",
        "IMAGEKIT_URL_ENDPOINT": "",
    }
)
get_settings.cache_clear()
