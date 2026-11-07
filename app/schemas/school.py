from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List
import re


class SchoolCreate(BaseModel):
    """Datos para registrar una nueva escuela en el sistema."""

    name: str = Field(description="Nombre oficial de la institución educativa.")
    year_foundation: int = Field(description="Año de fundación de la escuela (ej. 1998).")
    state: int = Field(description="ID del estado donde se ubica la escuela (catálogo 'states').")
    rif: int = Field(description="RIF de la institución, sin guiones ni letra identificadora.")
    address: Optional[str] = Field(default=None, description="Dirección física de la escuela.")
    school_type: int = Field(
        description="ID del tipo de escuela (catálogo 'school_type': pública, privada, etc.)."
    )

    model_config = ConfigDict(from_attributes=True)


class StateResponse(BaseModel):
    """Entrada del catálogo global de estados del país."""

    id: int = Field(description="Identificador único del estado.")
    name: str = Field(description="Nombre del estado.")


class SchoolTypeResponse(BaseModel):
    """Entrada del catálogo global de tipos de escuela."""

    id: int = Field(description="Identificador único del tipo de escuela.")
    name: str = Field(description="Nombre del tipo de escuela, ej. 'Pública'.")


class SystemStatusResponse(BaseModel):
    """Entrada del catálogo global de estados del sistema (status de registros)."""

    id: int = Field(description="Identificador único del estado del sistema.")
    name: str = Field(description="Nombre del estado, ej. 'Inscrito'.")


class ClassroomCategoryResponse(BaseModel):
    """Entrada del catálogo global de categorías de salón (nivel educativo)."""

    id: int = Field(description="Identificador único de la categoría.")
    name: str = Field(description="Nombre de la categoría, ej. 'Primaria'.")


class SchoolBasicResponse(BaseModel):
    """Datos básicos de una escuela para embeber en otras respuestas."""

    sch_id: int = Field(description="Identificador único de la escuela.")
    name: str = Field(description="Nombre oficial de la institución educativa.")
    year_foundation: int = Field(description="Año de fundación de la escuela.")
    state: int = Field(description="ID del estado donde se ubica la escuela.")
    rif: int = Field(description="RIF de la institución.")
    address: Optional[str] = Field(default=None, description="Dirección física de la escuela.")
    school_type: int = Field(description="ID del tipo de escuela.")
    is_active: bool = Field(description="True si la escuela está habilitada para operar.")


# ──────────────────────────────────────────────────────────
# Read schemas (GET endpoints)
# ──────────────────────────────────────────────────────────

class SchoolRead(BaseModel):
    """Información completa de una escuela."""

    sch_id: int = Field(description="Identificador único de la escuela.")
    name: str = Field(description="Nombre oficial de la institución educativa.")
    year_foundation: int = Field(description="Año de fundación de la escuela.")
    rif: int = Field(description="RIF de la institución.")
    address: Optional[str] = Field(default=None, description="Dirección física de la escuela.")
    state: int = Field(description="ID del estado donde se ubica la escuela.")
    school_type: int = Field(description="ID del tipo de escuela.")
    is_active: bool = Field(description="True si la escuela está habilitada para operar.")
    is_deleted: bool = Field(
        description="True si la escuela fue eliminada lógicamente (soft delete)."
    )


class PaginatedSchoolsResponse(BaseModel):
    """Página de escuelas.

    Formato legado: la paginación viaja anidada dentro de ``APIResponse.data`` en
    lugar de ``APIResponse.meta``. No se migra sin coordinar con el frontend.
    """

    data: List[SchoolRead] = Field(description="Escuelas contenidas en la página actual.")
    total: int = Field(description="Total de escuelas que cumplen el filtro aplicado.")
    page: int = Field(description="Número de página actual, comenzando en 1.")
    size: int = Field(description="Cantidad de escuelas solicitadas por página.")


class AcademicYearBasicRead(BaseModel):
    """Datos básicos de un año académico para embeber en classroom."""

    id: int = Field(description="Identificador único del año académico.")
    name: str = Field(description="Nombre del período, ej. '2025-2026'.")
    init_date: Optional[str] = Field(
        default=None, description="Fecha de inicio del período (YYYY-MM-DD)."
    )
    end_date: Optional[str] = Field(
        default=None, description="Fecha de cierre del período (YYYY-MM-DD)."
    )
    is_current: bool = Field(description="True si es el período vigente en la fecha actual.")


