"""Catálogos globales de consulta pública (estados, tipos de escuela, etc.)."""

from fastapi import APIRouter
from typing import List

from app.core.database import supabase
from app.core.openapi_responses import PUBLIC_RESPONSES
from app.schemas.responses import APIResponse
from app.schemas.school import StateResponse, SchoolTypeResponse, ClassroomCategoryResponse, SystemStatusResponse

router = APIRouter()


# PUBLIC_ROUTE
@router.get(
    "/states",
    response_model=APIResponse[List[StateResponse]],
    summary="Listar estados",
    description=(
        "Retorna el catálogo de estados del país activos y no eliminados. "
        "Se usa para poblar el selector de ubicación al registrar una escuela."
    ),
    responses=PUBLIC_RESPONSES,
)
def get_states():
    """Retorna el catálogo global de estados.

    Multi-tenancy:
        Catálogo global, sin alcance de escuela.

    RBAC:
        Ruta pública: no requiere token.

    Returns:
        APIResponse: Lista de estados activos; vacía si no hay ninguno.
    """
    response = supabase.table("states").select("id:state_id, name:state_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Estados obtenidos exitosamente")


# PUBLIC_ROUTE
@router.get(
    "/school-types",
    response_model=APIResponse[List[SchoolTypeResponse]],
    summary="Listar tipos de escuela",
    description=(
        "Retorna el catálogo de tipos de institución (pública, privada, etc.) "
        "activos y no eliminados."
    ),
    responses=PUBLIC_RESPONSES,
)
def get_school_types():
    """Retorna el catálogo global de tipos de escuela.

    Multi-tenancy:
        Catálogo global, sin alcance de escuela.

    RBAC:
        Ruta pública: no requiere token.

    Returns:
        APIResponse: Lista de tipos de escuela activos; vacía si no hay ninguno.
    """
    response = supabase.table("school_type").select("id, name:school_type_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Tipos de escuela obtenidos exitosamente")


# PUBLIC_ROUTE
@router.get(
    "/classroom-categories",
    response_model=APIResponse[List[ClassroomCategoryResponse]],
    summary="Listar categorías de salón",
    description=(
        "Retorna el catálogo de categorías o niveles educativos (Preescolar, "
        "Primaria, Bachillerato) activos y no eliminados."
    ),
    responses=PUBLIC_RESPONSES,
)
def get_classroom_categories():
    """Retorna el catálogo global de categorías de salón.

    Multi-tenancy:
        Catálogo global, sin alcance de escuela.

    RBAC:
        Ruta pública: no requiere token.

    Returns:
        APIResponse: Lista de categorías activas; vacía si no hay ninguna.
    """
    response = supabase.table("classroom_category").select("id, name:classroom_type_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Categorías de salón obtenidas exitosamente")


# PUBLIC_ROUTE
@router.get(
    "/system-status",
    response_model=APIResponse[List[SystemStatusResponse]],
    summary="Listar estatus del sistema",
    description=(
        "Retorna el catálogo de estatus que pueden tomar los registros del sistema "
        "(ej. inscrito, suspendido), activos y no eliminados."
    ),
    responses=PUBLIC_RESPONSES,
)
def get_system_status():
    """Retorna el catálogo global de estatus del sistema.

    Multi-tenancy:
        Catálogo global, sin alcance de escuela.

    RBAC:
        Ruta pública: no requiere token.

    Returns:
        APIResponse: Lista de estatus activos; vacía si no hay ninguno.
    """
    response = (
        supabase.table("system_status")
        .select("id:status_id, name:status_name")
        .eq("is_active", True)
        .eq("is_deleted", False)
        .execute()
    )
    return APIResponse(data=response.data, message="Estatus de sistema obtenidos exitosamente")
