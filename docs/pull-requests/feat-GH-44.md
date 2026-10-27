# [✨ Feat: GH-44] - Anticipación mínima configurable en revisiones

## Descripción

Implementa la contraparte backend de [frontend #31](https://github.com/Teixeira49/vitaly-care-for-families/issues/31): el inicio de un evento escolar solo se acepta a partir de `ahora_del_servidor + margen`, donde el margen se persiste en base de datos y, a falta de configuración válida, son cinco minutos.

Cambios concretos:

1. **Nueva tabla `settings`** (`supabase/migrations/20261026120000_create_settings_table.sql`). Configuración **global** del sistema: una fila por clave, con un `jsonb` autodescriptivo `{"type": ..., "value": ...}` para que cualquier tipo de dato quepa sin migraciones adicionales. Dos CHECK la protegen: la forma del objeto y que el tipo declarado coincida con el tipo JSON real. No tiene `school_id`: no participa del aislamiento multi-tenant.
2. **`app/services/settings_service.py`**. `SETTING_SPECS` es la única fuente de verdad de cada clave (tipo, rango, valor por defecto) y gobierna los dos extremos: la lectura cae al valor por defecto y deja log si la fila falta, está malformada, declara otro tipo, se sale de rango o la base de datos falla — **la configuración nunca desactiva una barrera de negocio**; la escritura del `admin_sistema` rechaza lo mismo con 400 y un motivo explícito.
3. **`app/services/event_schedule_policy.py`**. Normaliza a UTC, calcula `ahora + margen` y redondea el umbral al siguiente minuto exacto (a las 15:00:30 con el fallback, el primer inicio válido es 15:06). Ni el margen ni el reloj de referencia llegan del cliente.
4. **Integración en eventos**. `create_event` valida antes de cualquier escritura, de modo que un horario rechazado no deja evento ni participaciones. `update_event` revalida **solo si el cuerpo trae `init_time`**: reprogramar cuenta como programar, pero corregir el título de un evento ya ocurrido sigue permitido.
5. **Contrato de error**. Nueva `FieldValidationError` (`app/core/exceptions.py`) y el handler global ahora propaga `errors[]`. El rechazo es un **422** dentro de `APIResponse`, con `errors[0].loc = ["body", "init_time"]` y `type = "event_schedule_unavailable"`. Ni el mensaje ni los metadatos revelan el margen vigente ni el umbral calculado.
6. **`GET`/`PUT /api/v1/admin/settings`** tras `get_current_admin_sistema`, para que el margen se administre sin SQL crudo.

Decisiones acordadas con el autor del issue, que resuelven su punto 5 («Resolver antes de implementar»):

- **Alcance:** configuración global del sistema, sin override por institución. Si más adelante hace falta, se añade `school_id` nullable (NULL = global) y un índice único sobre `(key, COALESCE(school_id, -1))`.
- **Rango válido:** 0 a 10080 minutos (7 días), con fallback de 5. Con 0 la barrera sigue activa: el pasado nunca se acepta.
- **Edición:** la anticipación se revalida solo cuando cambia `init_time`.

**Dependencias nuevas:** ninguna.
**Variables de entorno nuevas:** ninguna.
**Migración de base de datos:** sí — `supabase/migrations/20261026120000_create_settings_table.sql`. Ya fue aplicada en el entorno de Supabase actual. Validada previamente en una instancia Postgres local desechable: se aplica, es reejecutable, siembra la clave y los CHECK aceptan/rechazan lo esperado.

> [!WARNING]
> **Pendiente de entorno, no de código:** la tabla `settings` quedó con **RLS activado y sin políticas** en Supabase. Como el backend se conecta con la `anon key`, no puede leer ni escribir esa tabla: la validación funciona, pero siempre con el fallback de 5 minutos, y los endpoints de administración no operarían. Se resuelve con `ALTER TABLE public.settings DISABLE ROW LEVEL SECURITY;` (el resto de tablas del proyecto no tienen RLS). No se incluye en esta PR por ser una decisión de infraestructura.

Closes #44

> Nota: GitHub solo cierra el issue automáticamente al fusionar en la rama por defecto. Esta PR apunta a `development`, así que el cierre ocurrirá al promover a `main` o deberá hacerse manualmente.

## Tipo de cambio

- [x] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [ ] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Pruebas automatizadas (`pytest`): 391 tests en verde, 40 de ellos nuevos en `tests/test_settings_and_event_lead_time.py`, cubriendo fallback, límites exactos de los criterios de aceptación, redondeo con segundos, equivalencia de instantes con distintos offsets, configuración inválida, ausencia de escrituras ante rechazo, contrato del error y matriz RBAC de la configuración.

Prueba manual sugerida (reloj del servidor en UTC; usa horas relativas a tu «ahora»):

- [ ] **POST /api/v1/school-admin/events/** (rol: `admin_escuela`) con `init_time` = ahora + 1 minuto → **422**, `success:false`, `errors[0].loc == ["body","init_time"]`, `type == "event_schedule_unavailable"` y mensaje genérico sin cifras.
- [ ] **POST /api/v1/school-admin/events/** (rol: `admin_escuela`) con `init_time` = ahora + 30 minutos → **200** con `data.event_id`; verificar en Supabase que se creó la fila en `event` y sus `event_participation`.
- [ ] **POST /api/v1/school-admin/events/** rechazado → confirmar en Supabase que **no** se creó ninguna fila en `event` ni en `event_participation`.
- [ ] **PUT /api/v1/school-admin/events/{id}** (rol: `admin_escuela`) con solo `title` sobre un evento ya pasado → **200** (no revalida la anticipación).
- [ ] **PUT /api/v1/school-admin/events/{id}** (rol: `admin_escuela`) con `init_time` = ahora + 1 minuto → **422** con el mismo error, y el evento sin modificar.
- [ ] **GET /api/v1/admin/settings** (rol: `admin_sistema`) → **200** con `event_min_lead_time_minutes` y su valor vigente.
- [ ] **PUT /api/v1/admin/settings/event_min_lead_time_minutes** (rol: `admin_sistema`) con `{"value": {"type": "integer", "value": 60}}` → **200**; repetir el POST de evento con ahora + 30 minutos → ahora responde **422** sin reiniciar la API.
- [ ] **PUT /api/v1/admin/settings/event_min_lead_time_minutes** (rol: `admin_sistema`) con `value` 10081 o de tipo `string` → **400** indicando tipo y rango admitidos; el valor almacenado no cambia.
- [ ] **GET /api/v1/admin/settings** (rol: `admin_escuela`) → **403**.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest`
- Requiere la migración `20261026120000_create_settings_table.sql` aplicada. Sin ella (o con RLS bloqueando la lectura) el sistema sigue funcionando con el fallback de 5 minutos.

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción *(no aplica: ninguna)*
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción *(no aplica: ninguna)*
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [x] Mis cambios pasan el build y lint del proyecto localmente
- [x] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona
- [x] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
