from fastapi import APIRouter
from typing import List
from app.core.database import supabase
from app.schemas.responses import APIResponse
from app.schemas.school import SchoolBasicResponse

router = APIRouter()

@router.get("", response_model=APIResponse[List[SchoolBasicResponse]])
def get_schools():
    """
    Obtiene todas las escuelas disponibles que estén activas y no eliminadas.
    No requiere protección JWT.
    Retorna información base: sch_id, name, year_foundation, state y rif.
    """
    response = supabase.table("school").select("sch_id, name, year_foundation, state, rif").eq("is_active", True).eq("is_deleted", False).execute()
    return APIResponse(data=response.data, message="Escuelas obtenidas exitosamente")
