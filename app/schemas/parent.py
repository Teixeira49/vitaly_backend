"""Esquemas del perfil propio del representante (`/parent/profile`)."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.enums import Gender


class ParentProfileRead(BaseModel):
    """Perfil del representante autenticado: datos de `user` y de `parent`.

    Nunca incluye la contraseña ni el identificador interno de la foto en ImageKit
    (`photo_file_id`).
    """

    id: int = Field(description="ID del registro del representante en la tabla 'parent'.")
    user_id: int = Field(description="ID de la cuenta de usuario del representante.")
    email: str = Field(description="Correo electrónico con el que inicia sesión.")
    name: str = Field(description="Nombre(s) del representante.")
    lastname: str = Field(description="Apellido(s) del representante.")
    identity_number: Optional[str] = Field(
        description="Cédula o documento de identidad. Se usa para vincular estudiantes autorizados."
    )
    birthday: Optional[date] = Field(description="Fecha de nacimiento (YYYY-MM-DD).")
    gender: Optional[str] = Field(description="Género registrado, o null si no se especificó.")
    address: Optional[str] = Field(description="Dirección de habitación, o null si no se especificó.")
    photo_url: Optional[str] = Field(
        description="URL pública de la foto de perfil en ImageKit, o null si no tiene foto."
    )
    occupation: Optional[str] = Field(description="Ocupación o profesión del representante.")
    type_representative: Optional[str] = Field(
        description="Parentesco con los estudiantes, ej. 'Madre', 'Padre', 'Tutor'."
    )


class ParentProfileUpdate(BaseModel):
    """Campos editables del perfil propio del representante. Los omitidos conservan su valor.

    No permite cambiar email, rol, contraseña, foto ni documento de identidad: el
    documento determina qué estudiantes se vinculan al representante, por lo que
    editarlo por esta vía permitiría vincularse a estudiantes ajenos. Cualquier
    campo no declarado se rechaza con 422.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Nombre(s) del representante."
    )
    lastname: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Apellido(s) del representante."
    )
    birthday: Optional[date] = Field(None, description="Fecha de nacimiento (YYYY-MM-DD).")
    gender: Optional[Gender] = Field(None, description="Género del representante.")
    address: Optional[str] = Field(
        None, max_length=255, description="Dirección de habitación."
    )
    occupation: Optional[str] = Field(
        None, max_length=100, description="Ocupación o profesión del representante."
    )
    type_representative: Optional[str] = Field(
        None,
        min_length=1,
        max_length=50,
        description="Parentesco con los estudiantes, ej. 'Madre', 'Padre', 'Tutor'.",
    )

    @field_validator("name", "lastname", "birthday", "type_representative")
    @classmethod
    def reject_explicit_null(cls, value):
        """Rechaza `null` explícito en campos obligatorios del perfil.

        Args:
            value: Valor enviado por el cliente para el campo.

        Returns:
            El mismo valor si no es `None`.

        Raises:
            ValueError: Si el cliente envía `null` en un campo que no admite vacío.
        """
        if value is None:
            raise ValueError("El campo no puede ser null; omítelo para conservar su valor actual.")
        return value
