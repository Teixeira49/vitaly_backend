from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.user import UserUpdate
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# Profile - Mi Perfil de Administrador
# ──────────────────────────────────────────────────────────

@router.get("/profile", response_model=APIResponse[dict])
def get_my_profile(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna el perfil del administrador de escuela autenticado.
    
    Incluye la información del usuario, la información del administrador 
    y datos básicos de la escuela a la que pertenece (nombre, año de fundación y dirección).
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_my_profile(user_id=user_id)
    return APIResponse(data=result, message="Perfil obtenido exitosamente")


@router.put("/profile", response_model=APIResponse[dict])
def update_my_profile(
    payload: UserUpdate,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Actualiza la información personal del administrador de escuela autenticado.
    
    Permite modificar: nombre, apellido, cédula (identity_number), 
    fecha de nacimiento (birthday), género, dirección y biografía.
    
    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.update_my_profile(
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Perfil actualizado exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Resumen / Métricas de Estudiantes
# ──────────────────────────────────────────────────────────

@router.get("/students/resume", response_model=APIResponse[dict])
def get_students_resume(
    category: int = Query(None, description="ID de la categoría del aula (ej. 1=PREESCOLAR). Filtra el resumen por categoría."),
    grade: int = Query(None, description="Nivel/grado del aula. Requiere 'category'."),
    section: str = Query(None, description="Letra de la sección (ej. 'A'). Requiere 'category' y 'grade'."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Resumen métrico de los estudiantes pertenecientes a la escuela del admin autenticado,
    correspondientes al año académico vigente.

    **Filtros opcionales (jerárquicos):**
    - **category**: Filtra por categoría de aula (classroom_category). Ej: 1=PREESCOLAR.
    - **grade**: Filtra por nivel/grado. *Requiere `category`.*
    - **section**: Filtra por sección (letra). *Requiere `category` y `grade`.*

    **Métricas:**
    - `total_students`: Número total de estudiantes en el alcance seleccionado.
    - `overweight_students`: Estudiantes con BMI > 24.9.
    - `malnourished_students`: Estudiantes con BMI < 18.5.
    - `active_cases`: Casos médicos activos (sin fecha de cierre ni diagnóstico final).
    - `optimal_students`: total_students - overweight - malnourished.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_students_resume(
        user_id=user_id,
        category=category,
        grade=grade,
        section=section,
    )
    return APIResponse(data=result, message="Resumen de estudiantes obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Historial Médico de un Estudiante
# ──────────────────────────────────────────────────────────

@router.get("/students/{student_id}/medical-history", response_model=APIResponse[dict])
def get_student_medical_history(
    student_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Lista paginada del historial médico (casos médicos) de un estudiante específico.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_medical_history(
        user_id=user_id,
        student_id=student_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Historial médico obtenido exitosamente")
