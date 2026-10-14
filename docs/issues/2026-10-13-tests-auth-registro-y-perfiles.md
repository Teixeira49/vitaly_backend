---
title: "[♻️ Deuda técnica] Cobertura de tests para Autenticación, Registro por Rol y Vinculación Familiar"
labels: [tech-debt, P2, api, services]
issue: 28
url: https://github.com/Teixeira49/vitaly_backend/issues/28
---

## Descripción

El módulo de autenticación (`auth.py`, `auth_service.py`) y los endpoints de representantes familiares (`parent.py`, `parent_service.py`) controlan la puerta de entrada a la plataforma. Administran el registro diferenciado por los cuatro roles del sistema (`admin_sistema`, `admin_escuela`, `doctor`, `representante`), el ciclo de aprobación/activación (`is_active=False` inicial), la emisión de JWTs con los claims estrictos requeridos por la arquitectura (sin claim `school_id`), la revocación de tokens en `logout` y la vinculación de hijos a representantes (`/link-students`). Actualmente no existe ninguna prueba automatizada en `tests/` que valide estos flujos críticos de seguridad y control de acceso.

## Evidencia

Endpoints en `app/api/v1/endpoints/auth.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/auth.py:10` — `POST /register-system-admin`.
- `app/api/v1/endpoints/auth.py:18` — `POST /register-school-admin` (requiere `school_id` y `administrative_position`).
- `app/api/v1/endpoints/auth.py:27` — `POST /register-doctor` (requiere `doc_license_number` y `especially`).
- `app/api/v1/endpoints/auth.py:36` — `POST /register-parent` (requiere `identity_number` y `type_representative`).
- `app/api/v1/endpoints/auth.py:45` — `POST /login` (emisión de Bearer token `APIResponse[Token]`).
- `app/api/v1/endpoints/auth.py:53` — `POST /logout` (revocación de token en memoria/lista).

Endpoint en `app/api/v1/endpoints/parent.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/parent.py:15` — `POST /link-students` (vinculación automática de alumnos por cédula).

Lógica de servicio en `app/services/auth_service.py`:
- Métodos de registro por rol (`register_system_admin`, `register_school_admin`, `register_doctor`, `register_parent`).
- `authenticate_user`: rechazo de usuarios inactivos (`is_active=False`) y contraseñas inválidas.
- `revoke_token` e `is_token_revoked`: lista de revocación para denegar accesos tras `logout`.

Ausencia de tests en el repositorio:
- El directorio `tests/` carece por completo de pruebas para `auth.py` o `parent.py`.

## Comportamiento actual vs esperado

- **Actual:** Regresiones en la generación de tokens JWT (ej. omisión de claims requeridos por los gates de roles, o inclusión indebida de `school_id`), fallos en el hashing de contraseñas o brechas en la revocación de tokens no son detectados automáticamente.
- **Esperado:** Cobertura de pruebas con `TestClient` y mocks de `supabase-py` que verifiquen:
  1. Registro exitoso de los cuatro roles, validando que queden en estado inactivo (`is_active=False`) a la espera de verificación.
  2. Login exitoso que retorne `access_token` y `token_type: bearer` en envelope `APIResponse`.
  3. Contenido del payload JWT: presencia obligatoria de `sub` (como string), `email`, `role`, `name`, `gender`, y ausencia garantizada de `school_id` (el aislamiento se resuelve server-side).
  4. Rechazo de login (`401` o `400` según lógica) ante credenciales inválidas o usuario inactivo.
  5. Flujo de `logout`: verificación de que el token quede revocado y una petición subsecuente sea rechazada con `401`.
  6. Vinculación de estudiantes (`POST /link-students`): asociación correcta en `student_representative` previniendo duplicados, restringida a rol `representante`.

## Impacto

- **¿Expone datos médicos/PHR o PII?** Alto. La autenticación es la primera barrera defensiva. Un fallo en la validación de tokens o en los roles del payload puede permitir acceso indebido a información clínica o de alumnos.
- **¿Fuga entre escuelas?** Si la emisión del token o la validación del rol falla, un usuario podría operar con privilegios no asignados.
- **Roles afectados:** Todos los roles (`admin_sistema`, `admin_escuela`, `doctor`, `representante`).

## Propuesta de solución

Crear dos suites de prueba modulares en `tests/`:

1. `tests/test_auth.py`:
   - Pruebas de registro para cada uno de los 4 roles validando esquemas y estado inicial.
   - Pruebas de login exitoso y decodificación de claims del token emitido.
   - Pruebas de rechazo de login ante credenciales erróneas o cuenta inactiva.
   - Pruebas de logout e invalidación de token con reintento fallido (`401`).

2. `tests/test_parent.py`:
   - Pruebas para `POST /link-students` con coincidencias de cédula en `authorization_number`.
   - Pruebas para representantes sin cédula o sin alumnos autorizados.
   - Prueba de denegación con `403` si se invoca con rol distinto a `representante`.

## Criterios de aceptación

- [ ] `tests/test_auth.py` creado y pasando con `pytest`.
- [ ] `tests/test_parent.py` creado y pasando con `pytest`.
- [ ] Se verifica que el token emitido en login contenga los claims exactos (`sub`, `role`, `email`) y no contenga `school_id`.
- [ ] Se verifica que usuarios inactivos no puedan iniciar sesión.
- [ ] Se verifica que tras invocar `logout`, el token revocado sea rechazado con `401`.
- [ ] Se verifica que `POST /link-students` rechace tokens sin rol `representante` con `403`.
- [ ] Todos los tests corren de forma determinista y offline con mocks de `supabase-py`.

## Referencias

- `.agents/rules/rbac-enforcement.md`
- Skill `vitaly-rbac`
- Skill `vitaly-feature-testing`
- `app/core/security.py`
