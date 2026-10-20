from pydantic import BaseModel, EmailStr, Field
from datetime import date
from app.schemas.enums import UserRole
from typing import Optional

class LoginBase(BaseModel):
    email: EmailStr = Field(..., description="Correo electrónico registrado de la cuenta")
    password: str = Field(..., description="Contraseña en texto plano de la cuenta")

class ClientLoginCreate(LoginBase):
    """Credenciales del portal de clientes (`POST /auth/client/login`): admin_escuela, doctor y representante."""

class AdminLoginCreate(LoginBase):
    """Credenciales del portal de administración (`POST /auth/admin/login`): solo admin_sistema.

    Esquema separado de `ClientLoginCreate` para poder exigir en el futuro campos exclusivos del
    portal de administración (ej. un segundo factor) sin afectar al de clientes.
    """

class SystemAdminRegister(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    contraseña: str
    fecha_de_nacimiento: date

class SchoolAdminRegister(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    contraseña: str
    fecha_de_nacimiento: date
    school_id: int
    administrative_position: str

class DoctorRegister(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    contraseña: str
    fecha_de_nacimiento: date
    doc_license_number: int
    especially: str

class ParentRegister(BaseModel):
    nombre: str
    apellido: str
    correo: EmailStr
    contraseña: str
    fecha_de_nacimiento: date
    identity_number: str
    type_representative: str
    occupation: Optional[str] = None

class UserResponse(BaseModel):
    id: str = Field(..., description="Identificador único del usuario")
    email: str = Field(..., description="Correo electrónico del usuario")
    first_name: str = Field(..., description="Nombre del usuario")
    last_name: str = Field(..., description="Apellido del usuario")
    birth_date: date = Field(..., description="Fecha de nacimiento del usuario")
    is_active: bool = Field(..., description="Indica si la cuenta está activa")
    photo_url: Optional[str] = Field(None, description="URL pública de la foto de perfil en ImageKit")
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Nombre(s) del usuario")
    lastname: Optional[str] = Field(None, description="Apellido(s) del usuario")
    identity_number: Optional[str] = Field(None, description="Cédula o número de documento de identidad")
    birthday: Optional[date] = Field(None, description="Fecha de nacimiento")
    gender: Optional[str] = Field(None, description="Género del usuario")
    address: Optional[str] = Field(None, description="Dirección de habitación")
    biography: Optional[str] = Field(None, description="Biografía o resumen personal")
    # photo_url is intentionally not updatable here: it is managed only through
    # the /profile/photo upload and delete endpoints. Unknown fields are ignored.

class UserPhotoResponse(BaseModel):
    photo_url: Optional[str] = Field(None, description="URL pública de la foto de perfil en ImageKit (o null si fue eliminada)")

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

