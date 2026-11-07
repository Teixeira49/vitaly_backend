"""Perfil y métricas generales del administrador de escuela."""

from fastapi import APIRouter, Depends, Query, UploadFile, File

from app.api.deps import get_current_admin_escuela
from app.core.openapi_responses import (
    BAD_REQUEST,
    TENANT_DETAIL_RESPONSES,
    TENANT_RESPONSES,
    error_response,
)
from app.schemas.responses import APIResponse
from app.schemas.user import UserUpdate, UserPhotoResponse
from app.services.school_admin_service import school_admin_service
from app.services import profile_photo_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# Profile - Mi Perfil de Administrador
# ──────────────────────────────────────────────────────────

@router.get("/profile", response_model=APIResponse[dict],
    summary="Obtener perfil del administrador",
    description=(
        "Retorna el perfil del administrador de escuela autenticado: sus datos personales, su "
        "cargo administrativo y los datos básicos de la escuela a la que pertenece (nombre, "
        "año de fundación y dirección)."
    ),
    responses=TENANT_DETAIL_RESPONSES,
)
def get_my_profile(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Retorna el perfil del administrador de escuela autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT
        (admin_payload['sub']). No acepta identificadores del cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(404): Si no existe el perfil de administrador.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_my_profile(user_id=user_id)
    return APIResponse(data=result, message="Perfil obtenido exitosamente")


@router.put("/profile", response_model=APIResponse[dict],
    summary="Actualizar perfil del administrador",
    description=(
        "Actualiza la información personal del administrador autenticado: nombre, apellido, "
        "cédula, fecha de nacimiento, género, dirección y biografía. La foto se gestiona "
        "aparte, en /profile/photo."
    ),
    responses={**TENANT_RESPONSES, **BAD_REQUEST},
)
def update_my_profile(
    payload: UserUpdate,
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Actualiza la información personal del administrador autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT
        (admin_payload['sub']). No acepta identificadores del cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(400): Si no se pudo actualizar el perfil.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.update_my_profile(
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(data=result, message="Perfil actualizado exitosamente")


@router.post(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Subir foto de perfil",
    description="Sube una imagen al bucket de ImageKit.io y actualiza la URL en el perfil del usuario autenticado.",
    responses={
        **TENANT_RESPONSES,
        **BAD_REQUEST,
        **error_response(502, "Falló la subida del archivo a ImageKit.", "No se pudo subir la imagen al proveedor de almacenamiento."),
    },
)
def upload_my_profile_photo(
    file: UploadFile = File(..., description="Archivo de imagen (JPEG, PNG o WebP, máx. 5MB)"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Sube y actualiza la foto de perfil del administrador de escuela autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (admin_payload['sub']).
        No acepta ni confía en identificadores enviados en el cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si el archivo no es una imagen válida (JPEG, PNG, WebP) o excede 5MB.
        HTTPException(500): Si el servicio ImageKit no está configurado en el servidor.
        HTTPException(502): Si la subida a ImageKit falla por error de pasarela.
    """
    user_id = int(admin_payload["sub"])
    # Plain `def` endpoint: FastAPI runs it in the threadpool, so the blocking
    # ImageKit/Supabase calls never block the event loop.
    file_bytes = profile_photo_service.read_upload_capped(file.file)
    result = school_admin_service.upload_my_profile_photo(
        user_id=user_id,
        file_bytes=file_bytes,
        content_type=file.content_type or ""
    )
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil subida y actualizada exitosamente"
    )


@router.delete(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Eliminar foto de perfil",
    description="Elimina la foto de perfil del administrador autenticado, estableciendo photo_url en null.",
    responses={**TENANT_RESPONSES, **BAD_REQUEST},
)
def delete_my_profile_photo(
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """
    Elimina la foto de perfil del administrador de escuela autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (admin_payload['sub']).
        No acepta ni confía en identificadores enviados en el cuerpo.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el registro en la base de datos.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.delete_my_profile_photo(user_id=user_id)
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil eliminada exitosamente"
    )



# ──────────────────────────────────────────────────────────
# GET - Resumen / Métricas de Estudiantes
# ──────────────────────────────────────────────────────────

@router.get("/students/resume", response_model=APIResponse[dict],
    summary="Resumen de salud de los estudiantes",
    description=(
        "Métricas agregadas de los estudiantes de la escuela en el año académico vigente: "
        "total, estudiantes con sobrepeso (IMC > 24.9), con desnutrición (IMC < 18.5), casos "
        "médicos activos y estudiantes en rango óptimo. Los filtros son jerárquicos: 'grade' "
        "exige 'category', y 'section' exige ambos."
    ),
    responses={**TENANT_DETAIL_RESPONSES, **BAD_REQUEST},
)
def get_students_resume(
    category: int = Query(None, description="ID de la categoría del aula (ej. 1=PREESCOLAR). Filtra el resumen por categoría."),
    grade: int = Query(None, description="Nivel/grado del aula. Requiere 'category'."),
    section: str = Query(None, description="Letra de la sección (ej. 'A'). Requiere 'category' y 'grade'."),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Calcula el resumen de salud de los estudiantes de la escuela.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela.
        HTTPException(400): Si se envía 'grade' sin 'category', o 'section' sin
            'category' y 'grade'.
        HTTPException(404): Si no hay un año académico vigente configurado.
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

@router.get("/students/{student_id}/medical-history", response_model=APIResponse[dict],
    summary="Historial médico de un estudiante",
    description=(
        "Retorna de forma paginada los casos médicos registrados para el estudiante indicado, "
        "previa verificación de que pertenece a la escuela del administrador."
    ),
    responses=TENANT_RESPONSES,
)
def get_student_medical_history(
    student_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Elementos por página"),
    admin_payload: dict = Depends(get_current_admin_escuela)
):
    """Lista de forma paginada el historial médico de un estudiante.

    Multi-tenancy:
        El 'school_id' se resuelve en el servidor a partir del usuario autenticado
        (admin_payload['sub']); el cliente nunca lo envía. La pertenencia del estudiante se comprueba antes de leer sus casos.

    RBAC:
        Requiere rol admin_escuela autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_escuela, o si el usuario no está
            vinculado a ninguna escuela. También 403 si el estudiante pertenece a otra escuela.
    """
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_medical_history(
        user_id=user_id,
        student_id=student_id,
        page=page,
        size=size
    )
    return APIResponse(data=result, message="Historial médico obtenido exitosamente")
