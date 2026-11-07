from pydantic import BaseModel, Field
from datetime import date


class AcademicYearCreate(BaseModel):
    """Datos para registrar un nuevo período escolar."""

    start_date: date = Field(description="Fecha de inicio del año académico (YYYY-MM-DD).")
    end_date: date = Field(description="Fecha de cierre del año académico (YYYY-MM-DD).")


class AcademicYearResponse(BaseModel):
    """Representación de un año académico tal como se expone al cliente."""

    id: int = Field(description="Identificador único del año académico.")
    name: str = Field(description="Nombre del período, ej. '2025-2026'.")
    start_date: date = Field(description="Fecha de inicio del año académico.")
    end_date: date = Field(description="Fecha de cierre del año académico.")
    is_current: bool = Field(description="True si es el período vigente en la fecha actual.")
    is_active: bool = Field(description="True si el período está habilitado para operar.")
    is_deleted: bool = Field(description="True si el período fue eliminado lógicamente (soft delete).")

    class Config:
        from_attributes = True
