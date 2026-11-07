---
title: "[♻️ Deuda técnica] Cobertura de tests para Eventos Escolares, Perfil y Métricas de Escuela"
labels: [tech-debt, P2, api, services]
issue: 27
url: https://github.com/Teixeira49/vitaly_backend/issues/27
---

## Descripción

El módulo de eventos (`school_admin_events.py`) y los endpoints de administración institucional (`school_admin.py`) gestionan la agenda escolar (jornadas de salud, vacunación, eventos), el perfil del administrador y el panel métrico consolidado de salud de la escuela (`/students/resume`). Estos flujos articulan la relación entre salones, doctores y eventos mediante participaciones, y calculan indicadores poblacionales de nutrición. Actualmente no cuentan con suites de pruebas automatizadas en `tests/` para verificar el ciclo de vida de los eventos, el cálculo del dashboard o el aislamiento por escuela (`school_id`).

## Evidencia

Endpoints en `app/api/v1/endpoints/school_admin_events.py` sin cobertura de pruebas:
- `app/api/v1/endpoints/school_admin_events.py:15` — `POST /` (creación de evento con asignación de salones y doctores).
- `app/api/v1/endpoints/school_admin_events.py:43` — `GET /` (listado paginado de eventos activos).
- `app/api/v1/endpoints/school_admin_events.py:66` — `GET /by-month` (eventos filtrados por año y mes).
- `app/api/v1/endpoints/school_admin_events.py:89` — `GET /{event_id}` (detalle con salones y doctores participantes).
- `app/api/v1/endpoints/school_admin_events.py:117` — `PATCH /{event_id}/cancel` (cancelación en cascada de evento y participaciones).
- `app/api/v1/endpoints/school_admin_events.py:139` — `PUT /{event_id}` (actualización de metadatos de evento).

Endpoints en `app/api/v1/endpoints/school_admin.py` sin cobertura de pruebas:
- `app/api/v1/endpoints/school_admin.py:16` — `GET /profile` (perfil del administrador y datos del colegio).
- `app/api/v1/endpoints/school_admin.py:33` — `PUT /profile` (actualización de datos personales).
- `app/api/v1/endpoints/school_admin.py:131` — `GET /students/resume` (dashboard métrico: total, sobrepeso, desnutridos, activos y óptimos con filtros jerárquicos de categoría/grado/sección).
- `app/api/v1/endpoints/school_admin.py:170` — `GET /students/{student_id}/medical-history` (historial médico del estudiante).

Servicios involucrados:
- `app/services/school_admin_event_service.py:1-420` — `school_admin_event_service` (gestión de `event` y `event_participation`).
- `app/services/school_admin_service.py` — métodos `get_my_profile`, `update_my_profile`, `get_students_resume`, `get_student_medical_history`.

Estado en el directorio `tests/`:
- `tests/test_profile_photo.py` únicamente prueba la subida de fotos; no existe ninguna prueba para eventos, perfiles ni métricas consolidadas del colegio.

## Comportamiento actual vs esperado

- **Actual:** Modificaciones en `school_admin_event_service.py` o en la agregación de métricas de `get_students_resume` pueden romper la lógica de fechas, cancelar eventos de otras escuelas o corromper el cálculo de sobrepeso/desnutrición sin alertas en CI.
- **Esperado:** Cobertura de pruebas automatizadas con `TestClient` que implemente las 5 leyes de `vitaly-feature-testing`:
  1. Envoltorio `APIResponse` en todos los endpoints (200/201 con `data` y `message`, errores con `success is False`).
  2. Multi-tenancy estricto: denegar con `403` si se intenta consultar, actualizar o cancelar un evento perteneciente a otra escuela, o si los salones/doctores asignados no pertenecen a la escuela del administrador.
  3. Mocks deterministas sin red para tablas `event`, `event_participation`, `classroom`, `user` y `student`.
  4. Lista vacía `200 + []` cuando no hay eventos en el mes o página; `404` si el `event_id` no existe.
  5. Matriz RBAC: denegar con `403` ante roles no autorizados (`doctor`, `representante`) y `401` ante tokens revocados.

## Impacto

- **¿Expone datos médicos/PHR o PII?** Moderado a alto. `GET /students/{student_id}/medical-history` expone el historial clínico del alumno; `GET /students/resume` expone agregaciones de salud; los eventos vinculan doctores y alumnos.
- **¿Fuga entre escuelas (`school_id`)?** Riesgo de fuga organizativa y de agenda. Un administrador no debe poder ver ni cancelar eventos de otras escuelas, ni agregar aulas de otra institución a sus eventos.
- **Roles afectados:** `admin_escuela`.

## Propuesta de solución

Crear dos suites de prueba modulares en `tests/`:

1. `tests/test_school_admin_events.py`:
   - Crear evento con validación de asignación de salones y doctores de la misma escuela.
   - Probar listado paginado y listado por mes con rangos de fecha válidos.
   - Probar detalle de evento (`GET /{id}`) y bloqueo de eventos cancelados.
   - Probar cancelación (`PATCH /{id}/cancel`) y actualización (`PUT /{id}`).
   - Probar intento de interactuar con evento de otra escuela (`403`).

2. `tests/test_school_admin_profile_and_dashboard.py`:
   - Probar `GET /profile` y `PUT /profile`.
   - Probar `GET /students/resume` con y sin filtros jerárquicos (categoría, grado, sección), verificando las fórmulas de métricas (sobrepeso, desnutridos, óptimos).
   - Probar `GET /students/{student_id}/medical-history` verificando pertenencia del alumno a la escuela (`403` si es foráneo).

## Criterios de aceptación

- [ ] `tests/test_school_admin_events.py` creado y pasando con `pytest`.
- [ ] `tests/test_school_admin_profile_and_dashboard.py` creado y pasando con `pytest`.
- [ ] Se verifica que consultar o mutar eventos de otra escuela retorne `403`.
- [ ] Se verifica que intentar crear un evento con salones o doctores de otra escuela sea rechazado con `403`.
- [ ] Se verifica que consultar un `event_id` inexistente retorne `404` con envelope `APIResponse`.
- [ ] Se verifica que filtros sin eventos devuelvan `200` con lista vacía.
- [ ] Se verifica que el dashboard métrico retorne conteos consistentes y filtrados por `school_id`.
- [ ] Se verifica que roles no autorizados reciban `403` y tokens inválidos reciban `401`.
- [ ] Todos los tests corren de forma determinista y offline con mocks de `supabase-py`.

## Referencias

- `.agents/rules/tenant-isolation.md`
- `.agents/rules/standard-response.md`
- `.agents/rules/empty-table-validation.md`
- Skill `vitaly-feature-testing`
- Skill `vitaly-rbac`
