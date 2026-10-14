# [🧹 Refactor: GH-28] - Cobertura de tests para Autenticación, Registro por Rol y Vinculación Familiar

## Descripción

Este pull request implementa la suite completa de pruebas unitarias y de integración para los módulos de Autenticación (`auth.py`, `auth_service.py`), Seguridad JWT (`security.py`, `deps.py`) y Vinculación Familiar de Representantes (`parent.py`, `parent_service.py`).

Se añaden 37 casos de prueba automatizados siguiendo rigurosamente las 5 leyes de `vitaly-feature-testing`:
1. **Envoltorio APIResponse:** Verificación sistemática del envelope uniforme (`success`, `data`, `message`) en todas las respuestas exitosas y de error.
2. **Aislamiento Multi-Tenancy y Claims Estrictos en JWT:** Verificación exhaustiva de que los tokens emitidos en `/login` contengan únicamente los claims autorizados (`sub`, `email`, `role`, `name`, `gender` y metadatos de rol) y **NO contengan** el claim `school_id`, preservando el principio de aislamiento silencioso resuelto exclusivamente en el servidor.
3. **Mocks Deterministas:** Simulación determinista del cliente `supabase-py` para las tablas `user`, `user_roles`, `system_administrator`, `school_administrator`, `doctor`, `parent`, `school`, `student`, `student_representative` y `token_blacklist`.
4. **Semántica REST y Reglas de Negocio:** Verificación de creación de usuarios con estado inicial inactivo (`is_active=False`, `is_deleted=False`), denegación con `400 Bad Request` ante duplicidad de correo, `403 Forbidden` ante intentos de inicio de sesión de usuarios inactivos o eliminados, y `401 Unauthorized` ante contraseñas incorrectas o correos inexistentes.
5. **Matriz RBAC y Ciclo de Revocación:** Comprobación del flujo de `logout` con inserción del token en lista negra (`token_blacklist`), verificación de que reintentos con el token revocado sean rechazados con `401 Unauthorized`, restricción estricta de `POST /link-students` exclusivamente al rol `representante` (`403 Forbidden` para otros roles) y validación de esquemas (`422 Unprocessable Entity`).

Closes #28

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

- [x] **POST /api/v1/auth/register-system-admin** → `200 OK` con envelope `APIResponse`, creación de usuario en `user` (`is_active=False`), rol en `user_roles` y registro en `system_administrator` con `level_privilege=1`. Correo duplicado retorna `400 Bad Request`.
- [x] **POST /api/v1/auth/register-school-admin** → `200 OK` con envelope `APIResponse`, creación de perfil en `school_administrator` con `status=2`, `school_id` y cargo administrativo. Correo duplicado retorna `400 Bad Request`.
- [x] **POST /api/v1/auth/register-doctor** → `200 OK` con envelope `APIResponse`, creación de perfil en `doctor` con `doc_license_number` y `especially`. Correo duplicado retorna `400 Bad Request`.
- [x] **POST /api/v1/auth/register-parent** → `200 OK` con envelope `APIResponse`, creación de perfil en `parent` y vinculación automática de alumnos por cédula. Correo duplicado retorna `400 Bad Request`.
- [x] **POST /api/v1/auth/login** → `200 OK` retornando `APIResponse[Token]` (`access_token`, `token_type="bearer"`). Verificación de claims (`sub`, `email`, `role`, `name`, `gender`, metadatos) y ausencia de `school_id`. Rechazo de cuentas inactivas (`403`), eliminadas (`403`), contraseña errónea (`401`) y usuario no registrado (`401`).
- [x] **POST /api/v1/auth/logout** → `200 OK` revocando el token e insertándolo en `token_blacklist`. Petición subsiguiente con el token revocado retorna `401 Unauthorized`.
- [x] **POST /api/v1/parent/link-students** (rol: `representante`) → `200 OK` vinculando estudiantes autorizados por cédula y detectando ya vinculados. Sin cédula retorna `200 OK` con `data=None` descriptivo. Perfil parent inexistente retorna `404 Not Found`.
- [x] **Matriz RBAC en /link-students** → Rechazo `403 Forbidden` para `admin_escuela`, `admin_sistema` y `doctor`. Rechazo `401` ante peticiones sin token o con token revocado.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest` (215 passed)

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
