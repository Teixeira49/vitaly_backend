# [🛠️ Fix: GH-1] - Separar los Auth de Clientes y de administración

## Descripción

Separa la autenticación en dos portales para que un token emitido para un dominio no sea
válido en el otro. El login de clientes conserva su ruta y su contrato, así que el frontend
no se rompe.

1. **Portales de login.** `POST /api/v1/auth/login` pasa a ser el portal de clientes
   (admin_escuela, doctor, representante). Nuevo `POST /api/v1/auth/admin/login`, exclusivo
   para admin_sistema.
2. **Rechazo antes de emitir el JWT.** `auth_service.authenticate_user` recibe el portal
   (`TokenScope`) y responde 403 si el rol no le pertenece. Ese rechazo ocurre después de
   validar la contraseña, por lo que no revela el rol a quien no tiene las credenciales.
   Efecto colateral: un usuario sin fila en `user_roles` ya no recibe un token con rol
   `desconocido`.
3. **Claim `scope` y gates de procedencia.** Todo token lleva `scope` (`admin` | `client`).
   Nuevos gates `get_current_admin` y `get_current_client` en `app/api/deps.py`; los gates de
   rol existentes se encadenan sobre ellos (`get_current_admin_sistema` → `get_current_admin`;
   admin_escuela, doctor y representante → `get_current_client`). Un token sin `scope` responde
   401; uno de otro portal, 403. `logout` sigue aceptando cualquier token válido.
4. **Esquemas.** `LoginBase` (campos documentados con `Field(description=...)`), `UserLogin`
   (clientes, nombre legado conservado por el contrato con el frontend) y `AdminLoginCreate`
   (administración). Se usan sufijos estándar en lugar de los `AdminAuthRequest` /
   `ClientAuthRequest` del issue, por la regla `schema-naming-convention.md`.
5. **OpenAPI.** Nueva sección «Autenticación - Administración» en Swagger/ReDoc; ambos logins
   documentan `summary`, `description` y las respuestas 401 (credenciales) y 403 (cuenta
   eliminada/inactiva o portal equivocado). Las rutas públicas de `auth.py` llevan
   `# PUBLIC_ROUTE` (avance parcial de #17).
6. **Documentación de agentes.** La regla RBAC y las skills `vitaly-rbac` y
   `vitaly-feature-testing` reflejan los nuevos gates y el claim `scope`.
7. **Ruta del frontend.** `AGENTS.md`/`CLAUDE.md`, `cross-repo-e2e.md` y las skills apuntan a
   `../vitaly_frontend/vitaly-care-for-families` (commit 📝 separado).

⚠️ **Al desplegar, todos los usuarios deberán iniciar sesión de nuevo:** los tokens emitidos
antes del cambio no llevan `scope` y reciben 401 (el frontend ya redirige a `/login` ante un
401).

Fuera de alcance: el refactor E2E de la ruta de clientes a `/auth/client/login` queda como tarea
propia: #39 (backend) y Teixeira49/vitaly-care-for-families#23 (frontend, que además tipará el
claim `scope`). No se añaden factores
adicionales para admins (decisión: nada por ahora).

Sin nuevas dependencias, variables de entorno ni migraciones.

Base: `development`. Rama: `feat/GH-1`.

Closes #1

## Tipo de cambio

- [x] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [x] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Pruebas automatizadas: `python -m pytest -q` → 291 pasan (19 nuevas en `tests/test_auth.py`);
`python -m ruff check app tests` sin errores.

Prueba manual en Swagger (`/docs`):

- [ ] **POST /api/v1/auth/login** (rol: `admin_escuela`, `doctor` o `representante`) → 200; el JWT de `data.access_token` incluye `scope: "client"`.
- [ ] **POST /api/v1/auth/login** (rol: `admin_sistema`) → 403, `data: null`, mensaje «no tiene acceso al portal de clientes».
- [ ] **POST /api/v1/auth/admin/login** (rol: `admin_sistema`) → 200; el JWT incluye `scope: "admin"`.
- [ ] **POST /api/v1/auth/admin/login** (rol: `representante`) → 403, `data: null`, mensaje «no tiene acceso al portal de administración».
- [ ] **GET /api/v1/admin/users** (token de `admin_sistema` emitido antes del cambio, sin `scope`) → 401 «inicia sesión de nuevo».
- [ ] **POST /api/v1/parent/link-students** (token de `admin_sistema` con `scope: "admin"`) → 403 «portal de clientes».
- [ ] **GET /docs** → sección «Autenticación - Administración» con el login de administración y respuestas 401/403 documentadas.
- [ ] Frontend: login con cada rol de cliente sigue entrando a su panel.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest`

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción (no aplica)
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción (no aplica)
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios

🤖 Generated with [Claude Code](https://claude.com/claude-code)
