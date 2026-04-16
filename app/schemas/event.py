from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime


class EventCreate(BaseModel):
    """Esquema para la creación de un evento con sus participaciones."""
    title: str
    description: Optional[str] = None
    init_time: datetime
    ent_time: datetime
    classroom_ids: List[int]
    doctor_ids: List[int]

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
    """Esquema para la actualización parcial de un evento (solo datos base)."""
    title: Optional[str] = None
    description: Optional[str] = None
    init_time: Optional[datetime] = None
    ent_time: Optional[datetime] = None
