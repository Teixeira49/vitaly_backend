from pydantic import BaseModel, EmailStr
from datetime import date
from app.schemas.enums import UserRole
from typing import Optional

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
    id: str
    email: str
    first_name: str
    last_name: str
    birth_date: date
    is_active: bool
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
