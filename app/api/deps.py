from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import get_settings
from app.schemas.enums import UserRole

settings = get_settings()
security = HTTPBearer()

ALGORITHM = "HS256"

def get_current_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o token expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_admin_sistema(payload: dict = Depends(get_current_user_token)) -> dict:
    role = payload.get("role")
    if role != UserRole.ADMIN_SISTEMA.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de admin_sistema."
        )
    return payload

def get_current_admin_escuela(payload: dict = Depends(get_current_user_token)) -> dict:
    role = payload.get("role")
    if role != UserRole.ADMIN_ESCUELA.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de admin_escuela."
        )
    return payload

def get_current_representante(payload: dict = Depends(get_current_user_token)) -> dict:
    role = payload.get("role")
    if role != UserRole.REPRESENTANTE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes los permisos suficientes para esta acción. Se requiere rol de representante."
        )
    return payload
