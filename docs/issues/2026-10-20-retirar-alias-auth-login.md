---
title: "[♻️ Deuda técnica] Retirar el alias obsoleto POST /auth/login del portal de clientes"
labels: [tech-debt, P3, api]
issue: 43
url: https://github.com/Teixeira49/vitaly_backend/issues/43
---

## Descripción
El issue #39 (PR #42) movió el login de clientes a `POST /api/v1/auth/client/login` y dejó `POST /api/v1/auth/login` como alias obsoleto para no romper el frontend durante la transición. Cuando el frontend que consume la nueva ruta (Teixeira49/vitaly-care-for-families#28) esté en producción, el alias deja de tener consumidores y debe retirarse para no mantener dos rutas públicas de login.

## Evidencia
Referencias en la rama `refactor/GH-39` (PR #42):
- `app/api/v1/endpoints/auth.py:75` — `deprecated=True` en el decorador del alias.
- `app/api/v1/endpoints/auth.py:77` — `def login(user_in: ClientLoginCreate)`, que delega en `client_login`.
- `app/core/openapi.py:6` — la descripción de la sección `auth` menciona el alias obsoleto.
- `tests/test_auth.py:887` — `TestDeprecatedClientLoginAlias` cubre el alias.
- `.agents/rules/rbac-enforcement.md` y `.agents/skills/vitaly-rbac/SKILL.md` — citan el alias como pendiente de retirar.

## Comportamiento actual vs esperado
- **Actual:** dos rutas públicas autentican a los clientes: `/auth/client/login` y el alias `/auth/login`.
- **Esperado:** solo `/auth/client/login` (simétrica con `/auth/admin/login`); `/auth/login` responde 404.

## Impacto
- ¿Expone datos médicos/PHR o PII? No.
- ¿Fuga entre escuelas (school_id)? No.
- Roles afectados: admin_escuela, doctor y representante. Retirar el alias antes de que el frontend #28 esté en producción rompe el login de los tres roles; una vez desplegado, el cambio no tiene efecto visible.

## Propuesta de solución
1. Eliminar el endpoint `login` (alias) de `app/api/v1/endpoints/auth.py`.
2. Actualizar la descripción de la sección `auth` en `app/core/openapi.py`.
3. Sustituir `TestDeprecatedClientLoginAlias` por un test que verifique que `POST /api/v1/auth/login` responde 404.
4. Quitar la mención del alias en la regla RBAC y en la skill `vitaly-rbac`.

Decisión abierta: ¿se retira en cuanto el frontend #28 llega a producción, o se mantiene un periodo de gracia (por ejemplo, un ciclo de despliegue) por si hay clientes con una versión antigua del frontend en caché?

## Criterios de aceptación
- [ ] Antes de fusionar: el frontend #28 está desplegado en producción y no hay tráfico a `/api/v1/auth/login` en los logs.
- [ ] `POST /api/v1/auth/login` responde 404 (test en `tests/test_auth.py`).
- [ ] `/docs` ya no muestra el alias; `POST /api/v1/auth/client/login` sigue funcionando.
- [ ] La regla RBAC y la skill `vitaly-rbac` no mencionan el alias.

## Referencias
- Issue #39 y PR #42 (migración a `/auth/client/login`).
- Teixeira49/vitaly-care-for-families#23 y PR #28 (consumo de la nueva ruta en el frontend).
- `.agents/rules/cross-repo-e2e.md`, skill `vitaly-rbac`.
