from fastapi import APIRouter, Depends, UploadFile, File

from app.api.deps import get_current_doctor
from app.schemas.responses import APIResponse
from app.schemas.user import UserUpdate, UserPhotoResponse
from app.services.doctor_service import doctor_service
from app.services import profile_photo_service

router = APIRouter()


# ──────────────────────────────────────────────────────────
# Profile - Mi Perfil de Doctor
# ──────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=APIResponse[dict],
    summary="Obtener perfil del médico",
    description="Retorna el perfil del doctor autenticado, incluyendo datos de usuario, profesionales y escuelas asignadas."
)
def get_my_profile(
    doctor_payload: dict = Depends(get_current_doctor)
):
    """
    Retorna el perfil del médico autenticado.

    Multi-tenancy:
        El usuario se deriva exclusivamente del token JWT (doctor_payload['sub']).

    RBAC:
        Requiere rol doctor autenticado mediante Bearer token.

    Raises:
        HTTPException(404): Si el perfil de médico no existe en el sistema.
    """
    user_id = int(doctor_payload["sub"])
    result = doctor_service.get_my_profile(user_id=user_id)
    return APIResponse(
        success=True,
        data=result,
        message="Perfil de médico obtenido exitosamente"
    )


@router.put(
    "/profile",
    response_model=APIResponse[dict],
    summary="Actualizar perfil del médico",
    description="Actualiza la información personal del doctor autenticado (nombre, apellido, cédula, dirección, biografía, etc.). La foto se gestiona en /profile/photo."
)
def update_my_profile(
    payload: UserUpdate,
    doctor_payload: dict = Depends(get_current_doctor)
):
    """
    Actualiza la información personal del médico autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (doctor_payload['sub']).

    RBAC:
        Requiere rol doctor autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el perfil.
    """
    user_id = int(doctor_payload["sub"])
    result = doctor_service.update_my_profile(
        user_id=user_id,
        payload=payload.model_dump(exclude_unset=True)
    )
    return APIResponse(
        success=True,
        data=result,
        message="Perfil de médico actualizado exitosamente"
    )


@router.post(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Subir foto de perfil del médico",
    description="Sube una imagen al bucket de ImageKit.io y actualiza photo_url en el perfil del médico autenticado."
)
def upload_my_profile_photo(
    file: UploadFile = File(..., description="Archivo de imagen (JPEG, PNG o WebP, máx. 5MB)"),
    doctor_payload: dict = Depends(get_current_doctor)
):
    """
    Sube y actualiza la foto de perfil del médico autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (doctor_payload['sub']).

    RBAC:
        Requiere rol doctor autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si el archivo no es una imagen válida o supera los 5 MB.
        HTTPException(500): Si ImageKit no está configurado en el servidor.
        HTTPException(502): Si la subida al bucket de ImageKit falla.
    """
    user_id = int(doctor_payload["sub"])
    # Plain `def` endpoint: FastAPI runs it in the threadpool, so the blocking
    # ImageKit/Supabase calls never block the event loop.
    file_bytes = profile_photo_service.read_upload_capped(file.file)
    result = doctor_service.upload_my_profile_photo(
        user_id=user_id,
        file_bytes=file_bytes,
        content_type=file.content_type or ""
    )
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil de médico subida y actualizada exitosamente"
    )


@router.delete(
    "/profile/photo",
    response_model=APIResponse[UserPhotoResponse],
    summary="Eliminar foto de perfil del médico",
    description="Elimina la foto de perfil del médico autenticado, estableciendo photo_url en null."
)
def delete_my_profile_photo(
    doctor_payload: dict = Depends(get_current_doctor)
):
    """
    Elimina la foto de perfil del médico autenticado.

    Multi-tenancy:
        El usuario afectado se deriva exclusivamente del token JWT (doctor_payload['sub']).

    RBAC:
        Requiere rol doctor autenticado mediante Bearer token.

    Raises:
        HTTPException(400): Si no se pudo actualizar el registro en la base de datos.
    """
    user_id = int(doctor_payload["sub"])
    result = doctor_service.delete_my_profile_photo(user_id=user_id)
    return APIResponse(
        success=True,
        data=UserPhotoResponse(**result),
        message="Foto de perfil de médico eliminada exitosamente"
    )
