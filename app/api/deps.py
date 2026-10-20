from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import get_settings
from app.schemas.enums import SCOPE_ROLES, TokenScope, UserRole
from app.services.auth_service import auth_service

settings = get_settings()
security = HTTPBearer()

ALGORITHM = "HS256"

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
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

def _require_scope(payload: dict, scope: TokenScope) -> dict:
    """Verifica que el token fue emitido por el portal `scope` para uno de sus roles.

    Raises:
        HTTPException: 401 si el token no trae `scope` (emitido antes de la separación de
            portales: el usuario debe iniciar sesión de nuevo); 403 si procede de otro portal
            o su rol no pertenece a este.
    """
    token_scope = payload.get("scope")
    if token_scope is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token no indica su procedencia. Por favor inicia sesión de nuevo.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    allowed_roles = {role.value for role in SCOPE_ROLES[scope]}
    if token_scope != scope.value or payload.get("role") not in allowed_roles:
        portal = "administración" if scope == TokenScope.ADMIN else "clientes"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Este recurso requiere un token emitido por el portal de {portal}."
        )
    return payload

def get_current_admin(payload: Annotated[dict, Depends(get_current_user_token)]) -> dict:
    """Gate del portal de administración: token con `scope=admin` (admin_sistema)."""
    return _require_scope(payload, TokenScope.ADMIN)

def get_current_client(payload: Annotated[dict, Depends(get_current_user_token)]) -> dict:
    """Gate del portal de clientes: token con `scope=client` (admin_escuela, doctor, representante)."""
    return _require_scope(payload, TokenScope.CLIENT)

def _require_role(payload: dict, role: UserRole) -> dict:
    if payload.get("role") != role.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"No tienes los permisos suficientes para esta acción. Se requiere rol de {role.value}."
        )
    return payload

def get_current_admin_sistema(payload: Annotated[dict, Depends(get_current_admin)]) -> dict:
    return _require_role(payload, UserRole.ADMIN_SISTEMA)

def get_current_admin_escuela(payload: Annotated[dict, Depends(get_current_client)]) -> dict:
    return _require_role(payload, UserRole.ADMIN_ESCUELA)

def get_current_representante(payload: Annotated[dict, Depends(get_current_client)]) -> dict:
    return _require_role(payload, UserRole.REPRESENTANTE)

def get_current_doctor(payload: Annotated[dict, Depends(get_current_client)]) -> dict:
    return _require_role(payload, UserRole.DOCTOR)
