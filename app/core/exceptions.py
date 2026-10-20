"""Handlers globales que envuelven los errores en el formato ``APIResponse``."""

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.schemas.responses import APIResponse, ErrorDetail

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

    Args:
        request: Petición que originó el error. No se usa, lo exige Starlette.
        exc: Excepción HTTP con su ``status_code`` y ``detail``.

    Returns:
        JSONResponse: El ``status_code`` original con ``success=False`` y el
        ``detail`` de la excepción en ``message``.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(success=False, message=str(exc.detail)).model_dump()
    )
