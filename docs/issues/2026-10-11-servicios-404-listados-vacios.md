---
title: "[🐛 Bug] Servicios lanzan 404 en listados vacíos en lugar de 200 con data=[]"
labels: [bug, P2, services]
issue: 15
url: https://github.com/Teixeira49/vitaly_backend/issues/15
---

## Descripción

Cinco métodos de listado paginado lanzan `HTTPException(404)` cuando la colección está vacía (`total == 0`). La regla del proyecto exige responder `200 OK` con `data=[]`. Otros listados del mismo código ya lo hacen bien (`return {"data": [], "total": 0, ...}`), así que el comportamiento es inconsistente entre endpoints.

## Evidencia

`admin_service.py` (rutas de `admin_sistema` en `/api/v1/admin/schools`):

- `app/services/admin_service.py:401-402` — `get_schools`: `if total == 0: raise HTTPException(status_code=404, detail="No hay escuelas registradas en el sistema.")`
- `app/services/admin_service.py:452-453` — `get_classrooms`: 404 "No hay salones de clase registrados en el sistema."
- `app/services/admin_service.py:522-523` — `get_students`: 404 "No hay estudiantes registrados en el sistema."
- Consumidos por `app/api/v1/endpoints/admin_school.py:121`, `:151`, `:181`.

`school_admin_service.py` (rutas de `admin_escuela` en `/api/v1/school-admin/classrooms`):

- `app/services/school_admin_service.py:323-327` — `get_academic_grades`: 404 "Esta escuela no tiene grados registrados para el año académico vigente."
- `app/services/school_admin_service.py:389-393` — `get_students_by_classroom`: 404 "El salón con ID {classroom_id} no tiene estudiantes registrados."
- Consumidos por `app/api/v1/endpoints/school_admin_classrooms.py:27` y el endpoint de `:36`.

Patrón correcto ya existente en el repo (referencia):

- `app/services/school_admin_service.py:917-918` (`get_medical_cases`), `:984-985` (`get_doctors`), `:1495-1496`, `:1652-1653`; `app/services/school_admin_event_service.py:186-187` (`get_events`) → `return {"data": [], "total": 0, "page": page, "size": size}`.

Reproducción: `grep -n -A2 "if total == 0" app/services/*.py`

## Comportamiento actual vs esperado

- **Actual:** `GET` de una colección vacía responde 404 con envelope de error.
- **Esperado:** `200 OK`, `success=true`, `data` con la lista vacía y `total=0` (`.agents/rules/empty-table-validation.md`, restricción 1).

## Impacto

- ¿Expone datos médicos/PHR o PII? No.
- ¿Fuga entre escuelas? No.
- Roles afectados: `admin_sistema` (escuelas, salones, estudiantes) y `admin_escuela` (grados del año vigente, estudiantes por salón). El frontend tiene que tratar 404 como "vacío" en unas pantallas y no en otras, y un 404 real (salón inexistente o de otra escuela, `school_admin_service.py:372`) se vuelve indistinguible de un salón sin estudiantes.

## Propuesta de solución

Reemplazar cada `raise HTTPException(404, ...)` sobre `total == 0` por `return {"data": [], "total": 0, "page": page, "size": size}`, igual que `get_events`. El endpoint puede ajustar el `message` ("No hay registros") sin cambiar el status.

Fuera de alcance: el 404 de `school_admin_service.py:305-309` ("No hay un año académico vigente configurado") es la verificación de un prerrequisito de catálogo (directiva 3 de la regla), no una colección vacía; se mantiene. También se mantiene el 404 de recurso inexistente en `get_students_by_classroom` (salón que no existe o no pertenece a la escuela).

## Criterios de aceptación

- [ ] Los 5 métodos devuelven `data=[]`, `total=0` con colección vacía.
- [ ] Los 5 endpoints responden 200 con `success=true` en ese caso.
- [ ] `GET /school-admin/classrooms/{id}/students` con un salón inexistente o de otra escuela sigue respondiendo 404/403.
- [ ] Tests "empty list → 200 + []" para cada endpoint (skill `vitaly-feature-testing`).
- [ ] Revisar con el frontend (`../vitaly-care-for-families`) que ninguna pantalla dependa del 404 para mostrar el estado vacío.

## Referencias

- `.agents/rules/empty-table-validation.md`
- `.agents/rules/standard-response.md` (directiva 3: listas vacías → `data=[]`)
- Skills `supabase-integration`, `vitaly-feature-testing`
