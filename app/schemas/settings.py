"""Esquemas de la configuración global del sistema (tabla ``settings``)."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.enums import SettingKey, SettingValueType


class SettingValue(BaseModel):
    """Valor autodescriptivo de una configuración: tipo declarado y dato.

    Replica la estructura del JSON almacenado en ``settings.value`` y los CHECK
    de la migración: ``{"type": "integer", "value": 5}``.
    """

    type: SettingValueType = Field(
        description="Tipo de dato del valor: integer, number, string, boolean o json."
    )
    value: Any = Field(
        description="Dato de la configuración, coherente con el tipo declarado en 'type'."
    )


class SettingRead(BaseModel):
    """Configuración tal como la expone la API al administrador de sistema."""

    key: SettingKey = Field(description="Clave que identifica el tipo de configuración.")
    value: SettingValue = Field(description="Tipo declarado y valor vigente de la configuración.")
    description: Optional[str] = Field(
        default=None, description="Explicación de para qué sirve la configuración."
    )
    updated_at: Optional[datetime] = Field(
        default=None, description="Fecha y hora de la última modificación del valor."
    )


class SettingUpdate(BaseModel):
    """Cuerpo para crear o modificar el valor de una configuración existente.

    La clave viaja en la ruta; el cuerpo solo transporta el valor y, de forma
    opcional, una descripción nueva.
    """

    value: SettingValue = Field(
        description="Nuevo valor de la configuración, con su tipo declarado."
    )
    description: Optional[str] = Field(
        default=None,
        description="Descripción a guardar. Si se omite, conserva la existente.",
    )
