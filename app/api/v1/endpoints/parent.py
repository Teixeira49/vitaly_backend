"""Endpoints del rol representante: perfil propio, foto de perfil y vinculación de estudiantes."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import get_current_representante
from app.core.openapi_responses import (
    BAD_REQUEST,
    PROTECTED_DETAIL_RESPONSES,
    PROTECTED_RESPONSES,
    error_response,
)
from app.schemas.parent import ParentProfileRead, ParentProfileUpdate
from app.schemas.responses import APIResponse
from app.schemas.user import UserPhotoResponse
from app.services.parent_service import parent_service
from app.services import profile_photo_service
from app.core.database import supabase

router = APIRouter()

RepresentantePayload = Annotated[dict, Depends(get_current_representante)]


# ──────────────────────────────────────────────────────────
# Profile - Mi Perfil de Representante
# ──────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=APIResponse[ParentProfileRead],
    summary="Obtener perfil del representante",
    description=(
        "Retorna el perfil del representante autenticado: datos personales, foto de "
        "perfil (photo_url), ocupación y parentesco. Nunca incluye la contraseña ni el "
        "identificador interno de la foto."
    ),
    responses=PROTECTED_DETAIL_RESPONSES,
)
def get_my_profile(parent_payload: RepresentantePayload):
    """Retorna el perfil del representante autenticado.

    Multi-tenancy:
        No aplica alcance de escuela: el usuario se deriva exclusivamente del token
        JWT (parent_payload['sub']) y no se aceptan identificadores del cliente.

    RBAC:
        Requiere rol representante autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es representante.
        HTTPException(404): Si el usuario no tiene un perfil de representante.
    """
    user_id = int(parent_payload["sub"])
    result = parent_service.get_my_profile(user_id=user_id)
    return APIResponse(
        data=ParentProfileRead(**result),
        message="Perfil de representante obtenido exitosamente"
    )


@router.put(
    "/profile",
    response_model=APIResponse[ParentProfileRead],
    summary="Actualizar perfil del representante",
    description=(
        "Actualiza solo los campos enviados del representante autenticado: nombre, "
        "apellido, fecha de nacimiento, género, dirección, ocupación y parentesco. "
        "Email, rol, contraseña y documento de identidad no se pueden cambiar por esta "
        "vía (un campo no permitido responde 422). La foto se gestiona en /profile/photo."
    ),
    responses={**PROTECTED_DETAIL_RESPONSES, **BAD_REQUEST},
)
def update_my_profile(payload: ParentProfileUpdate, parent_payload: RepresentantePayload):
    """Actualiza la información personal del representante autenticado.

    Multi-tenancy:
        No aplica alcance de escuela: el usuario afectado se deriva exclusivamente
        del token JWT (parent_payload['sub']). No acepta identificadores del cuerpo.

    RBAC:
        Requiere rol representante autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el perfil.
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es representante.
        HTTPException(404): Si el usuario no tiene un perfil de representante.
    """
    user_id = int(parent_payload["sub"])
    result = parent_service.update_my_profile(
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True, mode="json"),
    )
    return APIResponse(
        data=ParentProfileRead(**result),
        message="Perfil de representante actualizado exitosamente"
    )


@router.post(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Subir foto de perfil del representante",
    description="Sube una imagen al bucket de ImageKit.io y actualiza photo_url en el perfil del representante autenticado.",
    responses={
        **PROTECTED_RESPONSES,
        **BAD_REQUEST,
        **error_response(502, "Falló la subida del archivo a ImageKit.", "No se pudo subir la imagen al proveedor de almacenamiento."),
    },
)
def upload_my_profile_photo(
    file: Annotated[UploadFile, File(description="Archivo de imagen (JPEG, PNG o WebP, máx. 5MB)")],
    parent_payload: RepresentantePayload,
):
    """Sube y actualiza la foto de perfil del representante autenticado.

    Multi-tenancy:
        No aplica alcance de escuela: el usuario afectado se deriva exclusivamente
        del token JWT (parent_payload['sub']).

    RBAC:
        Requiere rol representante autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si el archivo no es una imagen válida o supera los 5 MB.
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es representante.
        HTTPException(500): Si ImageKit no está configurado en el servidor.
        HTTPException(502): Si la subida al bucket de ImageKit falla.
    """
    user_id = int(parent_payload["sub"])
    # Plain `def` endpoint: FastAPI runs it in the threadpool, so the blocking
    # ImageKit/Supabase calls never block the event loop.
    file_bytes = profile_photo_service.read_upload_capped(file.file)
    result = parent_service.upload_my_profile_photo(
        user_id=user_id,
        file_bytes=file_bytes,
        content_type=file.content_type or ""
    )
    return APIResponse(
        data=UserPhotoResponse(**result),
        message="Foto de perfil de representante subida y actualizada exitosamente"
    )


@router.delete(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Eliminar foto de perfil del representante",
    description="Elimina la foto de perfil del representante autenticado, estableciendo photo_url en null.",
    responses={**PROTECTED_RESPONSES, **BAD_REQUEST},
)
def delete_my_profile_photo(parent_payload: RepresentantePayload):
    """Elimina la foto de perfil del representante autenticado.

    Multi-tenancy:
        No aplica alcance de escuela: el usuario afectado se deriva exclusivamente
        del token JWT (parent_payload['sub']).

    RBAC:
        Requiere rol representante autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el registro en la base de datos.
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es representante.
    """
    user_id = int(parent_payload["sub"])
    result = parent_service.delete_my_profile_photo(user_id=user_id)
    return APIResponse(
        data=UserPhotoResponse(**result),
        message="Foto de perfil de representante eliminada exitosamente"
    )


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
