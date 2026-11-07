"""Salones, grados y secciones de la escuela del administrador autenticado."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.core.openapi_responses import TENANT_DETAIL_RESPONSES
from app.schemas.responses import APIResponse
from app.services.school_admin_service import school_admin_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# GET - Grados Académicos (Classrooms del año vigente)
# ──────────────────────────────────────────────────────────

@router.get("/", response_model=APIResponse[dict],
    summary="Listar grados del año vigente",
    description=(
        "Retorna de forma paginada los grados y salones de la escuela del administrador, "
        "restringidos al año académico vigente (is_current=True) y ordenados por categoría y "
        "nivel."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_academic_grades(
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista de forma paginada los grados de la escuela en el año vigente.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(404): Si no hay un año académico vigente, o si la escuela no
            tiene grados registrados en él. Este segundo 404 ante una colección
            vacía es comportamiento legado; se sigue en el issue #15.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_academic_grades(user_id=user_id, page=page, size=size)
    return APIResponse(data=result, message="Grados académicos obtenidos exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Estudiantes de un salón específico
# ──────────────────────────────────────────────────────────

@router.get("/{classroom_id}/students", response_model=APIResponse[dict],
    summary="Listar estudiantes de un salón",
    description=(
        "Retorna de forma paginada los estudiantes inscritos en el salón indicado, previa "
        "verificación de que el salón pertenece a la escuela del administrador."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_students_by_classroom(
    classroom_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista de forma paginada los estudiantes inscritos en un salón.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El salón se busca primero por su id y luego se compara su 'school_id'
        con el resuelto: si no coincide, responde 403, no 404.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el salón pertenece a otra escuela.
        HTTPException(404): Si el salón no existe, o si no tiene estudiantes
            registrados. Este segundo 404 es comportamiento legado (issue #15).
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

@router.get("/categories-summary", response_model=APIResponse[dict],
    summary="Resumir categorías y niveles",
    description=(
        "Retorna las combinaciones únicas de nivel y categoría presentes en los salones de la "
        "escuela para el año académico vigente. Con 'category_id' el resultado se restringe a "
        "los niveles de esa categoría."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_classroom_categories_summary(
    category_id: int = Query(None, description="ID de la categoría para filtrar los niveles (opcional)."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Resume los salones de la escuela agrupados por categoría y nivel.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(404): Si no hay un año académico vigente configurado.
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

@router.get("/categories-available", response_model=APIResponse[dict],
    summary="Listar categorías disponibles",
    description=(
        "Retorna las categorías (Preescolar, Primaria, etc.) que la escuela realmente usa en "
        "el año académico vigente. A diferencia de /categories-summary, no desglosa los "
        "niveles: sirve para poblar un selector sin ofrecer categorías vacías."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_available_classroom_categories(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista las categorías de salón en uso por la escuela este año.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(404): Si no hay un año académico vigente configurado.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_available_classroom_categories(user_id=user_id)
    return APIResponse(data=result, message="Categorías disponibles obtenidas exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Secciones disponibles para una categoría y nivel dados
# ──────────────────────────────────────────────────────────

@router.get("/categories/{category_id}/levels/{level}/sections", response_model=APIResponse[dict],
    summary="Listar secciones de un nivel",
    description=(
        "Retorna las secciones existentes para una combinación de categoría y nivel, por "
        "ejemplo A, B y C para Preescolar nivel 3. Con 'active=true' se restringe a los "
        "salones del año académico vigente."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_sections_by_category_and_level(
    category_id: int,
    level: int,
    active: bool = Query(False, description="Si es True, devuelve solo del año académico vigente"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista las secciones disponibles para una categoría y nivel dados.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(404): Si no hay un año académico vigente configurado.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_sections_by_category_and_level(
        user_id=user_id,
        category_id=category_id,
        level=level,
        active=active
    )
    return APIResponse(data=result, message="Secciones obtenidas exitosamente")
