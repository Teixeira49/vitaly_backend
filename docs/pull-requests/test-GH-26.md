# [🧹 Refactor: GH-26] - Cobertura de tests para Salud Escolar: Casos Médicos, Métricas y Doctores

## Descripción

Este pull request implementa la suite completa de pruebas unitarias y de integración para el módulo clínico de administración escolar (`school_admin_medical.py`) y sus métodos de servicio asociados en `school_admin_service.py`.

Se añaden 35 casos de prueba automatizados siguiendo rigurosamente las 5 leyes de `vitaly-feature-testing`:
1. **Envoltorio APIResponse:** Verificación de envoltura estándar (`success`, `data`, `message`) en todas las respuestas exitosas y de error.
2. **Aislamiento Multi-Tenancy de Salud (PHR/PII):** Verificación estricta de que la consulta y mutación de casos médicos, métricas de alumnos y doctores vinculados filtre obligatoriamente por el `school_id` resuelto en el servidor, retornando `403 Forbidden` ante intentos de acceso a recursos de otras instituciones educativas.
3. **Mocks Deterministas:** Simulación exhaustiva del cliente `supabase-py` para las tablas `doctor_to_school`, `doctor`, `medical_case`, `student_metrics`, `user_phones`, `classroom` y `classroom_registration`.
4. **Semántica REST:** Verificación de retorno `200 OK` con listas vacías en búsquedas y listados sin resultados (nunca 404 ni 500), y `404 Not Found` ante médicos o casos inexistentes.
5. **Matriz RBAC y Validación:** Comprobación de rechazo `401` ante tokens ausentes/malformados/revocados, `403` ante roles no autorizados (`representante`, `doctor`) y `422` ante parámetros o formatos de fecha inválidos.

Closes #26

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [x] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Se han ejecutado las suites de pruebas automatizadas con `pytest` y validado la sintaxis y estilo con `ruff`.

- [x] **GET /api/v1/school-admin/doctors** (rol: `admin_escuela`) → `200 OK` con lista de médicos de la escuela, prefijo (`Dr.`/`Dra.`), años de experiencia y paginación. Lista vacía retorna `200 OK` con `data=[]`.
- [x] **GET /api/v1/school-admin/doctors/{doctor_id}** (rol: `admin_escuela`) → `200 OK` con detalle profesional y teléfonos. Doctor no vinculado a la escuela retorna `403 Forbidden`. Doctor inexistente retorna `404 Not Found`.
- [x] **PATCH /api/v1/school-admin/doctors/{doctor_id}/suspend** (rol: `admin_escuela`) → `200 OK` cambiando estado a suspendido (`status=1`). Doctor no vinculado retorna `404 Not Found`.
- [x] **PATCH /api/v1/school-admin/doctors/{doctor_id}/activate** (rol: `admin_escuela`) → `200 OK` reactivando estado a activo (`status=2`). Doctor no vinculado retorna `404 Not Found`.
- [x] **GET /api/v1/school-admin/medical-cases** (rol: `admin_escuela`) → `200 OK` con casos médicos de los alumnos de la escuela. Filtro `current_year_only` acota por año académico vigente.
- [x] **GET /api/v1/school-admin/medical-cases/search** (rol: `admin_escuela`) → `200 OK` con filtros combinados (`status`, `type_of_case`, `q`, fechas). Sin coincidencias retorna `data=[]`.
- [x] **GET /api/v1/school-admin/students/medical-cases/tendency** (rol: `admin_escuela`) → `200 OK` con métricas de tendencia en modo mensual y semanal.
- [x] **GET /api/v1/school-admin/medical-cases/{case_id}** (rol: `admin_escuela`) → `200 OK` con detalle clínico, estudiante, representantes y doctor. Estudiante de otra escuela retorna `403 Forbidden`.
- [x] **GET /api/v1/school-admin/students/{student_id}/metrics** (rol: `admin_escuela`) → `200 OK` con series temporales de peso, altura e IMC. Estudiante de otra escuela retorna `403 Forbidden`. Sin métricas retorna `200 OK` con `data=None` y mensaje descriptivo.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest` (130 passed)

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción *(no aplica)*
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción *(no aplica)*
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
