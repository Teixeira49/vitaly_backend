from fastapi import APIRouter
from app.api.v1.endpoints import auth, admin, admin_school, catalogs, school, academic_year, school_admin

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administrador de Sistema"])
api_router.include_router(admin_school.router, prefix="/admin/schools", tags=["Administrador de Sistema - Feat. Escuela"])
api_router.include_router(catalogs.router, prefix="/catalogs", tags=["Catálogos Públicos"])
api_router.include_router(school.router, prefix="/schools", tags=["Escuelas Públicas"])
api_router.include_router(academic_year.router, prefix="/academic-year", tags=["Año Académico"])
api_router.include_router(school_admin.router, prefix="/school-admin", tags=["Administrador de Escuela"])
