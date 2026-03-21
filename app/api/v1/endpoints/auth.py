from fastapi import APIRouter
from app.schemas.user import UserRegister, UserLogin, Token
from app.schemas.responses import APIResponse
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/register", response_model=APIResponse[str])
def register(user_in: UserRegister):
    """
    Register a new user. The user will be created with is_active=False and must wait for verification.
    """
    msg = auth_service.register_user(user_in)
    return APIResponse(data=msg, message="Registro completado")

@router.post("/login", response_model=APIResponse[Token])
def login(user_in: UserLogin):
    """
    Login endpoint. Requires an active, non-deleted user with valid credentials.
    """
    token_response = auth_service.authenticate_user(user_in)
    return APIResponse(data=token_response, message="Login exitoso")
