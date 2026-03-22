from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
import re

class SchoolCreate(BaseModel):
    name: str
    year_foundation: int
    state: int
    rif: int
    address: Optional[str] = None
    school_type: int

    model_config = ConfigDict(from_attributes=True)

class StateResponse(BaseModel):
    id: int
    name: str

class SchoolTypeResponse(BaseModel):
    id: int
    name: str

class SystemStatusResponse(BaseModel):
    id: int
    name: str

class ClassroomCategoryResponse(BaseModel):
    id: int
    name: str

class SchoolBasicResponse(BaseModel):
    sch_id: int
    name: str
    year_foundation: int
    state: int
    rif: int
    address: Optional[str] = None
    school_type: int
    is_active: bool

# ──────────────────────────────────────────────────────────
# Read schemas (GET endpoints)
# ──────────────────────────────────────────────────────────

class SchoolRead(BaseModel):
    """Información completa de una escuela."""
    sch_id: int
    name: str
    year_foundation: int
    rif: int
    address: Optional[str] = None
    state: int
    school_type: int
    is_active: bool
    is_deleted: bool

class PaginatedSchoolsResponse(BaseModel):
    data: List[SchoolRead]
    total: int
    page: int
    size: int

class AcademicYearBasicRead(BaseModel):
    """Datos básicos de un año académico para embeber en classroom."""
    id: int
    name: str
    init_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool

class ClassroomRead(BaseModel):
    """Información base de un salón + su periodo y escuela."""
    id: int
    level: int
    category: int
    section: Optional[str] = None
    is_deleted: bool
    academic_year: Optional[AcademicYearBasicRead] = None
    school: Optional[SchoolBasicResponse] = None

class PaginatedClassroomsResponse(BaseModel):
    data: List[ClassroomRead]
    total: int
    page: int
    size: int

class StudentSchoolInfo(BaseModel):
    """Datos básicos de la escuela para embeber en la respuesta de estudiante."""
    sch_id: int
    name: str

class StudentClassroomInfo(BaseModel):
    """Datos básicos del salón para embeber en la respuesta de estudiante."""
    id: int
    level: int
    category: int
    section: Optional[str] = None

class StudentRead(BaseModel):
    """Información base del estudiante con escuela y salón vinculados."""
    id: int
    name: str
    lastname: str
    birthday: Optional[str] = None
    gender: Optional[str] = None
    blood_type: Optional[str] = None
    identity_number: Optional[str] = None
    is_active: bool
    is_deleted: bool
    school: Optional[StudentSchoolInfo] = None
    classroom: Optional[StudentClassroomInfo] = None

class PaginatedStudentsResponse(BaseModel):
    data: List[StudentRead]
    total: int
    page: int
    size: int

# ──────────────────────────────────────────────────────────
# Create schemas (POST endpoints)
# ──────────────────────────────────────────────────────────

class ClassroomCreate(BaseModel):
    school_id: int
    academic_year_id: int
    category: int       # FK: 1=Preescolar, 2=Primaria, 3=Bachillerato
    level: int
    section: Optional[str] = None

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip().upper()
        if len(v) > 3:
            raise ValueError("La sección no puede tener más de 3 caracteres de largo.")
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("La sección solo puede contener caracteres alfanuméricos (letras A-Z y números 0-9).")
        return v
