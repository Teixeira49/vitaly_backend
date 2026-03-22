from fastapi import APIRouter, Depends, Query
from typing import List

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# GET - Resumen / Métricas de Estudiantes
# ──────────────────────────────────────────────────────────

@router.get("/students/resume", response_model=APIResponse[dict])
def get_students_resume(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Resumen métrico de los estudiantes pertenecientes a la escuela del admin autenticado.

    Métricas:
    - **total_students**: Número total de estudiantes vinculados a la escuela.
    - **overweight_students**: (Hardcodeado a 0) Estudiantes con sobrepeso.
    - **malnourished_students**: (Hardcodeado a 0) Estudiantes con desnutrición.
    - **active_cases**: (Hardcodeado a 0) Casos médicos activos.
    - **optimal_students**: total_students - overweight - malnourished.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_resume(user_id=user_id)
    return APIResponse(data=result, message="Resumen de estudiantes obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Grados Académicos (Classrooms del año vigente)
# ──────────────────────────────────────────────────────────

@router.get("/classrooms", response_model=APIResponse[dict])
def get_academic_grades(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de grados/salones de la escuela del admin, filtrados por el año académico vigente (is_current=True).
    Los resultados se ordenan por categoría y luego por nivel.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_academic_grades(user_id=user_id, page=page, size=size)
    return APIResponse(data=result, message="Grados académicos obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Estudiantes de un salón específico
# ──────────────────────────────────────────────────────────

@router.get("/classrooms/{classroom_id}/students", response_model=APIResponse[dict])
def get_students_by_classroom(
    classroom_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada de los estudiantes inscritos en un salón específico.
    Valida que el salón pertenezca a la misma escuela del admin autenticado.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_by_classroom(
        user_id=user_id,
        classroom_id=classroom_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Estudiantes del salón obtenidos exitosamente")
