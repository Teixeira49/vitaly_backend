# [🧹 Refactor: GH-39] - Migrar el login de clientes a /auth/client/login

## Descripción

Hace simétricas las rutas de los dos portales de autenticación creados en #1, sin romper el
frontend:

1. **Nueva ruta.** `POST /api/v1/auth/client/login` en su propio router y sección de
   Swagger/ReDoc («Autenticación - Clientes»), simétrica con `POST /api/v1/auth/admin/login`.
   Mismo comportamiento que el login de clientes actual: admin_escuela, doctor y representante;
   admin_sistema recibe 403 sin emitir token; JWT con `scope=client`.
2. **Alias obsoleto.** `POST /api/v1/auth/login` se mantiene, delega en el nuevo endpoint y
   aparece como `deprecated` en `/docs`. El frontend sigue funcionando sin cambios hasta que
   migre (Teixeira49/vitaly-care-for-families#23).
3. **Esquema.** `UserLogin` pasa a `ClientLoginCreate` (sufijo estándar, simétrico con
   `AdminLoginCreate`). El frontend no se ve afectado: usa su propia interfaz
   `LoginCredentials` y el cuerpo (`email`, `password`) no cambia.
4. **Documentación.** Regla RBAC y skill `vitaly-rbac` actualizadas con la nueva ruta y el
   alias.

**Orden de despliegue:** esta PR → frontend Teixeira49/vitaly-care-for-families#28 (consume
`/auth/client/login`) → retirada del alias en #43. Retirar el alias antes de desplegar el
frontend rompería el login de los tres roles de cliente.

Pendiente de decisión (abierta en #43): cuánto tiempo se mantiene el alias `/auth/login`.

Sin nuevas dependencias, variables de entorno ni migraciones.

Base: `development`. Rama: `refactor/GH-39`.

Closes #39

## Tipo de cambio

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [x] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Pruebas automatizadas: `python -m pytest -q` → 304 pasan (3 nuevas para el alias; los tests
del portal de clientes usan la ruta nueva); `python -m ruff check app tests` sin errores.

Prueba manual en Swagger (`/docs`):

- [ ] **POST /api/v1/auth/client/login** (rol: `admin_escuela`, `doctor` o `representante`) → 200; el JWT incluye `scope: "client"`.
- [ ] **POST /api/v1/auth/client/login** (rol: `admin_sistema`) → 403, `data: null`.
- [ ] **POST /api/v1/auth/login** (rol: `representante`) → 200, igual que la ruta nueva; aparece tachado como obsoleto en `/docs`.
- [ ] **POST /api/v1/auth/admin/login** (rol: `admin_sistema`) → 200 sin cambios.
- [ ] **GET /docs** → sección «Autenticación - Clientes» con el login de clientes.
- [ ] Frontend actual (sin #23): login con cada rol de cliente sigue entrando a su panel.

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
