# [🧹 Refactor: GH-27] - Cobertura de tests para Eventos Escolares, Perfil y Métricas de Escuela

## Descripción

Este pull request implementa la suite completa de pruebas unitarias y de integración para los módulos de Eventos Escolares (`school_admin_events.py`), Perfil del Administrador y Dashboard Métrico de Estudiantes (`school_admin.py`), junto con sus servicios asociados (`school_admin_event_service.py` y `school_admin_service.py`).

Se añaden 48 casos de prueba automatizados siguiendo rigurosamente las 5 leyes de `vitaly-feature-testing`:
1. **Envoltorio APIResponse:** Verificación sistemática del envoltorio uniforme (`success`, `data`, `message`) en todas las respuestas exitosas y de error.
2. **Aislamiento Multi-Tenancy Estricto:** Verificación de aislamiento por `school_id` resuelto en el servidor a partir del token JWT. Bloqueo con `403 Forbidden` ante intentos de consulta, actualización o cancelación de eventos pertenecientes a otras escuelas, y rechazo con `400 Bad Request` si se intentan asociar salones o doctores foráneos a un evento. Verificación de `403 Forbidden` al acceder al historial médico de un estudiante de otra institución.
3. **Mocks Deterministas:** Simulación determinista del cliente `supabase-py` para las tablas `event`, `event_participation`, `classroom`, `classroom_registration`, `doctor_to_school`, `school_admin`, `school`, `user`, `student`, `medical_case` y `student_metrics`.
4. **Semántica REST:** Comprobación de retorno `200 OK` con listas vacías (`data=[]`) en paginaciones o búsquedas sin resultados (nunca 404 ni 500), y `404 Not Found` ante eventos, perfiles o estudiantes inexistentes.
5. **Matriz RBAC y Validación:** Verificación de rechazo `401 Unauthorized` ante tokens ausentes, malformados o revocados, `403 Forbidden` ante roles no autorizados (`doctor`, `representante`) y `422 Unprocessable Entity` ante payloads inválidos.

Closes #27

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

- [x] **POST /api/v1/school-admin/events/** (rol: `admin_escuela`) → `201 Created` con creación de evento y participaciones de aulas/doctores. Rechazo `400` ante aulas foráneas o doctores no asignados al colegio.
- [x] **GET /api/v1/school-admin/events/** (rol: `admin_escuela`) → `200 OK` con listado paginado de eventos de la escuela. Lista vacía retorna `200 OK` con `data=[]`.
- [x] **GET /api/v1/school-admin/events/by-month** (rol: `admin_escuela`) → `200 OK` con eventos del mes y año solicitados.
- [x] **GET /api/v1/school-admin/events/{event_id}** (rol: `admin_escuela`) → `200 OK` con detalle del evento. Evento de otra escuela retorna `403 Forbidden`. Evento inexistente retorna `404 Not Found`.
- [x] **PATCH /api/v1/school-admin/events/{event_id}/cancel** (rol: `admin_escuela`) → `200 OK` cancelando en cascada el evento y sus participaciones. Evento de otra escuela retorna `403 Forbidden`.
- [x] **PUT /api/v1/school-admin/events/{event_id}** (rol: `admin_escuela`) → `200 OK` actualizando metadatos. Evento de otra escuela retorna `403 Forbidden`.
- [x] **GET /api/v1/school-admin/profile** (rol: `admin_escuela`) → `200 OK` con datos del administrador y su escuela.
- [x] **PUT /api/v1/school-admin/profile** (rol: `admin_escuela`) → `200 OK` actualizando datos del perfil.
- [x] **GET /api/v1/school-admin/students/resume** (rol: `admin_escuela`) → `200 OK` con conteos métricos poblacionales (total, sobrepeso, desnutridos, óptimos, activos). Validación de jerarquía de filtros (sección requiere grado y categoría; grado requiere categoría) con `400 Bad Request`.
- [x] **GET /api/v1/school-admin/students/{student_id}/medical-history** (rol: `admin_escuela`) → `200 OK` con historial médico. Estudiante foráneo retorna `403 Forbidden`. Estudiante inexistente retorna `404 Not Found`.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest` (178 passed)

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
