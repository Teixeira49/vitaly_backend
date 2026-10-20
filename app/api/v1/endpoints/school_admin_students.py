"""Estudiantes y representantes de la escuela del administrador autenticado."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_current_admin_escuela
from app.core.openapi_responses import BAD_REQUEST, TENANT_DETAIL_RESPONSES, TENANT_RESPONSES
from app.schemas.responses import APIResponse
from app.schemas.student import StudentUpdateSchoolAdmin
from app.services.school_admin_service import school_admin_service

router = APIRouter()








# ──────────────────────────────────────────────────────────
# GET - Detalle completo de un estudiante
# ──────────────────────────────────────────────────────────

@router.get("/students/{student_id}", response_model=APIResponse[dict],
    summary="Obtener detalle de un estudiante",
    description=(
        "Ficha completa de un estudiante de la escuela: sus datos base, los representantes "
        "vinculados (null si no tiene) y sus métricas de salud más recientes con el estado "
        "nutricional OPTIMO, OBESO o DESNUTRIDO (null si no hay registros)."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Devuelve la ficha completa de un estudiante de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La pertenencia del estudiante es indirecta: debe estar inscrito, vía
        'classroom_registration', en un salón de la escuela del administrador.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante no está inscrito en ningún salón o
            pertenece a otra escuela.
        HTTPException(404): Si no existe un estudiante activo con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_detail(user_id=user_id, student_id=student_id)
    return APIResponse(data=result, message="Detalle del estudiante obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Detalle de un Representante y sus Hijos
# ──────────────────────────────────────────────────────────

@router.get("/representatives/{parent_id}", response_model=APIResponse[dict],
    summary="Obtener detalle de un representante",
    description=(
        "Datos de un representante junto con el conteo y la lista de sus hijos. Por cada hijo "
        "devuelve id, nombre completo, fecha de nacimiento, grado actual, estado nutricional "
        "(DESNUTRIDO, OPTIMO, OBESO o SIN DATOS) y si tiene algún caso médico activo."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_parent_detail(
    parent_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Devuelve el detalle de un representante y de sus hijos en la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. El representante solo es visible si al menos uno de sus estudiantes
        pertenece a la escuela del administrador.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el representante no tiene estudiantes asociados, o si
            ninguno de ellos pertenece a la escuela del administrador.
        HTTPException(404): Si no existe un representante activo con ese ID.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_parent_detail(
        user_id=user_id,
        parent_id=parent_id
    )
    return APIResponse(data=result, message="Detalle del representante obtenido exitosamente")


# ──────────────────────────────────────────────────────────
# PUT - Actualizar perfil del estudiante (incluyendo representante)
# ──────────────────────────────────────────────────────────

@router.put("/students/{student_id}", response_model=APIResponse[dict],
    summary="Actualizar perfil de un estudiante",
    description=(
        "Modifica los campos enviados del estudiante: nombre, apellido, cédula, género, tipo "
        "de sangre y fecha de nacimiento. Además, 'representative_id' reemplaza al "
        "representante actual en 'student_representative'."
    ),
    responses={**TENANT_RESPONSES, **BAD_REQUEST},
)
def update_student_profile(
    student_id: int,
    payload: StudentUpdateSchoolAdmin,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Actualiza el perfil de un estudiante y, opcionalmente, su representante.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La pertenencia del estudiante es indirecta: debe estar inscrito, vía
        'classroom_registration', en un salón de la escuela del administrador.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante no pertenece a la escuela del
            administrador.
        HTTPException(400): Si el 'representative_id' indicado no existe.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.update_student_profile(
        user_id=user_id,
        student_id=student_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Perfil del estudiante y representante actualizados exitosamente")


# ──────────────────────────────────────────────────────────
# GET - Búsqueda global de Representantes (Paginado)
# ──────────────────────────────────────────────────────────

@router.get("/search/representatives", response_model=APIResponse[dict],
    summary="Buscar representantes",
    description=(
        "Búsqueda paginada de representantes por coincidencia parcial de nombre o apellido. "
        "Sirve para localizar el 'representative_id' que luego se usa al reasignar el "
        "representante de un estudiante. Devuelve email, nombre, apellido, representative_id, "
        "user_id y ocupación.  **Alcance:** la búsqueda recorre todos los representantes del "
        "sistema, no solo los de la escuela del administrador."
    ),
    responses=TENANT_RESPONSES,
)
def search_representatives(
    query: str = Query(..., min_length=1, description="Nombre o Apellido del representante"),
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Busca representantes por nombre o apellido, de forma paginada.

    Multi-tenancy:
        Excepción al patrón del módulo: el servicio no recibe el 'user_id' y por
        tanto no filtra por escuela, sino que recorre todos los representantes del
        sistema. Es el comportamiento vigente, necesario para poder asignar a un
        estudiante un representante aún no vinculado a la escuela.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
    """
    result = school_admin_service.search_representatives(
        query=query,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Búsqueda completada exitosamente")


# ──────────────────────────────────────────────────────────
# PATCH - Activar Estudiante
# ──────────────────────────────────────────────────────────

@router.patch("/students/{student_id}/activate", response_model=APIResponse[dict],
    summary="Activar estudiante",
    description=(
        "Reactiva a un estudiante previamente desactivado de la escuela. No puede aplicarse a "
        "un estudiante eliminado."
    ),
    responses={**TENANT_DETAIL_RESPONSES, **BAD_REQUEST},
)
def activate_student(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Activa a un estudiante de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La pertenencia del estudiante es indirecta: debe estar inscrito, vía
        'classroom_registration', en un salón de la escuela del administrador.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante no está inscrito en ningún salón o
            pertenece a otra escuela.
        HTTPException(404): Si el estudiante no existe.
        HTTPException(400): Si se intenta activar a un estudiante eliminado.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.activate_student(
        user_id=user_id,
        student_id=student_id
    )
    return APIResponse(data=result, message="Estudiante activado exitosamente")


# ──────────────────────────────────────────────────────────
# PATCH - Desactivar Estudiante
# ──────────────────────────────────────────────────────────

@router.patch("/students/{student_id}/deactivate", response_model=APIResponse[dict],
    summary="Desactivar estudiante",
    description=(
        "Desactiva a un estudiante activo de la escuela. No puede aplicarse a un estudiante "
        "eliminado."
    ),
    responses={**TENANT_DETAIL_RESPONSES, **BAD_REQUEST},
)
def deactivate_student(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Desactiva a un estudiante de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La pertenencia del estudiante es indirecta: debe estar inscrito, vía
        'classroom_registration', en un salón de la escuela del administrador.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante no está inscrito en ningún salón o
            pertenece a otra escuela.
        HTTPException(404): Si el estudiante no existe.
        HTTPException(400): Si se intenta modificar un estudiante eliminado.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.deactivate_student(
        user_id=user_id,
        student_id=student_id
    )
    return APIResponse(data=result, message="Estudiante desactivado exitosamente")



