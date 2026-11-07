# [🗑️ Chore] - Versionar y alinear reglas, skills y roles de agentes

## Descripción

Versiona en el repositorio el ecosistema de agentes del backend (reglas, skills, roles y `AGENTS.md`) y lo alinea con el código real y con las decisiones del proyecto. No modifica código de la aplicación (`app/`); el único cambio con efecto en runtime es el rango de versión de FastAPI.

1. **Ecosistema de agentes versionado:** `.agents/` como fuente única, con symlinks para Claude (`.claude/`), Grok (`.grok/`), Cursor (`.mdc`) y Copilot (`.github/copilot-instructions.md`).
2. **Skills propias `vitaly-*`:** `branch-pr` y `chained-pr` se renombran a `vitaly-branch-pr` y `vitaly-chained-pr` para no colisionar con skills globales homónimas. Las skills de arquitectura, scaffold, RBAC, tenant isolation, respuestas, Supabase, contratos, testing, auditoría y exportaciones se alinean con las reglas.
3. **Decisiones documentadas:**
   - Registro de otra escuela → `403`; inexistente → `404`; colección vacía → `200` con `[]`.
   - Las excepciones que no son `HTTPException` producen un 500 sin envelope: los servicios las envuelven en `HTTPException(500)`.
   - Paginación: `meta=PaginationMeta` para endpoints nuevos; el formato anidado actual queda como legado.
   - Helper compartido de `school_id` en `app/services/tenancy.py` (pendiente, #22).
   - Handlers `def` síncronos con supabase-py y dependencias con `Annotated` en código nuevo.
   - `pr-review` emite el veredicto de PR y usa `fastapi-code-review` como checklist técnico.
4. **Roles:** tenant isolation compartido (Database Specialist implementa, Security Sentinel audita); el rol médico se reescribe a lo que existe hoy (IMC, `medical_case`, `student_metrics`).
5. **Limpieza:** se eliminan skills importadas de otros proyectos o fuera de stack; las de SQLAlchemy se archivan en `.agents/future-skills/`.
6. **Dependencias:**
   - `requirements.txt`: `fastapi[standard]>=0.122.0,<0.144.0` (desde 0.122.0 `HTTPBearer` responde `401` cuando falta el token, antes `403`).
   - `requirements-dev.txt`: se agrega `ruff>=0.17.0,<0.18.0`.
7. **Issues abiertos a partir de la revisión:** #21 (bug de IMC sin conversión cm→m), #22 (helper `tenancy.py`), #23 (citas erróneas en reglas).

Este PR no tiene issue asociado. Supera las 400 líneas porque es documentación de agentes que no se puede dividir con sentido; se solicita `size:exception`.

## Tipo de cambio

Marque con una x dentro de los `[]` los que apliquen

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [x] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [x] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [x] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Prueba manual. No hay endpoints modificados; la verificación cubre las dependencias y la carga de las skills:

- [ ] **Dependencias:** `pip install -r requirements-dev.txt` instala FastAPI dentro del rango `>=0.122.0,<0.144.0` y ruff.
- [ ] **Regresión:** `pytest tests/` pasa con la nueva versión de FastAPI.
- [ ] **Token ausente:** cualquier endpoint protegido (ej. **GET /api/v1/school-admin/students/{student_id}**, sin header `Authorization`) → `401` con envelope `APIResponse`.
- [ ] **Symlinks:** `find .claude .grok -type l ! -exec test -e {} \; -print` no devuelve nada.
- [ ] **Skills:** Claude Code lista `vitaly-branch-pr` y `vitaly-chained-pr`, y ya no lista las skills de SQLAlchemy del proyecto.

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest`

## Lista de Verificación

- [x] He agregado las nuevas dependencias en la descripción
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción *(no aplica)*
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [x] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [ ] Mis cambios pasan el build y lint del proyecto localmente
- [ ] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona *(no aplica)*
- [ ] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
