"""Handlers globales que envuelven los errores en el formato ``APIResponse``."""

from typing import Optional, Sequence, Union

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.responses import APIResponse, ErrorDetail


class FieldValidationError(HTTPException):
    """``HTTPException`` de negocio asociada a un campo concreto del cuerpo.

    Permite que un servicio rechace un dato con la misma forma que un error de
    validación de Pydantic (``errors[].loc`` / ``msg`` / ``type``), para que el
    frontend pueda mostrar el mensaje junto al campo responsable sin inspeccionar
    el texto de ``message``.

    El ``message`` del envelope y el ``msg`` del detalle son el mismo texto: no
    deben revelar umbrales, márgenes ni ninguna otra regla interna.

    Args:
        loc: Ruta del campo que falló, ej. ``["body", "init_time"]``.
        msg: Mensaje legible y genérico, apto para mostrarse al usuario final.
        error_type: Identificador estable del error, ej.
            ``"event_schedule_unavailable"``. Es el contrato que consume el
            frontend; no cambia aunque cambie el texto del mensaje.
        status_code: Código HTTP a devolver. Por defecto 422, igual que los
            errores de validación de Pydantic.
    """

    def __init__(
        self,
        *,
        loc: Sequence[Union[str, int]],
        msg: str,
        error_type: str,
        status_code: int = 422,
    ) -> None:
        super().__init__(status_code=status_code, detail=msg)
        self.errors: list[ErrorDetail] = [
            ErrorDetail(loc=list(loc), msg=msg, type=error_type)
        ]


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Traduce un error de validación de Pydantic al envelope ``APIResponse``.

    Registrado en ``app/main.py`` para ``RequestValidationError``.

    Args:
        request: Petición que falló la validación. No se usa, lo exige Starlette.
        exc: Excepción de validación con la lista de errores por campo.

    Returns:
        JSONResponse: 422 con ``success=False``, ``message="Validation error"`` y
        la lista de :class:`~app.schemas.responses.ErrorDetail` en ``errors``.
    """
    errors = [ErrorDetail(loc=err["loc"], msg=err["msg"], type=err["type"]) for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(success=False, message="Validation error", errors=errors).model_dump()
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Traduce cualquier ``HTTPException`` al envelope ``APIResponse``.

    Registrado en ``app/main.py`` para ``StarletteHTTPException``. Las excepciones
    que no derivan de ella (ej. ``APIError`` de supabase-py) no pasan por aquí y
    producen un 500 sin envelope: los servicios deben relanzarlas como
    ``HTTPException(500)``.

    Si la excepción es una :class:`FieldValidationError`, su lista ``errors`` se
    propaga al envelope para que el error quede asociado a un campo.

    Args:
        request: Petición que originó el error. No se usa, lo exige Starlette.
        exc: Excepción HTTP con su ``status_code`` y ``detail``.

    Returns:
        JSONResponse: El ``status_code`` original con ``success=False``, el
        ``detail`` de la excepción en ``message`` y, si existen, los detalles por
        campo en ``errors``.
    """
    errors: Optional[list[ErrorDetail]] = getattr(exc, "errors", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(success=False, message=str(exc.detail), errors=errors).model_dump()
    )
