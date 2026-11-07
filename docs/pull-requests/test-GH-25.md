# [🧹 Refactor: GH-25] - Cobertura de tests para School Admin: Estudiantes y Aulas

## Descripción

Este pull request implementa la suite completa de pruebas unitarias y de integración para los módulos de administración escolar: Estudiantes (`school_admin_students.py`) y Salones (`school_admin_classrooms.py`), junto con la lógica de servicio asociada en `school_admin_service.py`.

Se añaden 57 nuevos casos de prueba automatizados siguiendo rigurosamente las 5 leyes de `vitaly-feature-testing`:
1. **Envoltorio APIResponse:** Verificación de estructura unificada (`success`, `data`, `message`, `meta`) tanto en respuestas exitosas como en manejo de excepciones.
2. **Multi-tenancy Silencioso:** Validación estricta de aislamiento de escuela mediante resolución de `school_id` en servidor y aserción de `403 Forbidden` ante intentos de acceso o mutación sobre recursos de colegios ajenos.
3. **Mocks Deterministas:** Simulación exhaustiva del cliente `supabase-py` sin llamadas de red externas.
4. **Semántica REST:** Verificación de `404 Not Found` ante recursos individuales inexistentes vs. `200 OK` con listas vacías en colecciones.
5. **Matriz RBAC y Validación:** Comprobación de rechazo `401` ante tokens ausentes/malformados/revocados, `403` ante roles no autorizados (ej. `doctor`, `representante`) y `422` ante parámetros o payloads no conformes.

Closes #25

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

- [x] **GET /api/v1/school-admin/classrooms/** (rol: `admin_escuela`) → `200 OK` con lista de salones del año vigente y metadatos de paginación.
- [x] **GET /api/v1/school-admin/classrooms/{classroom_id}/students** (rol: `admin_escuela`) → `200 OK` con alumnos enriquecidos (IMC y casos médicos). Salón de otra escuela retorna `403 Forbidden`.
- [x] **GET /api/v1/school-admin/classrooms/categories-summary** (rol: `admin_escuela`) → `200 OK` con combinaciones únicas de categoría y nivel.
- [x] **GET /api/v1/school-admin/classrooms/categories-available** (rol: `admin_escuela`) → `200 OK` con categorías disponibles.
- [x] **GET /api/v1/school-admin/classrooms/categories/{cat_id}/levels/{lvl}/sections** (rol: `admin_escuela`) → `200 OK` con secciones disponibles.
- [x] **GET /api/v1/school-admin/students/{student_id}** (rol: `admin_escuela`) → `200 OK` con detalle, salón, representantes saneados (sin password) e info de salud. Estudiante de otra escuela retorna `403 Forbidden`.
- [x] **GET /api/v1/school-admin/representatives/{parent_id}** (rol: `admin_escuela`) → `200 OK` con hijos asociados e IMC. Padre sin hijos en la escuela retorna `403 Forbidden`.
- [x] **PUT /api/v1/school-admin/students/{student_id}** (rol: `admin_escuela`) → `200 OK` actualizando datos y reasignando representante.
- [x] **GET /api/v1/school-admin/search/representatives** (rol: `admin_escuela`) → `200 OK` con búsqueda ILIKE paginada.
- [x] **PATCH /api/v1/school-admin/students/{student_id}/activate** (rol: `admin_escuela`) → `200 OK` activando al estudiante (`is_active=True`).
- [x] **PATCH /api/v1/school-admin/students/{student_id}/deactivate** (rol: `admin_escuela`) → `200 OK` desactivando al estudiante (`is_active=False`).

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest` (95 passed)

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
