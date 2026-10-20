from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.schemas.user import SystemAdminRegister, SchoolAdminRegister, DoctorRegister, ParentRegister, UserLogin, AdminLoginCreate, Token
from app.schemas.enums import TokenScope
from app.schemas.responses import APIResponse
from app.services.auth_service import auth_service
from app.api.deps import get_current_user_token, security

router = APIRouter()
# Portal de administración: montado en /auth/admin con su propia sección en Swagger/ReDoc.
admin_router = APIRouter()

# Errores comunes de ambos portales de login (los cuerpos siguen el envelope APIResponse).
LOGIN_ERROR_RESPONSES = {
    401: {"model": APIResponse[None], "description": "Unauthorized: correo o contraseña incorrectos."},
    403: {
        "model": APIResponse[None],
        "description": "Forbidden: credenciales válidas pero la cuenta está eliminada, inactiva "
        "o su rol no pertenece a este portal. No se emite ningún token.",
    },
    500: {
        "model": APIResponse[None],
        "description": "Internal Server Error: no se pudo completar el login. Inténtalo de nuevo más tarde.",
    },
}

# PUBLIC_ROUTE
@router.post("/register-system-admin", response_model=APIResponse[str])
def register_system_admin(user_in: SystemAdminRegister):
    """
    Register a new system admin. The user will be created with is_active=False and must wait for verification.
    """
    msg = auth_service.register_system_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de sistema")

# PUBLIC_ROUTE
@router.post("/register-school-admin", response_model=APIResponse[str])
def register_school_admin(user_in: SchoolAdminRegister):
    """
    Register a new school administrator. The user will be created with is_active=False and must wait for verification.
    Requires school_id and administrative_position.
    """
    msg = auth_service.register_school_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de escuela")

# PUBLIC_ROUTE
@router.post("/register-doctor", response_model=APIResponse[str])
def register_doctor(user_in: DoctorRegister):
    """
    Register a new doctor. The user will be created with is_active=False and must wait for verification.
    Requires doc_license_number and especially.
    """
    msg = auth_service.register_doctor(user_in)
    return APIResponse(data=msg, message="Registro completado para doctor")

# PUBLIC_ROUTE
@router.post("/register-parent", response_model=APIResponse[str])
def register_parent(user_in: ParentRegister):
    """
    Register a new parent/representative. 
    Requires identity_number and type_representative (Mother, Father, etc).
    """
    msg = auth_service.register_parent(user_in)
    return APIResponse(data=msg, message="Registro completado para representante")

# PUBLIC_ROUTE
@router.post(
    "/login",
    response_model=APIResponse[Token],
    summary="Login del portal de clientes",
    description="Autentica a administradores de escuela, doctores y representantes. "
    "Un admin_sistema es rechazado con 403 y debe usar `POST /auth/admin/login`.",
    responses=LOGIN_ERROR_RESPONSES,
)
def login(user_in: UserLogin):
    """Login del portal de clientes; emite un JWT con `scope=client`.

    Multi-tenancy: el token no incluye `school_id`; cada servicio lo resuelve desde `sub`.
    RBAC: ruta pública. Solo admite los roles admin_escuela, doctor y representante.

    Raises:
        HTTPException: 401 si las credenciales son incorrectas; 403 si la cuenta está
            eliminada, inactiva o pertenece al portal de administración; 500 si falla
            una operación interna del login.
    """
    token_response = auth_service.authenticate_user(user_in, TokenScope.CLIENT)
    return APIResponse(data=token_response, message="Login exitoso")

@router.post("/logout", response_model=APIResponse[str])
def logout(
    payload: dict = Depends(get_current_user_token),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Logout endpoint. Revokes the current access token.
    """
    token = credentials.credentials
    expires_at = payload.get("exp")
    auth_service.revoke_token(token, expires_at)
    return APIResponse(data="Logout exitoso", message="Sesión cerrada correctamente")

# PUBLIC_ROUTE
@admin_router.post(
    "/login",
    response_model=APIResponse[Token],
    summary="Login del portal de administración",
    description="Autentica exclusivamente a administradores de sistema. Cualquier otro rol "
    "es rechazado con 403 antes de emitir el token y debe usar `POST /auth/login`.",
    responses=LOGIN_ERROR_RESPONSES,
)
def admin_login(user_in: AdminLoginCreate):
    """Login del portal de administración; emite un JWT con `scope=admin`.

    Multi-tenancy: no aplica; admin_sistema opera sobre todo el sistema.
    RBAC: ruta pública. Solo admite el rol admin_sistema.

    Raises:
        HTTPException: 401 si las credenciales son incorrectas; 403 si la cuenta está
            eliminada, inactiva o pertenece al portal de clientes; 500 si falla una
            operación interna del login.
    """
    token_response = auth_service.authenticate_user(user_in, TokenScope.ADMIN)
    return APIResponse(data=token_response, message="Login exitoso")
