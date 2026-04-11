from fastapi import APIRouter, Depends

from app.api.deps import get_current_representante
from app.schemas.responses import APIResponse
from app.services.parent_service import parent_service
from app.core.database import supabase

router = APIRouter()


# ──────────────────────────────────────────────────────────
# POST - Vincular estudiantes autorizados al representante
# ──────────────────────────────────────────────────────────

@router.post("/link-students", response_model=APIResponse[dict])
def link_authorized_students(
    parent_payload: dict = Depends(get_current_representante)
):
    """
    Busca en la tabla de estudiantes aquellos cuyo campo `authorization_number`
    contenga el número de identidad del representante autenticado.

    Si encuentra coincidencias, crea automáticamente la relación en `student_representative`.
    Evita crear relaciones duplicadas.

    Requiere JWT (representante).
    """
    user_id = int(parent_payload["sub"])

    # Obtener el identity_number del usuario autenticado
    user_response = supabase.table("user").select("identity_number").eq("id", user_id).execute()
    if not user_response.data or not user_response.data[0].get("identity_number"):
        return APIResponse(
            data=None,
            message="No se encontró un número de identidad asociado a tu perfil."
        )

    identity_number = user_response.data[0]["identity_number"]
    result = parent_service.link_students_by_identity(user_id=user_id, identity_number=identity_number)
    return APIResponse(data=result, message=result["message"])
