from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date
from app.schemas.enums import Gender, BloodType

class StudentCreate(BaseModel):
    name: str
    lastname: str
    birthday: date
    gender: Gender
    blood_type: Optional[BloodType] = None
    identity_number: Optional[str] = None

    @field_validator("birthday")
    @classmethod
    def validate_birthday(cls, v: date) -> date:
        today = date.today()
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if age > 21:
            raise ValueError("El estudiante no puede ser mayor a 21 años.")
        if v > today:
            raise ValueError("La fecha de nacimiento no puede ser una fecha futura.")
        return v

class StudentUpdate(BaseModel):
    """Campos opcionales para actualizar un estudiante. is_active e is_deleted no son modificables desde este endpoint."""
    name: Optional[str] = None
    lastname: Optional[str] = None
    birthday: Optional[date] = None
    gender: Optional[Gender] = None
    blood_type: Optional[BloodType] = None
    identity_number: Optional[str] = None

    @field_validator("birthday")
    @classmethod
    def validate_birthday(cls, v: Optional[date]) -> Optional[date]:
        if v is None:
            return v
        today = date.today()
        # Detectar fechas imposibles ya es tarea de Pydantic al parsear `date`,
        # pero validamos la regla de negocio: no mayor de 21 ni fecha futura.
        age = today.year - v.year - ((today.month, today.day) < (v.month, v.day))
        if v > today:
            raise ValueError("La fecha de nacimiento no puede ser una fecha futura.")
        if age > 21:
            raise ValueError("El estudiante no puede ser mayor a 21 años.")
        return v

class StudentResponse(BaseModel):
    id: int
    name: str
    lastname: str
    birthday: Optional[date] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    identity_number: Optional[str] = None
    is_active: bool
    is_deleted: bool
from typing import List

class ClassroomRegistrationCreate(BaseModel):
    student_id: int
    academic_year_id: int
    classroom_id: int
    status_id: Optional[int] = 2

class BulkClassroomRegistrationCreate(BaseModel):
    student_ids: List[int]
    academic_year_id: int
    classroom_id: int
    status_id: Optional[int] = 2
