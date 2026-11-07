---
title: "[♻️ Deuda técnica] Cobertura de tests para Administración Global, Colegios y Años Académicos"
labels: [tech-debt, P2, api, services]
issue: 29
url: https://github.com/Teixeira49/vitaly_backend/issues/29
---

## Descripción

Los módulos de administración global del sistema (`admin.py`, `admin_school.py`), años académicos (`academic_year.py`) y catálogos (`catalogs.py`) concentran las operaciones reservadas exclusivamente al superadministrador (`admin_sistema`). Estos endpoints gestionan la supervisión transversal de la plataforma: aprobación individual y masiva de usuarios pendientes, activación/desactivación de cuentas, creación de colegios (con validaciones de RIF y unicidad territorial), registro global de aulas/estudiantes y el ciclo de vida de los años académicos (`academic_year`). Actualmente ninguno de estos endpoints cuenta con pruebas automatizadas en `tests/`, dejando desprotegida la lógica de privilegios del rol maestro y la gestión multi-escuela.

## Evidencia

Endpoints en `app/api/v1/endpoints/admin.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/admin.py:9` — `GET /users` (listado global de usuarios).
- `app/api/v1/endpoints/admin.py:23` — `GET /users/pending` (solicitudes pendientes con `isActive=False`).
- `app/api/v1/endpoints/admin.py:37` — `PATCH /users/approve` (aprobación individual de usuarios).
- `app/api/v1/endpoints/admin.py:50` — `PATCH /users/approve/bulk` (aprobación masiva).
- `app/api/v1/endpoints/admin.py:63` — `GET /users/{user_id}/details` (detalle completo con rol y metadatos).
- `app/api/v1/endpoints/admin.py:76` — `PATCH /users/{user_id}/toggle-active` (bloqueo/desbloqueo de usuarios con jerarquía de nivel).

Endpoints en `app/api/v1/endpoints/admin_school.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/admin_school.py:16` — `POST /` (creación de escuela con validación de RIF y nombre/estado).
- `app/api/v1/endpoints/admin_school.py:28` — `POST /classrooms` (creación de aula validando límites de niveles por categoría).
- `app/api/v1/endpoints/admin_school.py:45` — `POST /students` (registro global de alumnos validando edad y CI).
- Listados globales paginados de escuelas, aulas y estudiantes.

Endpoints en `app/api/v1/endpoints/academic_year.py` y `catalogs.py`:
- `app/api/v1/endpoints/academic_year.py:9` — `POST /` (creación de año escolar y cálculo de `is_current`).
- `app/api/v1/endpoints/academic_year.py:43` — `PATCH /sync-current` (sincronización de vigencia por fecha actual).
- `app/api/v1/endpoints/catalogs.py:10-45` — Catálogos públicos (`states`, `school_types`, `classroom_categories`, `system_status`).

Lógica de servicio en `app/services/admin_service.py`:
- `get_users`, `approve_user`, `approve_users_bulk`, `get_user_details`, `toggle_user_status`.
- `create_school`, `create_classroom`, `create_student`.

Ausencia de tests en el repositorio:
- El directorio `tests/` no contiene ninguna prueba para `admin.py`, `admin_school.py`, `academic_year.py` ni `catalogs.py`.

## Comportamiento actual vs esperado

- **Actual:** No existe validación automatizada que garantice que roles inferiores (`admin_escuela`, `doctor`, `representante`) no puedan acceder a endpoints de administración global (escalamiento de privilegios), ni que la lógica de unicidad de RIF y validaciones de nivel por categoría escolar funcionen predeciblemente.
- **Esperado:** Cobertura de pruebas unitarias y funcionales con `TestClient` que implemente las 5 leyes de `vitaly-feature-testing`:
  1. Envoltorio `APIResponse` en todos los endpoints (2xx y respuestas de error con `success is False`).
  2. RBAC estricto de `admin_sistema`: acceso exitoso con token de superadmin; respuesta `403` inmediata para `admin_escuela`, `doctor` o `representante`.
  3. Mocks deterministas sin red para tablas `school`, `user`, `academic_year`, `classroom` y `student`.
  4. Manejo de listas vacías (`200 + []`) en listados de usuarios pendientes o colegios; `404` ante IDs inexistentes.
  5. Validaciones de dominio (`422` o `400`): rechazo de fechas inconsistentes en año académico (`start_date >= end_date`), niveles inválidos para la categoría o RIF duplicado.

## Impacto

- **¿Expone datos médicos/PHR o PII?** Alto. El administrador del sistema tiene visibilidad global de todos los usuarios registrados y de todas las escuelas. Una falla de autorización permitiría a un usuario no autorizado ver detalles de cualquier colegio o usuario.
- **¿Fuga entre escuelas?** `admin_sistema` es el único rol con acceso cross-school legítimo; los tests deben blindar que este bypass sea exclusivo de su gate (`get_current_admin_sistema`).
- **Roles afectados:** `admin_sistema` (y protección contra suplantación por `admin_escuela`, `doctor`, `representante`).

## Propuesta de solución

Crear tres suites de prueba modulares en `tests/`:

1. `tests/test_admin_users.py`:
   - Pruebas para listado de usuarios y filtro de pendientes (`isActive=False`).
   - Pruebas de aprobación individual y en bloque (`bulk`), verificando transición a `isActive=True`.
   - Pruebas de toggle active y bloqueo de autodeshabilitación.
   - Pruebas de RBAC denegando acceso con `403` a cualquier rol que no sea `admin_sistema`.

2. `tests/test_admin_school_management.py`:
   - Pruebas de creación de escuela validando RIF único y nombre único por estado.
   - Pruebas de creación de aulas validando rangos de grado (Preescolar 1-3, Primaria 1-6, Bachillerato 1-5).
   - Pruebas de listados paginados globales.

3. `tests/test_academic_year_and_catalogs.py`:
   - Pruebas de creación de año escolar validando cálculo de `is_current` y rechazo de fechas invertidas.
   - Pruebas de sincronización de vigencia (`/sync-current`).
   - Pruebas de catálogos públicos verificando formato `APIResponse` y contenido estático.

## Criterios de aceptación

- [ ] `tests/test_admin_users.py` creado y pasando con `pytest`.
- [ ] `tests/test_admin_school_management.py` creado y pasando con `pytest`.
- [ ] `tests/test_academic_year_and_catalogs.py` creado y pasando con `pytest`.
- [ ] Se verifica que cualquier petición a endpoints de `admin.py` y `admin_school.py` con rol distinto a `admin_sistema` retorne `403`.
- [ ] Se verifica que la aprobación de usuarios actualice correctamente el estado y rechace usuarios ya aprobados o eliminados.
- [ ] Se verifica que la creación de colegios rechace RIF duplicados con error de validación/conflicto.
- [ ] Se verifica que años académicos con fechas inválidas retornen error con envoltura estándar.
- [ ] Todos los tests corren de forma determinista y offline con mocks de `supabase-py`.

## Referencias

- `.agents/rules/rbac-enforcement.md`
- `.agents/rules/standard-response.md`
- Skill `vitaly-feature-testing`
- Skill `vitaly-rbac`
