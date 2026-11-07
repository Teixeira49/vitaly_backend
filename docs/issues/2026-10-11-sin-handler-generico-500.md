---
title: "[🐛 Bug] Sin handler genérico de Exception: los 500 no usan el envelope APIResponse"
labels: [bug, P2, api]
issue: 16
url: https://github.com/Teixeira49/vitaly_backend/issues/16
---

## Descripción

La aplicación solo registra handlers para `RequestValidationError` y `HTTPException`. Cualquier excepción no controlada (error de red con Supabase, `KeyError`, `IndexError` sobre `response.data[0]`, etc.) llega al `ServerErrorMiddleware` de Starlette, que responde `500` en texto plano (`Internal Server Error`), no con el envelope `APIResponse`. Además, esa respuesta se genera fuera de `CORSMiddleware`, por lo que el navegador la ve sin cabeceras CORS y el frontend recibe un error de red opaco en lugar de un 500 legible.

## Evidencia

- `app/main.py:45-46` — solo se registran `validation_exception_handler` y `http_exception_handler`.
- `app/core/exceptions.py:7` y `:14` — el módulo define únicamente esos dos handlers; no hay handler para `Exception`.
- Ejemplos de código que puede lanzar excepciones no controladas: accesos `response.data[0]` sin comprobar, p. ej. `app/services/auth_service.py:48` si el insert no devuelve el formato esperado, o cualquier fallo de red de supabase-py fuera de un `try`.
- Reproducción: en un test, sobrescribir una dependencia o un servicio para que lance `RuntimeError("boom")` y llamar al endpoint con `TestClient(app, raise_server_exceptions=False)`: el cuerpo es `Internal Server Error` (texto), no JSON.
- El skill `standard-api-responses` documenta la carencia ("There is **no** catch-all `Exception` handler").

## Comportamiento actual vs esperado

- **Actual:** 500 en texto plano, sin `success`/`message`, y sin cabeceras CORS para el frontend.
- **Esperado:** todo error responde con `APIResponse(success=False, message=...)` (`.agents/rules/standard-response.md`), con un mensaje genérico que no filtre detalles internos, y el detalle registrado en logs del servidor.

## Impacto

- ¿Expone datos médicos/PHR o PII? No directamente. Riesgo lateral: varios endpoints hacen `raise HTTPException(500, detail=f"...{str(e)}")` (p. ej. `app/api/v1/endpoints/academic_year.py:41`, `:88`) y `/health` devuelve `str(e)` (`app/main.py:63`), filtrando mensajes internos de la base de datos al cliente. Un handler genérico es el lugar natural para dejar de hacerlo.
- ¿Fuga entre escuelas? No.
- Roles afectados: todos; el frontend no puede mostrar un mensaje coherente ante fallos inesperados.

## Propuesta de solución

1. Añadir en `app/core/exceptions.py` un `unhandled_exception_handler(request, exc: Exception)` que registre la traza con `logging` y devuelva `JSONResponse(status_code=500, content=APIResponse(success=False, message="Error interno del servidor").model_dump())`.
2. Registrarlo en `app/main.py` con `app.add_exception_handler(Exception, unhandled_exception_handler)`.
3. Verificar que la respuesta 500 incluya cabeceras CORS (en Starlette el handler de `Exception` se ejecuta en `ServerErrorMiddleware`, fuera de `CORSMiddleware`; si no llegan, valorar un middleware propio que capture la excepción dentro de la pila).
4. (Seguimiento) Sustituir `detail=f"...{str(e)}"` por mensajes genéricos y dejar el detalle en logs.

## Criterios de aceptación

- [ ] Una excepción no controlada en un endpoint produce 500 con cuerpo JSON `{"success": false, "message": "...", ...}`.
- [ ] El mensaje no contiene el texto de la excepción original.
- [ ] La traza queda registrada en el log del servidor.
- [ ] La respuesta 500 llega al navegador con `Access-Control-Allow-Origin`.
- [ ] Test en `tests/` que fuerza una excepción y valida el envelope.
- [ ] El skill `standard-api-responses` se actualiza para reflejar el nuevo handler.

## Referencias

- `.agents/rules/standard-response.md`
- Skill `standard-api-responses`
