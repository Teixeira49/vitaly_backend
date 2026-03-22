from fastapi import APIRouter
from app.schemas.user import SystemAdminRegister, SchoolAdminRegister, DoctorRegister, UserLogin, Token
from app.schemas.responses import APIResponse
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/register-system-admin", response_model=APIResponse[str])
def register_system_admin(user_in: SystemAdminRegister):
    """
    Register a new system admin. The user will be created with is_active=False and must wait for verification.
    """
    msg = auth_service.register_system_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de sistema")

@router.post("/register-school-admin", response_model=APIResponse[str])
def register_school_admin(user_in: SchoolAdminRegister):
    """
    Register a new school administrator. The user will be created with is_active=False and must wait for verification.
    Requires school_id and administrative_position.
    """
    msg = auth_service.register_school_admin(user_in)
    return APIResponse(data=msg, message="Registro completado para administrador de escuela")

@router.post("/register-doctor", response_model=APIResponse[str])
def register_doctor(user_in: DoctorRegister):
    """
    Register a new doctor. The user will be created with is_active=False and must wait for verification.
    Requires doc_license_number and especially.
    """
    msg = auth_service.register_doctor(user_in)
    return APIResponse(data=msg, message="Registro completado para doctor")

@router.post("/login", response_model=APIResponse[Token])
def login(user_in: UserLogin):
    """
    Login endpoint. Requires an active, non-deleted user with valid credentials.
    """
    token_response = auth_service.authenticate_user(user_in)
    return APIResponse(data=token_response, message="Login exitoso")
