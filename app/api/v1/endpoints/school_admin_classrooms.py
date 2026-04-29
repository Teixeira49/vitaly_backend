from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# GET - Grados Académicos (Classrooms del año vigente)
# ──────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[dict])
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

@router.get("/{classroom_id}/students", response_model=APIResponse[dict])
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


# ──────────────────────────────────────────────────────────
# GET - Resumen de categorías/niveles del año académico vigente
# ──────────────────────────────────────────────────────────

@router.get("/categories-summary", response_model=APIResponse[dict])
def get_classroom_categories_summary(
    category_id: int = Query(None, description="ID de la categoría para filtrar los niveles (opcional)."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna las combinaciones únicas de (level, classroom_category_id, classroom_type_name)
    presentes en los salones de la escuela para el año académico vigente.

    Si se proporciona `category_id`, el resultado se filtrará para devolver únicamente 
    los niveles correspondientes a esa categoría específica.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_classroom_categories_summary(
        user_id=user_id,
        category_id=category_id
    )
    return APIResponse(data=result, message="Resumen de categorías obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Lista simple de categorías disponibles para la escuela
# ──────────────────────────────────────────────────────────

@router.get("/categories-available", response_model=APIResponse[dict])
def get_available_classroom_categories(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna la lista única de categorías (PREESCOLAR, PRIMARIA, etc.) disponibles 
    en la escuela para el año académico vigente.
    
    A diferencia de /categories-summary, este endpoint no incluye los niveles (grados),
    solo las categorías principales.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_available_classroom_categories(user_id=user_id)
    return APIResponse(data=result, message="Categorías disponibles obtenidas exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Secciones disponibles para una categoría y nivel dados
# ──────────────────────────────────────────────────────────

@router.get("/categories/{category_id}/levels/{level}/sections", response_model=APIResponse[dict])
def get_sections_by_category_and_level(
    category_id: int,
    level: int,
    active: bool = Query(False, description="Si es True, devuelve solo del año académico vigente"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Retorna las secciones disponibles para una combinación específica de classroom_category (category_id) y level.
    Si active=True, filtra para retornar solo las del año académico vigente.

    Ejemplo: category_id=1, level=3 → secciones A, B, C disponibles.

    Requiere JWT (admin_escuela).
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_sections_by_category_and_level(
        user_id=user_id,
        category_id=category_id,
        level=level,
        active=active
    )
    return APIResponse(data=result, message="Secciones obtenidas exitosamente")
