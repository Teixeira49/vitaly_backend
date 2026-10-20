"""Autenticación: registro por rol, login y revocación de sesión."""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import get_current_user_token, security
from app.core.openapi_responses import BAD_REQUEST, PROTECTED_RESPONSES, PUBLIC_RESPONSES, UNAUTHORIZED, FORBIDDEN_ROLE
from app.schemas.user import SystemAdminRegister, SchoolAdminRegister, DoctorRegister, ParentRegister, UserLogin, Token
from app.schemas.responses import APIResponse
from app.services.auth_service import auth_service

router = APIRouter()

#: Registro: cualquiera puede solicitarlo; el 400 cubre el correo ya existente.
_REGISTER_RESPONSES = {**PUBLIC_RESPONSES, **BAD_REQUEST}


# PUBLIC_ROUTE
@router.post(
    "/register-system-admin",
    response_model=APIResponse[str],
    summary="Registrar administrador de sistema",
    description=(
        "Crea una cuenta de administrador de sistema. La cuenta nace inactiva "
        "(is_active=False) y requiere la aprobación de otro administrador antes "
        "de poder iniciar sesión."
    ),
    responses=_REGISTER_RESPONSES,
)
def register_system_admin(user_in: SystemAdminRegister):
    """Registra un administrador de sistema, pendiente de verificación.

    Multi-tenancy:
        Rol de alcance global: la cuenta no queda vinculada a ninguna escuela.

    RBAC:
        Ruta pública: no requiere token.

    Raises:
        HTTPException(400): Si el correo ya está registrado bajo algún rol.
        HTTPException(500): Si falla la creación del usuario base.
    """
    msg = auth_service.register_system_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de sistema")


# PUBLIC_ROUTE
@router.post(
    "/register-school-admin",
    response_model=APIResponse[str],
    summary="Registrar administrador de escuela",
    description=(
        "Crea una cuenta de administrador de escuela vinculada a la institución "
        "indicada en 'school_id'. La cuenta nace inactiva y requiere aprobación. "
        "El 'school_id' enviado aquí define el alcance de datos del usuario para "
        "el resto del sistema; a partir del login se resuelve siempre en el servidor."
    ),
    responses=_REGISTER_RESPONSES,
)
def register_school_admin(user_in: SchoolAdminRegister):
    """Registra un administrador de escuela, pendiente de verificación.

    Multi-tenancy:
        Es el único punto donde el cliente aporta un 'school_id': fija el vínculo
        inicial en 'school_administrator'. Después nunca se vuelve a aceptar del
        cliente, sino que se deriva del usuario autenticado.

    RBAC:
        Ruta pública: no requiere token.

    Raises:
        HTTPException(400): Si el correo ya está registrado bajo algún rol.
        HTTPException(500): Si falla la creación del usuario base.
    """
    msg = auth_service.register_school_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de escuela")


# PUBLIC_ROUTE
@router.post(
    "/register-doctor",
    response_model=APIResponse[str],
    summary="Registrar médico",
    description=(
        "Crea una cuenta de médico escolar con su número de licencia y "
        "especialidad. La cuenta nace inactiva y requiere aprobación. La "
        "asignación a escuelas se gestiona aparte, en 'doctor_to_school'."
    ),
    responses=_REGISTER_RESPONSES,
)
def register_doctor(user_in: DoctorRegister):
    """Registra un médico, pendiente de verificación.

    Multi-tenancy:
        La cuenta nace sin escuela asignada; el alcance se otorga después vía
        'doctor_to_school'.

    RBAC:
        Ruta pública: no requiere token.

    Raises:
        HTTPException(400): Si el correo ya está registrado bajo algún rol.
        HTTPException(500): Si falla la creación del usuario base.
    """
    msg = auth_service.register_doctor(user_in)
    return APIResponse(data=msg, message="Registro completado para doctor")


# PUBLIC_ROUTE
@router.post(
    "/register-parent",
    response_model=APIResponse[str],
    summary="Registrar representante",
    description=(
        "Crea una cuenta de representante (padre, madre o tutor). El "
        "'identity_number' es obligatorio: con él se buscan y vinculan "
        "automáticamente los estudiantes que lo declararon como autorizado. La "
        "cuenta nace inactiva y requiere aprobación."
    ),
    responses=_REGISTER_RESPONSES,
)
def register_parent(user_in: ParentRegister):
    """Registra un representante y lo vincula con sus estudiantes autorizados.

    Multi-tenancy:
        El alcance se deriva de los estudiantes vinculados, no de un 'school_id'
        enviado por el cliente.

    RBAC:
        Ruta pública: no requiere token.

    Raises:
        HTTPException(400): Si el correo ya está registrado, o si falta el
            documento de identidad.
        HTTPException(500): Si falla la creación del usuario base.
    """
    msg = auth_service.register_parent(user_in)
    return APIResponse(data=msg, message="Registro completado para representante")


# PUBLIC_ROUTE
@router.post(
    "/login",
    response_model=APIResponse[Token],
    summary="Iniciar sesión",
    description=(
        "Valida las credenciales y devuelve un JWT de tipo bearer. Requiere una "
        "cuenta aprobada y no eliminada. El token incluye el rol pero no la "
        "escuela: el alcance por institución se resuelve en el servidor en cada "
        "petición."
    ),
    responses={**PUBLIC_RESPONSES, **UNAUTHORIZED, **FORBIDDEN_ROLE},
)
def login(user_in: UserLogin):
    """Autentica al usuario y emite su token de acceso.

    Multi-tenancy:
        El token no lleva claim de escuela a propósito; cada servicio resuelve el
        'school_id' a partir del claim 'sub'.

    RBAC:
        Ruta pública: no requiere token.

    Raises:
        HTTPException(401): Si el correo no existe o la contraseña no coincide.
        HTTPException(403): Si la cuenta fue eliminada o aún no está aprobada.
    """
    token_response = auth_service.authenticate_user(user_in)
    return APIResponse(data=token_response, message="Login exitoso")


@router.post(
    "/logout",
    response_model=APIResponse[str],
    summary="Cerrar sesión",
    description=(
        "Revoca el token de acceso actual añadiéndolo a la lista negra. El token "
        "sigue siendo criptográficamente válido hasta su expiración, pero las "
        "siguientes peticiones que lo usen reciben un 401."
    ),
    responses=PROTECTED_RESPONSES,
)
def logout(
    payload: dict = Depends(get_current_user_token),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Revoca el token con el que se realiza la petición.

    Multi-tenancy:
        Afecta únicamente al token del usuario autenticado.

    RBAC:
        Requiere cualquier rol autenticado mediante Bearer token.

    Raises:
        HTTPException(401): Si el token es inválido, expiró o ya fue revocado.
    """
    token = credentials.credentials
    expires_at = payload.get("exp")
    auth_service.revoke_token(token, expires_at)
    return APIResponse(data="Logout exitoso", message="Sesión cerrada correctamente")
