from pydantic import BaseModel, EmailStr, Field
from datetime import date
from typing import Optional


class LoginBase(BaseModel):
    """Credenciales comunes a los portales de autenticación."""

    email: EmailStr = Field(..., description="Correo electrónico registrado de la cuenta")
    password: str = Field(..., description="Contraseña en texto plano de la cuenta")

class UserLogin(LoginBase):
    """Credenciales del portal de clientes (`POST /auth/login`): admin_escuela, doctor y representante."""

class AdminLoginCreate(LoginBase):
    """Credenciales del portal de administración (`POST /auth/admin/login`): solo admin_sistema.

    Esquema separado de `UserLogin` para poder exigir en el futuro campos exclusivos del
    portal de administración (ej. un segundo factor) sin afectar al de clientes.
    """

class SystemAdminRegister(BaseModel):
    """Datos de registro de un administrador de sistema."""

    nombre: str = Field(description="Nombre del administrador.")
    apellido: str = Field(description="Apellido del administrador.")
    correo: EmailStr = Field(description="Correo electrónico con el que iniciará sesión.")
    contraseña: str = Field(description="Contraseña en texto plano; se almacena hasheada.")
    fecha_de_nacimiento: date = Field(description="Fecha de nacimiento (YYYY-MM-DD).")


class SchoolAdminRegister(BaseModel):
    """Datos de registro de un administrador de escuela."""

    nombre: str = Field(description="Nombre del administrador escolar.")
    apellido: str = Field(description="Apellido del administrador escolar.")
    correo: EmailStr = Field(description="Correo electrónico con el que iniciará sesión.")
    contraseña: str = Field(description="Contraseña en texto plano; se almacena hasheada.")
    fecha_de_nacimiento: date = Field(description="Fecha de nacimiento (YYYY-MM-DD).")
    school_id: int = Field(
        description="ID de la escuela a la que queda vinculado. Determina su alcance de datos."
    )
    administrative_position: str = Field(
        description="Cargo administrativo dentro de la escuela, ej. 'Director'."
    )


class DoctorRegister(BaseModel):
    """Datos de registro de un médico escolar."""

    nombre: str = Field(description="Nombre del médico.")
    apellido: str = Field(description="Apellido del médico.")
    correo: EmailStr = Field(description="Correo electrónico con el que iniciará sesión.")
    contraseña: str = Field(description="Contraseña en texto plano; se almacena hasheada.")
    fecha_de_nacimiento: date = Field(description="Fecha de nacimiento (YYYY-MM-DD).")
    doc_license_number: int = Field(description="Número de colegiatura o licencia médica.")
    especially: str = Field(description="Especialidad médica, ej. 'Pediatría'.")


class ParentRegister(BaseModel):
    """Datos de registro de un representante (padre, madre o tutor)."""

    nombre: str = Field(description="Nombre del representante.")
    apellido: str = Field(description="Apellido del representante.")
    correo: EmailStr = Field(description="Correo electrónico con el que iniciará sesión.")
    contraseña: str = Field(description="Contraseña en texto plano; se almacena hasheada.")
    fecha_de_nacimiento: date = Field(description="Fecha de nacimiento (YYYY-MM-DD).")
    identity_number: str = Field(description="Cédula o documento de identidad del representante.")
    type_representative: str = Field(
        description="Parentesco con el estudiante, ej. 'Madre', 'Padre', 'Tutor'."
    )
    occupation: Optional[str] = Field(
        default=None, description="Ocupación o profesión del representante."
    )


class UserResponse(BaseModel):
    """Datos públicos de una cuenta de usuario. Nunca incluye el hash de contraseña."""

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
    """Campos editables del perfil propio. Los omitidos conservan su valor actual."""

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
    """Resultado de una operación sobre la foto de perfil del usuario."""

    photo_url: Optional[str] = Field(None, description="URL pública de la foto de perfil en ImageKit (o null si fue eliminada)")


class Token(BaseModel):
    """Token de acceso JWT emitido tras un login exitoso."""

    access_token: str = Field(description="JWT firmado (HS256) que autentica las siguientes peticiones.")
    token_type: str = Field(
        default="bearer", description="Esquema de autenticación a usar en el header Authorization."
    )
