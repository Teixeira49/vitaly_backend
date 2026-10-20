"""Endpoints del rol representante."""

from fastapi import APIRouter, Depends

from app.api.deps import get_current_representante
from app.core.openapi_responses import PROTECTED_RESPONSES
from app.schemas.responses import APIResponse
from app.services.parent_service import parent_service
from app.core.database import supabase

router = APIRouter()


# ──────────────────────────────────────────────────────────
# POST - Vincular estudiantes autorizados al representante
# ──────────────────────────────────────────────────────────

@router.post(
    "/link-students",
    response_model=APIResponse[dict],
    summary="Vincular estudiantes autorizados",
    description=(
        "Busca los estudiantes cuyo campo 'authorization_number' contiene el "
        "documento de identidad del representante autenticado y crea la relación "
        "en 'student_representative'. Es idempotente: las vinculaciones ya "
        "existentes se reportan aparte en lugar de duplicarse."
    ),
    responses=PROTECTED_RESPONSES,
)
def link_authorized_students(
    parent_payload: dict = Depends(get_current_representante)
):
    """Vincula al representante autenticado con los estudiantes que lo autorizaron.

    Multi-tenancy:
        El alcance lo da el propio representante: solo se vinculan los estudiantes
        que declaran su documento de identidad. El usuario se deriva del token
        (parent_payload['sub']).

    RBAC:
        Requiere rol representante autenticado mediante Bearer token.

    Raises:
        HTTPException(404): Si el usuario no tiene un perfil de representante.
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
