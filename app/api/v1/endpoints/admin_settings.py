"""Configuración global del sistema, administrada por el rol admin_sistema."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin_sistema
from app.core.openapi_responses import BAD_REQUEST, PROTECTED_RESPONSES
from app.schemas.enums import SettingKey
from app.schemas.responses import APIResponse
from app.schemas.settings import SettingRead, SettingUpdate
from app.services.settings_service import settings_service

#: Todo el módulo exige rol admin_sistema: la configuración es global y no
#: participa del aislamiento por escuela.
router = APIRouter(dependencies=[Depends(get_current_admin_sistema)])


@router.get(
    "/",
    response_model=APIResponse[list[SettingRead]],
    summary="Listar la configuración del sistema",
    description=(
        "Retorna todas las claves de configuración soportadas con su valor vigente. Las "
        "claves que aún no tienen fila en la base de datos se devuelven con su valor por "
        "defecto y 'updated_at' en null."
    ),
    responses=PROTECTED_RESPONSES,
)
def list_settings(
    admin_payload: Annotated[dict, Depends(get_current_admin_sistema)],
):
    """Lista la configuración global del sistema.

    Multi-tenancy:
        No aplica: la tabla 'settings' es global y no tiene 'school_id'. Solo el
        administrador de sistema puede consultarla o modificarla.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(500): Si la consulta a la base de datos falla.
    """
    result = settings_service.list_settings()
    return APIResponse(data=result, message="Configuración obtenida exitosamente")


@router.get(
    "/{key}",
    response_model=APIResponse[SettingRead],
    summary="Obtener una configuración",
    description=(
        "Retorna el valor vigente de una clave de configuración. Si la clave aún no tiene "
        "fila almacenada, devuelve su valor por defecto con 'updated_at' en null."
    ),
    responses=PROTECTED_RESPONSES,
)
def get_setting(
    key: SettingKey,
    admin_payload: Annotated[dict, Depends(get_current_admin_sistema)],
):
    """Devuelve una configuración concreta del sistema.

    Multi-tenancy:
        No aplica: la tabla 'settings' es global y no tiene 'school_id'.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        RequestValidationError(422): Si la clave no es una configuración soportada.
    """
    result = settings_service.get_setting(key)
    return APIResponse(data=result, message="Configuración obtenida exitosamente")


@router.put(
    "/{key}",
    response_model=APIResponse[SettingRead],
    summary="Actualizar una configuración",
    description=(
        "Crea o actualiza el valor de una clave de configuración. El tipo declarado debe "
        "coincidir con el de la clave y el valor debe caer dentro del rango admitido; de lo "
        "contrario la petición se rechaza con 400 y el valor almacenado no cambia. El nuevo "
        "valor rige para las solicitudes posteriores, sin reiniciar la API."
    ),
    responses={**PROTECTED_RESPONSES, **BAD_REQUEST},
)
def update_setting(
    key: SettingKey,
    payload: SettingUpdate,
    admin_payload: Annotated[dict, Depends(get_current_admin_sistema)],
):
    """Crea o actualiza el valor de una configuración global.

    Multi-tenancy:
        No aplica: la tabla 'settings' es global y no tiene 'school_id'. El cambio
        afecta a todas las escuelas.

    RBAC:
        Requiere rol admin_sistema autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o fue revocado.
        HTTPException(403): Si el rol no es admin_sistema.
        HTTPException(400): Si el tipo declarado no corresponde a la clave, o si el
            valor queda fuera del rango admitido.
        HTTPException(500): Si la escritura en la base de datos falla.
        RequestValidationError(422): Si la clave no es una configuración soportada.
    """
    result = settings_service.upsert_setting(
        key=key,
        value_type=payload.value.type,
        value=payload.value.value,
        description=payload.description,
        actor_user_id=int(admin_payload["sub"]),
    )
    return APIResponse(data=result, message="Configuración actualizada exitosamente")
