---
title: "[♻️ Deuda técnica] Cobertura de tests para Salud Escolar: Casos Médicos, Métricas y Doctores"
labels: [tech-debt, P1, api, services]
issue: 26
url: https://github.com/Teixeira49/vitaly_backend/issues/26
---

## Descripción

El módulo de salud escolar de la administración escolar (`school_admin_medical.py`) gestiona el personal médico (`/doctors`), los casos médicos de los alumnos (`/medical-cases`), las tendencias epidemiológicas y el historial de métricas corporales (`/students/{student_id}/metrics`). Al contener registros protegidos de salud (PHR) e información identificable de menores (PII), su aislamiento multi-tenancy (`school_id`) es crítico para el cumplimiento legal y de seguridad. Actualmente este módulo carece totalmente de pruebas automatizadas en `tests/`, dejando sin verificación de regresión el acceso a diagnósticos, búsquedas filtradas y gestión de facultativos.

## Evidencia

Endpoints en `app/api/v1/endpoints/school_admin_medical.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/school_admin_medical.py:15` — `GET /doctors` (médicos asignados al colegio).
- `app/api/v1/endpoints/school_admin_medical.py:45` — `GET /doctors/{doctor_id}` (detalle profesional y de usuario).
- `app/api/v1/endpoints/school_admin_medical.py:68` — `PATCH /doctors/{doctor_id}/suspend`.
- `app/api/v1/endpoints/school_admin_medical.py:87` — `PATCH /doctors/{doctor_id}/activate`.
- `app/api/v1/endpoints/school_admin_medical.py:110` — `GET /medical-cases` (casos médicos de alumnos de la escuela).
- `app/api/v1/endpoints/school_admin_medical.py:140` — `GET /medical-cases/search` (búsqueda con filtros de estado, tipo, fechas y texto).
- `app/api/v1/endpoints/school_admin_medical.py:193` — `GET /students/medical-cases/tendency` (agrupación temporal mensual/semanal).
- `app/api/v1/endpoints/school_admin_medical.py:213` — `GET /medical-cases/{case_id}` (detalle clínico con diagnóstico y padres).
- `app/api/v1/endpoints/school_admin_medical.py:233` — `GET /students/{student_id}/metrics` (historial de peso, talla e IMC).

Lógica de servicio en `app/services/school_admin_service.py`:
- `get_doctors`, `get_doctor_detail`, `suspend_doctor`, `reactivate_doctor`.
- `get_medical_cases`, `search_medical_cases`, `get_medical_cases_tendency`, `get_medical_case_detail`, `get_student_metrics_history`.

Ausencia de tests en el repositorio:
- `ls tests/test_school_admin*` no arroja ningún archivo de test para este módulo clínico. Las únicas pruebas existentes en `tests/` corresponden a perfiles de doctores individuales y fotos (`test_doctor_profile.py`, `test_profile_photo.py`).

## Comportamiento actual vs esperado

- **Actual:** No existe validación automatizada en CI (`pytest`) que asegure que un administrador escolar no pueda consultar historiales médicos, diagnósticos o doctores de otra institución educativa, ni que las respuestas mantengan el envelope `APIResponse` ante búsquedas complejas.
- **Esperado:** Cobertura de pruebas unitarias y de integración con `TestClient` que implemente las 5 leyes de `vitaly-feature-testing`:
  1. Envoltorio `APIResponse` en todas las respuestas (2xx con `data` y `message`, errores con `success is False`).
  2. Aislamiento estricto de PHR/PII por `school_id`: si un `case_id`, `doctor_id` o `student_id` pertenece a otra escuela, responder estrictamente con `403`.
  3. Mocks deterministas de `supabase-py` para simular tablas de casos médicos, métricas y relaciones escuela-doctor.
  4. Caso o doctor inexistente responde `404`; listados y búsquedas sin resultados devuelven `200` con `data=[]` o paginación vacía (nunca 404 ni 500).
  5. Matriz RBAC: denegar con `403` a roles no autorizados (ej. `representante` o `doctor`), y responder `401` ante tokens revocados o ausentes.

## Impacto

- **¿Expone datos médicos/PHR o PII?** Crítico. Este módulo maneja diagnósticos clínicos (`final_diagnosis`, `symptomatology`), tipos de casos médicos (alergias, lesiones, emergencias), historiales corporales/nutricionales (IMC) y datos personales de médicos y representantes.
- **¿Fuga entre escuelas (`school_id`)?** Riesgo de máxima severidad. Una fuga de información de salud entre instituciones violaría los principios fundamentales del producto y las normativas de protección de datos de menores.
- **Roles afectados:** `admin_escuela`.

## Propuesta de solución

Crear una suite de pruebas exhaustiva en `tests/test_school_admin_medical.py` que cubra:
1. **Gestión de Personal Médico:**
   - Listado paginado de doctores y detalle de doctor.
   - Activación y suspensión de médicos verificando pertenencia a la escuela.
   - Acceso a doctores de otra escuela denegado con `403`.
2. **Casos Médicos Escolares:**
   - Listado y búsqueda filtrada (`status`, `type_of_case`, rango de fechas).
   - Detalle de caso médico validando que el alumno asociado pertenezca a la escuela del administrador (`403` si es de otra escuela, `404` si no existe).
   - Tendencia temporal de casos (`monthly` y `weekly`).
3. **Métricas de Salud de Estudiantes:**
   - Historial de métricas corporales (peso, talla, IMC).
   - Retorno de mensaje adecuado cuando el estudiante no posee métricas registradas.
   - Bloqueo con `403` si el estudiante consultado pertenece a otro colegio.

## Criterios de aceptación

- [ ] `tests/test_school_admin_medical.py` creado y pasando con `pytest`.
- [ ] Se verifica que consultar o mutar un caso médico, doctor o métrica de otra escuela devuelva `403`.
- [ ] Se verifica que consultar un `case_id` o `doctor_id` inexistente devuelva `404` con envelope `APIResponse`.
- [ ] Se verifica que búsquedas sin coincidencias devuelvan `200` con lista vacía (nunca `404`).
- [ ] Se verifica que roles no autorizados reciban `403`.
- [ ] Se verifica que tokens ausentes o revocados reciban `401`.
- [ ] Todos los tests corren de forma determinista y offline con mocks de `supabase-py`.

## Referencias

- `.agents/rules/tenant-isolation.md`
- `.agents/rules/standard-response.md`
- `.agents/rules/empty-table-validation.md`
- Skill `vitaly-feature-testing`
- Skill `medical-domain` (rol del Medical Domain Guardian)
