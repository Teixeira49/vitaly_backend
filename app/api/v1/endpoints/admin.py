from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_admin_sistema
from app.schemas.responses import APIResponse
from app.schemas.admin import PaginatedUsersResponse, ApproveUserRequest, BulkApproveUserRequest, UserDetailsResponse, ToggleUserRequest
from app.services.admin_service import admin_service

router = APIRouter()

@router.get("/users", response_model=APIResponse[PaginatedUsersResponse])
def get_all_users(
    page: int = Query(1, ge=1, description="Número de página para la paginación"),
    size: int = Query(20, ge=1, le=100, description="Cantidad de usuarios a mostrar por página"),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Lista todos los usuarios guardados en la plataforma.
    El resultado devuelve la lista paginada e información de cada usuario básico.
    Solo un administrador de sistema autenticado puede acceder.
    """
    result = admin_service.get_users(page=page, size=size, pending_only=False)
    return APIResponse(data=result, message="Lista de todos los usuarios obtenida exitosamente")

@router.get("/users/pending", response_model=APIResponse[PaginatedUsersResponse])
def get_pending_users(
    page: int = Query(1, ge=1, description="Número de página para la paginación"),
    size: int = Query(20, ge=1, le=100, description="Cantidad de usuarios a mostrar por página"),
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Trae las solicitudes pendientes (Usuarios que todavía tienen isActive = False).
    El resultado devuelve la lista paginada.
    Solo un administrador de sistema autenticado puede acceder.
    """
    result = admin_service.get_users(page=page, size=size, pending_only=True)
    return APIResponse(data=result, message="Usuarios pendientes obtenidos exitosamente")

@router.patch("/users/approve", response_model=APIResponse[str])
def approve_user(
    body: ApproveUserRequest,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Aprueba a un usuario particular especificado en el payload.
    Para que se apruebe exitosamente debe existir, no estar eliminado, ni estar ya aprobado. Al completarse pasa de False a True su `isActive`.
    Solo un administrador de sistema autenticado puede acceder.
    """
    msg = admin_service.approve_user(user_id=body.user_id_to_approve, admin_id=body.admin_id)
    return APIResponse(data=msg, message="Aprobación completada")

@router.patch("/users/approve/bulk", response_model=APIResponse[str])
def approve_users_bulk(
    body: BulkApproveUserRequest,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Aprueba una lista masiva de usuarios especificados en el payload según su array de IDs.
    Cambia a isActive = True a los usuarios que estén en la lista, existan y no estén eliminados.
    Solo un administrador de sistema autenticado puede acceder.
    """
    msg = admin_service.approve_users_bulk(user_ids=body.user_ids_to_approve, admin_id=body.admin_id)
    return APIResponse(data=msg, message="Aprobación masiva completada")

@router.get("/users/{user_id}/details", response_model=APIResponse[UserDetailsResponse])
def get_user_details(
    user_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Visualiza toda la información detallada de un usuario por ID.
    Determina su rol (doctor, representante, admin_sistema, admin_escuela) internamente y anexa los datos de la tabla relacionada (como su data de escuela, clínica, etc).
    Solo admin_sistema puede acceder.
    """
    result = admin_service.get_user_details(user_id=user_id)
    return APIResponse(data=result, message="Detalle del usuario obtenido exitosamente.")

@router.patch("/users/{user_id}/toggle-active", response_model=APIResponse[str])
def toggle_user_active(
    user_id: int,
    body: ToggleUserRequest,
    admin_payload: dict = Depends(get_current_admin_sistema)
):
    """
    Cambia el estatus de un usuario registrado alternando su isActive.
    Previene autodeshabilitarse a sí mismo.
    Si el destino también es un admin_sistema, el solicitante debe tener un `level_privilege` numéricamente menor o exácto según sea la convención (solo restringe si tiene nivel superior).
    Solo admin_sistema puede acceder.
    """
    msg = admin_service.toggle_user_status(user_id=user_id, request_admin_id=body.admin_id)
    return APIResponse(data=msg, message="Estado activo de usuario alternado")

