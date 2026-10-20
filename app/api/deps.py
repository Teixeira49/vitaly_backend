"""Gates de autorización de FastAPI.

Este módulo es el único lugar del backend autorizado a comparar el rol del
usuario. Todo endpoint no público declara uno de estos gates mediante
``Depends(...)``; las rutas públicas se marcan con ``# PUBLIC_ROUTE``.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import get_settings
from app.schemas.enums import UserRole
from app.services.auth_service import auth_service

settings = get_settings()
security = HTTPBearer()

ALGORITHM = "HS256"

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Decodifica y valida el JWT del header ``Authorization: Bearer``.

    Es la base de todos los demás gates: verifica la firma HS256, la expiración y
    que el token no haya sido revocado por un logout previo.

    Args:
        credentials: Credenciales extraídas por ``HTTPBearer``. FastAPI responde
            401 por su cuenta si el header está ausente o malformado.

    Returns:
        dict: Payload decodificado del JWT. Contiene al menos ``sub`` (id de
        usuario como string) y ``role``. No incluye claim de escuela.

    Raises:
        HTTPException: 401 si el token es inválido, expiró o fue revocado.
    """
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        
        # Verificar si el token ha sido revocado (logout)
        if auth_service.is_token_revoked(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="El token ha sido revocado. Por favor inicia sesión de nuevo.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_sistema(payload: dict = Depends(get_current_user_token)) -> dict:
    """Exige que el usuario autenticado sea un administrador de sistema.

    Su alcance es global: puede auditar cualquier escuela, por lo que sus rutas sí
    admiten recibir un ``school_id`` por path.

    Args:
        payload: Payload del JWT ya validado por :func:`get_current_user_token`.

    Returns:
        dict: El mismo payload, para que el handler lea ``int(payload["sub"])``.

    Raises:
        HTTPException: 401 si el token es inválido, expiró o fue revocado.
        HTTPException: 403 si el rol del usuario no es ``admin_sistema``.
    """
    role = payload.get("role")
    if role != UserRole.ADMIN_SISTEMA.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de admin_sistema."
        )
    return payload

def get_current_admin_escuela(payload: dict = Depends(get_current_user_token)) -> dict:
    """Exige que el usuario autenticado sea un administrador de escuela.

    Su alcance se limita a la escuela vinculada en ``school_administrator``; el
    ``school_id`` se resuelve en el servidor a partir de ``sub``, nunca del cliente.

    Args:
        payload: Payload del JWT ya validado por :func:`get_current_user_token`.

    Returns:
        dict: El mismo payload, para que el handler lea ``int(payload["sub"])``.

    Raises:
        HTTPException: 401 si el token es inválido, expiró o fue revocado.
        HTTPException: 403 si el rol del usuario no es ``admin_escuela``.
    """
    role = payload.get("role")
    if role != UserRole.ADMIN_ESCUELA.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de admin_escuela."
        )
    return payload

def get_current_representante(payload: dict = Depends(get_current_user_token)) -> dict:
    """Exige que el usuario autenticado sea un representante.

    Su alcance se limita a los estudiantes vinculados a su registro en ``parent``.

    Args:
        payload: Payload del JWT ya validado por :func:`get_current_user_token`.

    Returns:
        dict: El mismo payload, para que el handler lea ``int(payload["sub"])``.

    Raises:
        HTTPException: 401 si el token es inválido, expiró o fue revocado.
        HTTPException: 403 si el rol del usuario no es ``representante``.
    """
    role = payload.get("role")
    if role != UserRole.REPRESENTANTE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de representante."
        )
    return payload

def get_current_doctor(payload: dict = Depends(get_current_user_token)) -> dict:
    """Exige que el usuario autenticado sea un médico.

    Su alcance se limita a las escuelas vinculadas en ``doctor_to_school``.

    Args:
        payload: Payload del JWT ya validado por :func:`get_current_user_token`.

    Returns:
        dict: El mismo payload, para que el handler lea ``int(payload["sub"])``.

    Raises:
        HTTPException: 401 si el token es inválido, expiró o fue revocado.
        HTTPException: 403 si el rol del usuario no es ``doctor``.
    """
    role = payload.get("role")
    if role != UserRole.DOCTOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de doctor."
        )
    return payload

