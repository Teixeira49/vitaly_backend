---
title: "[♻️ Deuda técnica] Cobertura de tests para School Admin: Estudiantes y Aulas"
labels: [tech-debt, P1, api, services]
issue: 25
url: https://github.com/Teixeira49/vitaly_backend/issues/25
---

## Descripción

Los módulos de gestión de estudiantes (`school_admin_students.py`) y salones/aulas (`school_admin_classrooms.py`) constituyen el núcleo operativo del colegio en el backend de Vitaly. Estos endpoints manejan información personal de alumnos (PII), asignaciones de grado y estado nutricional base, dependiendo críticamente del aislamiento multi-tenancy por escuela (`school_id`). Actualmente carecen por completo de suites de pruebas automatizadas en `tests/`, dejando desprotegidos contra regresiones los flujos de consulta de alumnos por aula, detalles de estudiantes, actualización de perfiles y activación/desactivación.

## Evidencia

Endpoints en `app/api/v1/endpoints/school_admin_students.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/school_admin_students.py:21` — `GET /students/{student_id}` (detalle completo de alumno y representante).
- `app/api/v1/endpoints/school_admin_students.py:46` — `GET /representatives/{parent_id}` (hijos vinculados a un representante).
- `app/api/v1/endpoints/school_admin_students.py:80` — `PUT /students/{student_id}` (actualización de perfil y representante).
- `app/api/v1/endpoints/school_admin_students.py:114` — `GET /search/representatives` (búsqueda paginada).
- `app/api/v1/endpoints/school_admin_students.py:149` — `PATCH /students/{student_id}/activate`.
- `app/api/v1/endpoints/school_admin_students.py:174` — `PATCH /students/{student_id}/deactivate`.

Endpoints en `app/api/v1/endpoints/school_admin_classrooms.py` sin pruebas automatizadas:
- `app/api/v1/endpoints/school_admin_classrooms.py:14` — `GET /` (listado paginado de salones del año vigente).
- `app/api/v1/endpoints/school_admin_classrooms.py:35` — `GET /{classroom_id}/students` (estudiantes por aula).
- `app/api/v1/endpoints/school_admin_classrooms.py:62` — `GET /categories-summary`.
- `app/api/v1/endpoints/school_admin_classrooms.py:88` — `GET /categories-available`.
- `app/api/v1/endpoints/school_admin_classrooms.py:111` — `GET /categories/{category_id}/levels/{level}/sections`.

Lógica de servicio en `app/services/school_admin_service.py`:
- `app/services/school_admin_service.py:360` — `def get_students_by_classroom(...)`.
- `app/services/school_admin_service.py:469` — `def get_student_detail(...)`.

Inexistencia de tests en el repositorio:
- Ejecución de `ls tests/test_school_admin*` confirma que no existe ninguna suite de pruebas para estos módulos; el directorio `tests/` únicamente contiene `test_doctor_profile.py` y `test_profile_photo.py`.
- Existe una plantilla de referencia ejecutable ya implementada para `GET /{classroom_id}/students` en `.agents/skills/vitaly-feature-testing/examples/template_feature_test.py:1-247`.

## Comportamiento actual vs esperado

- **Actual:** Modificaciones o refactorizaciones en `school_admin_service.py` o en los endpoints de estudiantes y aulas pueden romper el aislamiento por `school_id`, la envoltura `APIResponse` o el manejo de errores sin ser detectados por CI (`pytest`).
- **Esperado:** Cobertura de pruebas unitarias y funcionales con `TestClient` que implemente las 5 leyes de `vitaly-feature-testing`:
  1. Envoltorio `APIResponse` (2xx y respuestas de error con `success is False`).
  2. Multi-tenancy estricto: `school_id` derivado en servidor desde `sub`, y respuesta `403` si el aula o estudiante pertenece a otra escuela.
  3. Mocks deterministas de `supabase-py` sin llamadas de red externas.
  4. Recurso individual inexistente devuelve `404`; listados sin filas devuelven `200` con `data=[]` (nunca 404 ni 500).
  5. Matriz RBAC: rol no autorizado → `403`, token revocado/ausente → `401`, payload inválido → `422`.

## Impacto

- **¿Expone datos médicos/PHR o PII?** Sí. `GET /students/{student_id}` expone PII sensible (nombre, cédula, fecha de nacimiento, datos del padre) y métricas de salud (`health_info`: peso, talla, IMC, estado nutricional).
- **¿Fuga entre escuelas (`school_id`)?** Alto riesgo potencial. Si la validación de `school_id` falla en el servicio o endpoint, un administrador escolar podría consultar o modificar estudiantes de otros colegios.
- **Roles afectados:** `admin_escuela`.

## Propuesta de solución

Implementar dos suites de prueba organizadas bajo `tests/`:

1. `tests/test_school_admin_classrooms.py`:
   - Adaptar `template_feature_test.py` para cubrir exhaustivamente salones vigentes, categorías, secciones y estudiantes de un aula.
   - Probar casos de salón perteneciente a otra escuela (`403`) y salón inexistente (`404`).

2. `tests/test_school_admin_students.py`:
   - Probar detalle de estudiante, detalle de representante e hijos vinculados.
   - Probar actualización de perfil de estudiante (`PUT`) con y sin reasignación de representante.
   - Probar activación y desactivación (`PATCH`).
   - Probar que intentar modificar o consultar un estudiante de otro colegio devuelva `403`.

## Criterios de aceptación

- [ ] `tests/test_school_admin_classrooms.py` creado y pasando con `pytest`.
- [ ] `tests/test_school_admin_students.py` creado y pasando con `pytest`.
- [ ] Se verifica con aserciones que consultar un estudiante o aula de otra escuela retorne `403`.
- [ ] Se verifica que consultar un estudiante o aula inexistente retorne `404` con envelope `APIResponse`.
- [ ] Se verifica que un salón sin alumnos retorne `200` con lista vacía (nunca `404`).
- [ ] Se verifica que un token con rol diferente (ej. `doctor` o `representante`) retorne `403`.
- [ ] Se verifica que tokens ausentes o revocados retornen `401`.
- [ ] Todos los tests corren de forma determinista y offline con mocks de `supabase-py`.

## Referencias

- `.agents/rules/tenant-isolation.md`
- `.agents/rules/standard-response.md`
- `.agents/rules/empty-table-validation.md`
- Skill `vitaly-feature-testing`
- Plantilla de referencia `.agents/skills/vitaly-feature-testing/examples/template_feature_test.py`
