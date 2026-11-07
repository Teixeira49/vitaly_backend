# [🧹 Refactor: GH-29] - Cobertura de tests para Administración Global, Colegios y Años Académicos

## Descripción

Este pull request implementa la suite completa de pruebas unitarias y de integración para los módulos de Administración Global del Sistema (`admin.py`), Gestión Escolar Centralizada (`admin_school.py`), Años Académicos (`academic_year.py`) y Catálogos Públicos (`catalogs.py`), junto con sus servicios asociados (`admin_service.py`).

Se añaden 57 casos de prueba automatizados siguiendo rigurosamente las 5 leyes de `vitaly-feature-testing`:
1. **Envoltorio APIResponse:** Verificación sistemática del envelope estándar (`success`, `data`, `message`) en todas las respuestas exitosas y de error.
2. **Control de Acceso de Superadministrador (RBAC Estricto):** Verificación de que todos los endpoints de administración global en `/api/v1/admin` y `/api/v1/admin/schools` requieran exclusivamente el rol `admin_sistema`, bloqueando con `403 Forbidden` a cualquier otro rol (`admin_escuela`, `doctor`, `representante`) y previniendo escalamiento de privilegios o fugas transversales entre escuelas.
3. **Mocks Deterministas:** Simulación determinista del cliente `supabase-py` para las tablas `user`, `user_roles`, `system_administrator`, `school_administrator`, `doctor`, `school`, `classroom`, `student`, `classroom_registration`, `academic_year`, `states`, `school_type`, `classroom_category` y `system_status`.
4. **Semántica REST y Reglas de Negocio:** Validación de aprobación individual y masiva de usuarios inactivos, prevención de autodeshabilitación (`400`) y jerarquía de privilegios (`403` al intentar alterar a administradores de igual o mayor nivel), validación de unicidad de RIF y nombre por estado en escuelas, rangos de grados permitidos por categoría escolar (Preescolar 1-3, Primaria 1-6, Bachillerato 1-5), cálculo automático de vigencia (`is_current`) y rechazo de rangos de fecha invertidos (`400`).
5. **Rutas Públicas y Validación:** Verificación de acceso público sin token (`# PUBLIC_ROUTE`) para catálogos y endpoints de año académico, y rechazo `422 Unprocessable Entity` ante payloads malformados.

Closes #29

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

- [x] **GET /api/v1/admin/users** (rol: `admin_sistema`) → `200 OK` con listado paginado de usuarios en envelope `APIResponse`.
- [x] **GET /api/v1/admin/users/pending** (rol: `admin_sistema`) → `200 OK` filtrando usuarios inactivos (`isActive=False`).
- [x] **PATCH /api/v1/admin/users/approve** (rol: `admin_sistema`) → `200 OK` aprobando usuario. Usuario inexistente retorna `404`, ya aprobado retorna `400` y eliminado retorna `400`.
- [x] **PATCH /api/v1/admin/users/approve/bulk** (rol: `admin_sistema`) → `200 OK` con aprobación masiva y reporte de cantidad de aprobados.
- [x] **GET /api/v1/admin/users/{user_id}/details** (rol: `admin_sistema`) → `200 OK` con detalles específicos según rol (médico, escuela, representante o sistema). Usuario inexistente retorna `404`.
- [x] **PATCH /api/v1/admin/users/{user_id}/toggle-active** (rol: `admin_sistema`) → `200 OK` alternando estatus activo. Autodeshabilitación rechazada con `400` y alteración a admin de igual o mayor jerarquía rechazada con `403`.
- [x] **POST /api/v1/admin/schools/** (rol: `admin_sistema`) → `200 OK` creando escuela. Rechazo ante año de fundación negativo (`400`), año futuro (`400`), RIF duplicado (`400`) y nombre duplicado en el mismo estado (`400`).
- [x] **POST /api/v1/admin/schools/classrooms** (rol: `admin_sistema`) → `200 OK` creando salón. Categoría inválida retorna `400`, nivel excedido retorna `400`, escuela o año inexistente retorna `404`, salón duplicado retorna `400`.
- [x] **POST /api/v1/admin/schools/students** (rol: `admin_sistema`) → `200 OK` registrando estudiante. CI duplicada retorna `400`, edad mayor a 21 años retorna `422`.
- [x] **PATCH /api/v1/admin/schools/students/{id}** (rol: `admin_sistema`) → `200 OK` actualizando estudiante. No encontrado `404`, eliminado `400`, payload vacío `400`.
- [x] **POST /api/v1/admin/schools/classrooms/register & bulk** (rol: `admin_sistema`) → `200 OK` vinculando estudiantes a salones de clase.
- [x] **GET /api/v1/admin/schools/, classrooms/, students/** (rol: `admin_sistema`) → `200 OK` con listados paginados y detalles por ID.
- [x] **POST /api/v1/academic-year** → `200 OK` creando año académico y calculando `is_current` según fecha actual. Fechas invertidas retornan `400`.
- [x] **PATCH /api/v1/academic-year/sync-current** → `200 OK` sincronizando vigencia de años escolares contra la fecha del día.
- [x] **GET /api/v1/catalogs/states, school-types, classroom-categories, system-status** → `200 OK` accesibles públicamente sin token (# PUBLIC_ROUTE).
- [x] **Matriz RBAC transversal** → Rechazo `403 Forbidden` para `admin_escuela`, `doctor` y `representante` en todos los endpoints de administración global. Rechazo `401` ante peticiones sin token.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest` (272 passed)

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
