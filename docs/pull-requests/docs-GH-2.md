## Descripción

Documentación formal de todo el backend, cerrando el issue #2. Es la contraparte retroactiva del issue #8 (la regla que obliga este formato en código nuevo, ya recogida en el estándar #5 del `AGENTS.md`): #8 fija la norma hacia adelante, esta PR la aplica a lo existente.

Cambios concretos:

1. **Nuevo `app/core/openapi_responses.py`** — bloques reutilizables de respuestas de error (401/403/404/422/500 sobre el envelope `APIResponse`, más 400/409 y la factoría `error_response`) con presets compuestos (`PUBLIC_RESPONSES`, `PROTECTED_RESPONSES`, `TENANT_DETAIL_RESPONSES`, …). Evita duplicar un diccionario literal en cada una de las 68 rutas.
2. **Endpoints (`app/api/`)** — los 68 endpoints pasan de 6/68 a 68/68 en `summary`, `description` y `responses`. Sus docstrings se reescriben con las secciones obligatorias **Multi-tenancy**, **RBAC** y **Raises**; ya no queda ninguno de 1–2 líneas (antes había 22).
3. **Docstrings de código (`app/services/`, `app/core/`, `app/utils/`, `app/api/deps.py`)** — de 39/101 a **102/102** funciones documentadas en estilo Google (`Args`, `Returns`, `Raises`), más docstring de módulo y de clase en cada archivo.
4. **Esquemas (`app/schemas/`)** — de 15/204 a **204/204** campos con `Field(description=...)`, y docstring en cada modelo Pydantic.
5. **Marcadores `# PUBLIC_ROUTE`** — migrados en `catalogs.py` desde dentro del docstring a un comentario encima de la función (como pide `rbac-enforcement.md`) y añadidos a las demás rutas realmente públicas (`auth`, `school`, raíz y health).

### Comportamientos documentados tal cual están, sin modificarlos

Esta PR es de documentación: no cambia lógica. Tres desviaciones conocidas quedan descritas con honestidad en vez de maquilladas:

- **404 en colecciones vacías** (`admin_service.get_schools/get_classrooms/get_students`, `get_academic_grades`, `get_students_by_classroom`): documentado como comportamiento legado contrario al estándar REST, con referencia al issue **#15**.
- **`POST /academic-year` y `PATCH /academic-year/sync-current` sin autenticación**: **no** se les puso `# PUBLIC_ROUTE`, porque eso afirmaría que su exposición es intencional. Llevan un `TODO(GH-14)` y una advertencia visible en su `description` de Swagger. Issue **#14**.
- **`search_representatives` consulta todas las escuelas**: el servicio no recibe `user_id` y por tanto no filtra por escuela. Queda documentado explícitamente en la sección Multi-tenancy del endpoint y en el docstring del servicio.

Closes #2

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Prueba manual: la verificación principal es visual, en Swagger (`/docs`). Los 272 tests existentes pasan sin cambios, lo que confirma que no se alteró comportamiento.

- [ ] **Abrir `http://localhost:8000/docs`** → cada endpoint muestra su título corto, su descripción y, al desplegarlo, los códigos 401/403/404/422/500 con un ejemplo del envelope `APIResponse` (`success: false`, `message`, `data: null`).
- [ ] **GET `/api/v1/catalogs/states`** (rol: ninguno, ruta pública) → 200 con la lista de estados; en `/docs` aparece sin candado y con 422/500 documentados.
- [ ] **GET `/api/v1/school-admin/classrooms/{classroom_id}/students`** (rol: `admin_escuela`) → 200 con los estudiantes del salón propio; con el `classroom_id` de otra escuela → 403; con un id inexistente → 404. Ambos códigos están descritos en `/docs`.
- [ ] **GET `/api/v1/admin/schools/{school_id}`** (rol: `admin_sistema`) → 200 con el detalle; con un id inexistente → 404.
- [ ] **POST `/api/v1/auth/login`** (rol: ninguno, ruta pública) → 200 con el token; credenciales malas → 401; cuenta sin aprobar → 403.
- [ ] **Revisar los esquemas en `/docs`** → al desplegar cualquier modelo (`SchoolRead`, `StudentCreate`, `APIResponse`), cada campo muestra su descripción.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest`

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción *(no aplica: ninguna dependencia nueva)*
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción *(no aplica: ninguna variable nueva)*
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente *(`ruff check app/` → All checks passed)*
- [ ] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona *(no aplica: cambio exclusivamente documental, sin lógica nueva que probar)*
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios *(272 passed)*