class ClassroomRead(BaseModel):
    """Información base de un salón + su periodo y escuela."""

    id: int = Field(description="Identificador único del salón.")
    level: int = Field(description="Grado o nivel del salón dentro de su categoría, ej. 3.")
    category: int = Field(
        description="ID de la categoría del salón (1=Preescolar, 2=Primaria, 3=Bachillerato)."
    )
    section: Optional[str] = Field(
        default=None, description="Sección del salón, ej. 'A'. Máximo 3 caracteres alfanuméricos."
    )
    is_deleted: bool = Field(description="True si el salón fue eliminado lógicamente (soft delete).")
    academic_year: Optional[AcademicYearBasicRead] = Field(
        default=None, description="Año académico al que pertenece el salón."
    )
    school: Optional[SchoolBasicResponse] = Field(
        default=None, description="Escuela propietaria del salón."
    )


class PaginatedClassroomsResponse(BaseModel):
    """Página de salones.

    Formato legado: la paginación viaja anidada dentro de ``APIResponse.data``.
    """

    data: List[ClassroomRead] = Field(description="Salones contenidos en la página actual.")
    total: int = Field(description="Total de salones que cumplen el filtro aplicado.")
    page: int = Field(description="Número de página actual, comenzando en 1.")
    size: int = Field(description="Cantidad de salones solicitados por página.")


class StudentSchoolInfo(BaseModel):
    """Datos básicos de la escuela para embeber en la respuesta de estudiante."""

    sch_id: int = Field(description="Identificador único de la escuela.")
    name: str = Field(description="Nombre de la escuela.")


class StudentClassroomInfo(BaseModel):
    """Datos básicos del salón para embeber en la respuesta de estudiante."""

    id: int = Field(description="Identificador único del salón.")
    level: int = Field(description="Grado o nivel del salón dentro de su categoría.")
    category: int = Field(description="ID de la categoría del salón (nivel educativo).")
    section: Optional[str] = Field(default=None, description="Sección del salón, ej. 'A'.")


class StudentRead(BaseModel):
    """Información base del estudiante con escuela y salón vinculados."""

    id: int = Field(description="Identificador único del estudiante.")
    name: str = Field(description="Nombre del estudiante.")
    lastname: str = Field(description="Apellido del estudiante.")
    birthday: Optional[str] = Field(
        default=None, description="Fecha de nacimiento del estudiante (YYYY-MM-DD)."
    )
    gender: Optional[str] = Field(default=None, description="Género del estudiante.")
    blood_type: Optional[str] = Field(default=None, description="Tipo de sangre del estudiante.")
    identity_number: Optional[str] = Field(
        default=None, description="Documento de identidad del estudiante."
    )
    is_active: bool = Field(description="True si el estudiante está activo en la escuela.")
    is_deleted: bool = Field(
        description="True si el estudiante fue eliminado lógicamente (soft delete)."
    )
    school: Optional[StudentSchoolInfo] = Field(
        default=None, description="Escuela en la que está inscrito el estudiante."
    )
    classroom: Optional[StudentClassroomInfo] = Field(
        default=None, description="Salón en el que está inscrito el estudiante."
    )


class PaginatedStudentsResponse(BaseModel):
    """Página de estudiantes.

    Formato legado: la paginación viaja anidada dentro de ``APIResponse.data``.
    """

    data: List[StudentRead] = Field(description="Estudiantes contenidos en la página actual.")
    total: int = Field(description="Total de estudiantes que cumplen el filtro aplicado.")
    page: int = Field(description="Número de página actual, comenzando en 1.")
    size: int = Field(description="Cantidad de estudiantes solicitados por página.")


# ──────────────────────────────────────────────────────────
# Create schemas (POST endpoints)
# ──────────────────────────────────────────────────────────

class ClassroomCreate(BaseModel):
    """Datos para crear un salón dentro de una escuela y un año académico."""

    school_id: int = Field(description="ID de la escuela propietaria del salón.")
    academic_year_id: int = Field(description="ID del año académico al que pertenece el salón.")
    category: int = Field(
        description="ID de la categoría del salón (1=Preescolar, 2=Primaria, 3=Bachillerato)."
    )
    level: int = Field(description="Grado o nivel del salón dentro de su categoría, ej. 3.")
    section: Optional[str] = Field(
        default=None,
        description="Sección del salón, ej. 'A'. Máximo 3 caracteres alfanuméricos; se normaliza a mayúsculas.",
    )

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
