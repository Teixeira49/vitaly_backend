---
title: "[🔧 Chore] Configurar ruff y reenviar header WWW-Authenticate en el handler de HTTPException"
labels: [chore, P3, api]
issue: 18
url: https://github.com/Teixeira49/vitaly_backend/issues/18
---

## Descripción

Dos ajustes menores de higiene:

1. Las reglas del proyecto usan `ruff check` como comando de verificación, pero `ruff` no está en las dependencias ni existe configuración, así que el comando no se puede ejecutar de forma reproducible.
2. El handler global de `HTTPException` reconstruye la respuesta sin copiar `exc.headers`, por lo que el header `WWW-Authenticate: Bearer` que añaden los 401 de autenticación se pierde.

## Evidencia

ruff:

- `.agents/rules/schema-naming-convention.md:73` — "Comando de Verificación: `ruff check app/schemas/`".
- `requirements-dev.txt` — solo contiene `-r requirements.txt` y `pytest>=8.0.0`.
- No existen `pyproject.toml`, `ruff.toml` ni `.ruff.toml` en la raíz del repositorio.

WWW-Authenticate:

- `app/api/deps.py:22` y `:30` — los 401 se lanzan con `headers={"WWW-Authenticate": "Bearer"}`.
- `app/core/exceptions.py:14-18` — `http_exception_handler` devuelve `JSONResponse(status_code=exc.status_code, content=...)` sin `headers=exc.headers`.
- Reproducción: `curl -i -H "Authorization: Bearer invalido" http://localhost:8000/api/v1/auth/logout` → 401 sin header `WWW-Authenticate`.

## Comportamiento actual vs esperado

- **Actual:** `ruff check` falla con "command not found" en un entorno limpio; los 401 no incluyen `WWW-Authenticate`.
- **Esperado:** `pip install -r requirements-dev.txt && ruff check app/` funciona con una configuración versionada; los 401 incluyen `WWW-Authenticate: Bearer` (RFC 6750 / RFC 9110), igual que el comportamiento por defecto de FastAPI.

## Impacto

- ¿Expone datos médicos/PHR o PII? No.
- ¿Fuga entre escuelas? No.
- Roles afectados: ninguno funcionalmente; afecta a herramientas de desarrollo y a clientes HTTP estándar que dependen del header para reautenticar.

## Propuesta de solución

1. Añadir `ruff` (versión fijada) a `requirements-dev.txt` y una configuración mínima (`ruff.toml` o `pyproject.toml` con `[tool.ruff]`: `target-version`, `line-length`, reglas base `E`, `F`, `I`). Valorar si el primer paso es solo reportar, para no bloquear por el código existente.
2. En `app/core/exceptions.py`, pasar `headers=getattr(exc, "headers", None)` al `JSONResponse` de `http_exception_handler`.

## Criterios de aceptación

- [ ] `pip install -r requirements-dev.txt` instala `ruff`.
- [ ] Existe configuración de ruff versionada y `ruff check app/schemas/` se ejecuta (aunque reporte hallazgos existentes).
- [ ] Un 401 de `get_current_user_token` incluye el header `WWW-Authenticate: Bearer`.
- [ ] Test en `tests/` que valida el header en un 401.

## Referencias

- `.agents/rules/schema-naming-convention.md`
- `.agents/rules/standard-response.md`
- Skill `standard-api-responses`
