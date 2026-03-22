from fastapi import APIRouter
from typing import List
from app.core.database import supabase
from app.schemas.responses import APIResponse
from app.schemas.school import StateResponse, SchoolTypeResponse, ClassroomCategoryResponse, SystemStatusResponse

router = APIRouter()

@router.get("/states", response_model=APIResponse[List[StateResponse]])
def get_states():
    """
    Obtiene todos los estados disponibles que estén activos y no eliminados.
    No requiere protección JWT. # PUBLIC_ROUTE
    """
    response = supabase.table("states").select("id:state_id, name:state_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Estados obtenidos exitosamente")

@router.get("/school-types", response_model=APIResponse[List[SchoolTypeResponse]])
def get_school_types():
    """
    Obtiene todos los tipos de escuela disponibles que estén activos y no eliminados.
    No requiere protección JWT. # PUBLIC_ROUTE
    """
    response = supabase.table("school_type").select("id, name:school_type_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Tipos de escuela obtenidos exitosamente")

@router.get("/classroom-categories", response_model=APIResponse[List[ClassroomCategoryResponse]])
def get_classroom_categories():
    """
    Obtiene todas las categorías de salones disponibles que estén activas y no eliminadas.
    No requiere protección JWT. # PUBLIC_ROUTE
    """
    response = supabase.table("classroom_category").select("id, name:classroom_type_name").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Categorías de salón obtenidas exitosamente")

@router.get("/system-status", response_model=APIResponse[List[SystemStatusResponse]])
def get_system_status():
    """
    Obtiene todos los estatus de sistema disponibles que estén activos y no eliminados.
    No requiere protección JWT. # PUBLIC_ROUTE
    """
    response = (
        supabase.table("system_status")
        .select("id:status_id, name:status_name")
        .eq("is_active", True)
        .eq("is_deleted", False)
        .execute()
    )
    return APIResponse(data=response.data, message="Estatus de sistema obtenidos exitosamente")

