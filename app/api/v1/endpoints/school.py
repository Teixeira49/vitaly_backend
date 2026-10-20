"""Consulta pública del directorio de escuelas registradas."""

from fastapi import APIRouter
from typing import List

from app.core.database import supabase
from app.core.openapi_responses import PUBLIC_RESPONSES
from app.schemas.responses import APIResponse
from app.schemas.school import SchoolBasicResponse

router = APIRouter()


# PUBLIC_ROUTE
@router.get(
    "",
    response_model=APIResponse[List[SchoolBasicResponse]],
    summary="Listar escuelas públicas",
    description=(
        "Retorna las escuelas activas y no eliminadas con su información base. "
        "Alimenta el selector de institución del formulario de registro de "
        "administradores de escuela, por lo que no requiere autenticación."
    ),
    responses=PUBLIC_RESPONSES,
)
def get_schools():
    """Retorna el directorio público de escuelas activas.

    Multi-tenancy:
        Expone deliberadamente todas las escuelas: es un directorio previo al
        registro, cuando el usuario todavía no pertenece a ninguna.

    RBAC:
        Ruta pública: no requiere token.

    Returns:
        APIResponse: Lista de escuelas con ``sch_id``, ``name``,
        ``year_foundation``, ``state`` y ``rif``; vacía si no hay ninguna activa.
    """
    response = supabase.table("school").select("sch_id, name, year_foundation, state, rif").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Escuelas obtenidas exitosamente")
