"""Bloques reutilizables de documentación OpenAPI para respuestas de error.

Todos los errores de la API viajan en el envelope unificado ``APIResponse`` con
``success=False`` (ver :mod:`app.core.exceptions`). Este módulo centraliza su
documentación para que los endpoints declaren ``responses=...`` sin duplicar
diccionarios literales en cada ruta.

Ejemplo de uso en un endpoint protegido por escuela::

    @router.get(
        "/classrooms/{classroom_id}",
        response_model=APIResponse[ClassroomRead],
        responses=TENANT_DETAIL_RESPONSES,
    )

Para añadir un código puntual, combina los diccionarios::

    responses={**PROTECTED_RESPONSES, **BAD_REQUEST}

Y para un código que no tenga constante propia, construye la entrada con
:func:`error_response`::

    responses={**PROTECTED_RESPONSES, **error_response(502, "...", "...")}
"""

from typing import Any, Dict

from app.schemas.responses import APIResponse

#: Modelo del envelope devuelto por los handlers globales de excepciones.
#: ``data`` siempre es ``null`` en una respuesta de error.
ErrorEnvelope = APIResponse[None]

ResponsesDict = Dict[int | str, Dict[str, Any]]


def error_response(status_code: int, description: str, message: str) -> ResponsesDict:
    """Construye la entrada OpenAPI de un código de error con el envelope estándar.

    Args:
        status_code: Código HTTP documentado (ej. ``404``).
        description: Texto que Swagger muestra junto al código de estado.
        message: Valor de ejemplo para el campo ``message`` del envelope.

    Returns:
        Diccionario apto para el parámetro ``responses`` de un decorador de ruta.
    """
    return {
        status_code: {
            "model": ErrorEnvelope,
            "description": description,
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": message,
                        "data": None,
                        "errors": None,
                        "meta": None,
                    }
                }
            },
        }
    }


# ──────────────────────────────────────────────────────────
# Códigos individuales
# ──────────────────────────────────────────────────────────

BAD_REQUEST: ResponsesDict = error_response(
    400,
    "Petición inválida: los datos enviados no permiten completar la operación.",
    "No se pudo procesar la solicitud con los datos proporcionados.",
)

UNAUTHORIZED: ResponsesDict = error_response(
    401,
    "Token ausente, inválido, expirado o revocado.",
    "Token inválido o expirado.",
)

FORBIDDEN_ROLE: ResponsesDict = error_response(
    403,
    "El rol del usuario autenticado no tiene permiso sobre este recurso.",
    "No tienes permiso para realizar esta acción.",
)

FORBIDDEN_TENANT: ResponsesDict = error_response(
    403,
    "Rol insuficiente, o el recurso pertenece a otra escuela.",
    "No tienes permiso para acceder a este recurso: pertenece a otra escuela.",
)

NOT_FOUND: ResponsesDict = error_response(
    404,
    "El recurso solicitado no existe.",
    "El recurso solicitado no existe.",
)

CONFLICT: ResponsesDict = error_response(
    409,
    "El recurso ya existe o su estado actual impide la operación.",
    "El recurso ya existe o está en un estado que impide la operación.",
)

UNPROCESSABLE: ResponsesDict = {
    422: {
        "model": APIResponse[None],
        "description": "Error de validación del cuerpo, la ruta o los query params.",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Validation error",
                    "data": None,
                    "errors": [
                        {"loc": ["body", "email"], "msg": "value is not a valid email address", "type": "value_error"}
                    ],
                    "meta": None,
                }
            }
        },
    }
}

INTERNAL_ERROR: ResponsesDict = error_response(
    500,
    "Error inesperado del servidor.",
    "Ocurrió un error interno al procesar la solicitud.",
)


# ──────────────────────────────────────────────────────────
# Presets compuestos
# ──────────────────────────────────────────────────────────

#: Ruta pública (`# PUBLIC_ROUTE`): sin autenticación, pero con validación y errores de servidor.
PUBLIC_RESPONSES: ResponsesDict = {**UNPROCESSABLE, **INTERNAL_ERROR}

#: Ruta pública que resuelve un recurso individual por id.
PUBLIC_DETAIL_RESPONSES: ResponsesDict = {**NOT_FOUND, **UNPROCESSABLE, **INTERNAL_ERROR}

#: Ruta con gate de rol (`Depends(get_current_*)`) sin alcance de escuela.
PROTECTED_RESPONSES: ResponsesDict = {
    **UNAUTHORIZED,
    **FORBIDDEN_ROLE,
    **UNPROCESSABLE,
    **INTERNAL_ERROR,
}

#: Ruta con gate de rol que resuelve un recurso individual por id.
PROTECTED_DETAIL_RESPONSES: ResponsesDict = {**PROTECTED_RESPONSES, **NOT_FOUND}

#: Ruta con alcance de escuela: el 403 cubre rol insuficiente y recurso de otra escuela.
TENANT_RESPONSES: ResponsesDict = {
    **UNAUTHORIZED,
    **FORBIDDEN_TENANT,
    **UNPROCESSABLE,
    **INTERNAL_ERROR,
}

#: Ruta con alcance de escuela sobre un recurso individual (404 si no existe, 403 si es ajeno).
TENANT_DETAIL_RESPONSES: ResponsesDict = {**TENANT_RESPONSES, **NOT_FOUND}

#: Creación con gate de rol: añade 400 por datos de negocio inválidos.
CREATE_RESPONSES: ResponsesDict = {**PROTECTED_RESPONSES, **BAD_REQUEST}

#: Creación con alcance de escuela.
TENANT_CREATE_RESPONSES: ResponsesDict = {**TENANT_RESPONSES, **BAD_REQUEST}
