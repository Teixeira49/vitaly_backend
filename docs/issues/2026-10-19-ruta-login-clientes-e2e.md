---
title: "[♻️ Deuda técnica] Migrar el login de clientes a /auth/client/login de forma coordinada (E2E)"
labels: [tech-debt, P3, api, schemas]
issue: 39
url: https://github.com/Teixeira49/vitaly_backend/issues/39
---

## Descripción
Al separar los portales de autenticación (issue #1), el login de clientes se mantuvo en `POST /api/v1/auth/login` para no romper el frontend, mientras que el de administración quedó en `POST /api/v1/auth/admin/login`. Las rutas resultan asimétricas y no siguen la propuesta original del issue #1 (`/auth/client/login`). Este cambio es global y debe hacerse de forma coordinada entre backend y frontend, con su propia tarea.

## Evidencia
- `app/api/v1/endpoints/auth.py:64` — el login de clientes se declara en `"/login"` del router `auth` (montado en `/auth`).
- `app/api/v1/endpoints/auth.py:99` — el login de administración se declara en `"/login"` del `admin_router` (montado en `/auth/admin`, `app/api/v1/router.py:7`).
- `app/schemas/user.py:10` — el esquema de clientes conserva el nombre legado `UserLogin`, mientras que el de administración es `AdminLoginCreate`.
- Frontend `src/services/auth/authService.ts:90` — consume `POST /api/v1/auth/login/` (con barra final, que hoy resuelve una redirección 307 hacia `/login`).

## Comportamiento actual vs esperado
- **Actual:** clientes en `/auth/login` y administración en `/auth/admin/login`; esquemas `UserLogin` / `AdminLoginCreate`.
- **Esperado:** rutas simétricas `/auth/client/login` y `/auth/admin/login`, y esquemas con sufijos estándar (`.agents/rules/schema-naming-convention.md`), con el frontend actualizado en el mismo ciclo (`.agents/rules/cross-repo-e2e.md`).

## Impacto
- ¿Expone datos médicos/PHR o PII? No.
- ¿Fuga entre escuelas (school_id)? No.
- Roles afectados: admin_escuela, doctor y representante (portal de clientes). Cambiar la ruta sin coordinar con el frontend rompe el login de los tres roles.

## Propuesta de solución
1. Backend: exponer `POST /auth/client/login` y mantener `POST /auth/login` como alias marcado `deprecated=True` en OpenAPI durante la transición.
2. Frontend (issue propio, Teixeira49/vitaly-care-for-families#23): apuntar `authService.login` a `/api/v1/auth/client/login` y tipar el claim `scope` del JWT.
3. Retirar el alias cuando el frontend desplegado ya no lo use.
4. Renombrar de forma oportunista `UserLogin` a un nombre con sufijo estándar, coordinando la interfaz TypeScript.

Decisión abierta: ¿cuánto tiempo se mantiene el alias `/auth/login` antes de retirarlo?

## Criterios de aceptación
- [ ] `POST /api/v1/auth/client/login` autentica a admin_escuela, doctor y representante y rechaza a admin_sistema con 403 (test en `tests/test_auth.py`).
- [ ] `POST /api/v1/auth/login` aparece como `deprecated` en `/docs` mientras exista.
- [ ] El frontend consume la nueva ruta y su login sigue funcionando (prueba manual por rol).
- [ ] Commits separados por repositorio; ningún commit mezcla backend y frontend.

## Referencias
- Issue #1 (separación de portales de autenticación).
- Teixeira49/vitaly-care-for-families#23 (consumo de la nueva ruta y tipado de `scope` en el frontend).
- `.agents/rules/cross-repo-e2e.md`, `.agents/rules/schema-naming-convention.md`, skill `vitaly-contracts-parity`.
