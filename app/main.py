from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import validation_exception_handler, http_exception_handler
from app.core.database import supabase
from app.core.openapi import setup_openapi, tags_metadata
from app.utils.html.index import ROOT_HTML
from app.utils.html.health import HEALTH_HTML

settings = get_settings()


app = FastAPI(
    title="Vitaly Backend API",
    version="0.4.0",
    docs_url=None,
    redoc_url=None,
    openapi_tags=tags_metadata
)

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configurar rutas de documentación OpenAPI personalizadas
setup_openapi(app)



# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# PUBLIC_ROUTE
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def root():
    """Sirve la página de bienvenida de la API.

    Returns:
        str: HTML estático con los enlaces a la documentación interactiva.
    """
    return ROOT_HTML

# PUBLIC_ROUTE
@app.get("/health")
async def health_check():
    """Verifica el estado de la API y su conexión con la base de datos.

    Ejecuta una consulta mínima contra Supabase para distinguir "la API responde"
    de "la API responde y la base de datos está accesible".

    Returns:
        dict: ``status``, ``database`` (``connected`` o el detalle del fallo),
        ``version`` y ``app_name``. Responde 200 incluso con la base caída, para
        que el chequeo distinga ambos estados en lugar de fallar.
    """
    try:
        # Intenta una operación mínima para validar la conexión con Supabase
        supabase.table("system_status").select("*").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"disconnected: {str(e)}"
    
    return {
        "status": "online",
        "database": db_status,
        "version": app.version,
        "app_name": app.title
    }

# PUBLIC_ROUTE
@app.get("/health-visual", response_class=HTMLResponse, include_in_schema=False)
async def health_visual():
    """Retorna el estado de salud del sistema como una página HTML legible.

    Equivalente visual de ``/health``, pensado para revisión manual en el navegador.

    Returns:
        str: HTML con el estado de la API y de la base de datos.
    """
    try:
        supabase.table("system_status").select("*").limit(1).execute()
        db_status = "Connected"
    except:
        db_status = "Disconnected"
    
    # Inyectar datos en el HTML
    return HEALTH_HTML.format(
        status="Online",
        status_class="online",
        database=db_status,
        version=app.version,
        app_name=app.title
    )
