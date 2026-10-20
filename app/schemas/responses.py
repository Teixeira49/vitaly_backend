from typing import Generic, TypeVar, Optional, List, Union
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadatos de paginación que acompañan a un listado en ``APIResponse.meta``."""

    page: int = Field(description="Número de página actual, comenzando en 1.")
    size: int = Field(description="Cantidad de elementos solicitados por página.")
    total: int = Field(description="Total de registros disponibles que cumplen el filtro.")
    total_pages: int = Field(description="Número total de páginas resultante de 'total' y 'size'.")


class ErrorDetail(BaseModel):
    """Detalle individual de un error de validación (formato de Pydantic/FastAPI)."""

    loc: Optional[List[Union[str, int]]] = Field(
        default=None,
        description="Ruta del campo que falló, ej. ['body', 'email'].",
    )
    msg: str = Field(description="Mensaje legible que describe el error de validación.")
    type: str = Field(description="Identificador del tipo de error, ej. 'value_error'.")


class APIResponse(BaseModel, Generic[T]):
    """Envelope unificado de respuesta de la API de Vitaly.

    Todo endpoint JSON (éxito o error) devuelve esta estructura. Las descargas de
    archivos son la única excepción documentada en la respuesta exitosa; sus errores
    sí usan este envelope.
    """

    success: bool = Field(
        default=True,
        description="True si la operación se completó; False en cualquier respuesta de error.",
    )
    message: Optional[str] = Field(
        default=None,
        description="Mensaje descriptivo del resultado, apto para mostrarse al usuario final.",
    )
    data: Optional[T] = Field(
        default=None,
        description="Carga útil de la operación. Es null en las respuestas de error.",
    )
    errors: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Lista de errores de validación. Solo se completa en respuestas 422.",
    )
    meta: Optional[PaginationMeta] = Field(
        default=None,
        description="Metadatos de paginación. Solo presente en listados paginados.",
    )

    class Config:
        from_attributes = True
