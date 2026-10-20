from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime


class EventCreate(BaseModel):
    """Esquema para la creación de un evento con sus participaciones."""

    title: str = Field(description="Título del evento mostrado en el calendario escolar.")
    description: Optional[str] = Field(
        default=None, description="Descripción o detalle opcional del evento."
    )
    init_time: datetime = Field(description="Fecha y hora de inicio del evento (ISO 8601).")
    ent_time: datetime = Field(
        description="Fecha y hora de finalización del evento. Debe ser posterior a 'init_time'."
    )
    classroom_ids: List[int] = Field(
        description="IDs de los salones convocados al evento. Debe incluir al menos uno."
    )
    doctor_ids: List[int] = Field(
        description="IDs de los médicos asignados al evento. Debe incluir al menos uno."
    )

    @field_validator("ent_time")
    @classmethod
    def validate_end_after_start(cls, v, info):
        if "init_time" in info.data and v <= info.data["init_time"]:
            raise ValueError("La fecha de finalización debe ser posterior a la de inicio.")
        return v

    @field_validator("classroom_ids")
    @classmethod
    def validate_classrooms_not_empty(cls, v):
        if not v:
            raise ValueError("Debe incluir al menos un salón en el evento.")
        return v

    @field_validator("doctor_ids")
    @classmethod
    def validate_doctors_not_empty(cls, v):
        if not v:
            raise ValueError("Debe incluir al menos un doctor en el evento.")
        return v


class EventUpdate(BaseModel):
    """Esquema para la actualización parcial de un evento (solo datos base).

    Los campos omitidos conservan su valor actual; las participaciones de salones y
    médicos se gestionan en endpoints dedicados.
    """

    title: Optional[str] = Field(default=None, description="Nuevo título del evento.")
    description: Optional[str] = Field(default=None, description="Nueva descripción del evento.")
    init_time: Optional[datetime] = Field(
        default=None, description="Nueva fecha y hora de inicio del evento (ISO 8601)."
    )
    ent_time: Optional[datetime] = Field(
        default=None, description="Nueva fecha y hora de finalización del evento (ISO 8601)."
    )
