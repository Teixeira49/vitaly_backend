from fastapi import HTTPException, status
from app.core.database import supabase
from app.core.security import get_password_hash, verify_password, create_access_token
from app.schemas.user import UserRegister, UserLogin, Token
from app.schemas.enums import UserRole
import uuid

class AuthService:
    def register_user(self, user_in: UserRegister):
        # 1. Verificar si el usuario ya existe (usamos tabla 'user' singular)
        user_response = supabase.table("user").select("id").eq("email", user_in.correo).execute()
        
        if user_response.data:
            user_id = user_response.data[0]["id"]
            roles_response = supabase.table("user_roles").select("role").eq("user_id", user_id).execute()
            role = roles_response.data[0]["role"] if roles_response.data else "desconocido"
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario ya existe bajo el rol: {role}"
            )
        
        # 2. Insertar en la tabla maestra 'user'
        hashed_password = get_password_hash(user_in.contraseña)
        user_data = {
            "email": user_in.correo,
            "password": hashed_password,
            "name": user_in.nombre,
            "lastname": user_in.apellido,
            "birthday": user_in.fecha_de_nacimiento.isoformat(),
            "is_active": False,
            "is_deleted": False
        }
        
        # INSERT ... RETURNING id
        user_result = supabase.table("user").insert(user_data).execute()
        if not user_result.data:
            raise HTTPException(status_code=500, detail="Error al crear el usuario base")
            
        new_user_id = user_result.data[0]["id"]
        
        # 3. Insertar el mapeo de rol en 'user_roles'
        role_data = {
            "user_id": new_user_id,
            "role": user_in.role.value,
            "is_active": False
        }
        supabase.table("user_roles").insert(role_data).execute()
        
        # 4. Insertar en la tabla de detalle específica según el rol
        self._create_role_profile(new_user_id, user_in.role)
        
        return "El usuario ha sido creado exitosamente, pero debe esperar a ser verificado en el sistema para continuar."

    def _create_role_profile(self, user_id: int, role: UserRole):
        """Crea el perfil inicial según el rol del usuario."""
        if role == UserRole.ADMIN_SISTEMA:
            supabase.table("system_administrator").insert({
                "admin_id": user_id,
                "level_privilege": 1 # Nivel básico por defecto
            }).execute()
            
        elif role == UserRole.ADMIN_ESCUELA:
            supabase.table("school_administrator").insert({
                "user_id": user_id,
                "status": 2 # Estado 'Inactivo/Pendiente' usualmente
            }).execute()
            
        elif role == UserRole.DOCTOR:
            supabase.table("doctor").insert({
                "user_id": user_id
            }).execute()
            
        elif role == UserRole.REPRESENTANTE:
            supabase.table("parent").insert({
                "user_id": user_id,
                "is_active": False,
                "is_deleted": False
            }).execute()
        
    def authenticate_user(self, user_in: UserLogin):
        user_response = supabase.table("user").select("*").eq("email", user_in.email).execute()
        if not user_response.data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
            
        user = user_response.data[0]
        
        if user.get("is_deleted", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario ha sido eliminado"
            )
            
        if not user.get("is_active", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario está inactivo, debe esperar verificación"
            )
            
        if not verify_password(user_in.password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales incorrectas"
            )
            
        # Generar token
        token_data = {"sub": str(user["id"])}
        access_token = create_access_token(data=token_data)
        
        return Token(access_token=access_token, token_type="bearer")

auth_service = AuthService()
