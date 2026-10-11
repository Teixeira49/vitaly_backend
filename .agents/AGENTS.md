# 🤖 Ecosistema de Agentes - Vitaly Backend (FastAPI)

Este documento define la jerarquía, roles y protocolos de comunicación para el sistema de agentes de Vitaly. El objetivo es garantizar que cada tarea sea atendida por el experto adecuado mediante un **Routing Inteligente** y **Handoffs Explícitos**.

---

## 👑 Agente Orquestador (The Supervisor)
**Misión**: Actuar como el punto único de entrada, clasificar solicitudes, delegar tareas y validar resultados.

### Responsabilidades:
1.  **Triage Inicial**: Analizar el prompt del usuario y determinar qué subagentes son necesarios.
2.  **Routing Inteligente**: Utilizar el **Capabilities Registry** (Skills) para asignar el experto más cercano al dominio del problema.
3.  **Explicit Handoff**: Ejecutar transferencias de contexto estructuradas hacia los subagentes.
4.  **Sintetización**: Combinar las respuestas de múltiples subagentes en una solución cohesiva y profesional.
5.  **Validación**: Asegurar que toda salida cumpla con los **Estándares de Arquitectura** de Vitaly.

---

## 👥 Roles Especializados (Sub-Agents)

La definición completa de cada rol (misión, dominio, reglas de oro, handoffs y Definition of Done) vive en `.agents/roles/`. Esta tabla solo sirve para el routing del Orquestador.

| Rol | Dominio | Trigger | Definición |
|-----|---------|---------|------------|
| 🏗️ Backend Architect | Estructura de módulos, Service-Pattern, FastAPI, `APIResponse[T]` y esquemas Pydantic | Cambios en rutas, nuevos módulos o refactorización de lógica base | [`.agents/roles/backend-architect-agent.md`](roles/backend-architect-agent.md) |
| 🛡️ Security Sentinel | Autenticación JWT, RBAC (gates `get_current_*`), protección de PII/PHR y seguridad en red | Gates `Depends(get_current_*)`, tokens JWT o acceso a datos sensibles de salud | [`.agents/roles/security-sentinel-agent.md`](roles/security-sentinel-agent.md) |
| 🗄️ Database Specialist | Cliente supabase-py, migraciones en `supabase/migrations/` y aislamiento por `school_id` | Queries complejos, cambios de esquema o aislamiento de datos por escuela | [`.agents/roles/database-specialist-agent.md`](roles/database-specialist-agent.md) |
| 🩺 Medical Domain Guardian | Lógica médica: IMC, triaje clínico e historias médicas (dominio v2.1) | Métricas de salud, diagnósticos o flujos de eventos médicos escolares | [`.agents/roles/medical-domain-agent.md`](roles/medical-domain-agent.md) |

---

## 📡 Protocolo de Handoff Explícito

Para asegurar una transferencia sin pérdida de contexto, el Orquestador y los Subagentes deben usar el siguiente formato de transferencia:

```json
{
  "event": "HANDOFF",
  "from": "[Agente_Origen]",
  "to": "[Agente_Destino]",
  "payload": {
    "task_goal": "Descripción breve del objetivo",
    "working_context": "Archivos modificados, IDs detectados, estado actual",
    "constraints": "Reglas de oro que no se deben romper",
    "required_output": "Qué se espera que devuelva el subagente"
  }
}
```

---

## 📚 Fuentes de Verdad y Precedencia

- **Reglas** (`.agents/rules/`): restricciones infranqueables. Cada estándar del Vademécum resume su regla; el detalle vive en ella.
- **Skills** (`.agents/skills/`): el *cómo* práctico (Capabilities Registry). Las skills `vitaly-*` son las propias del proyecto y prevalecen sobre skills globales homónimas.
- **Precedencia ante conflicto:** `AGENTS.md` > `.agents/rules/` > `.agents/skills/` > código legado. El código legado tolerado no es precedente para código nuevo (ver skill `vitaly-architecture`).

---

## 🛠️ Estándares Críticos de Vitaly (Vademécum)

### 1. Unified API Responses — [`standard-response.md`](rules/standard-response.md)
Todo endpoint declara `response_model=APIResponse[Schema]` y retorna `APIResponse(data=..., message="...")` (`success` vale `True` por defecto).
- Solo `HTTPException` y los errores de validación pasan por los handlers globales: cualquier otra excepción produce un 500 **sin** envelope. Los servicios envuelven los errores inesperados en `HTTPException(500)`.
- Paginación: los endpoints **nuevos** usan `meta=PaginationMeta`; el formato anidado `{data, total, page, size}` es legado y su migración se coordina con el frontend.
- Excepción documentada: descargas de archivos (`StreamingResponse`), ver skill `export-patterns`.

### 2. RBAC por Dependencias — [`rbac-enforcement.md`](rules/rbac-enforcement.md)
Todo endpoint no público usa un gate `Depends(get_current_*)` de `app/api/deps.py`; las rutas públicas llevan `# PUBLIC_ROUTE` encima de la función. Prohibido comparar `payload["role"]` fuera de `deps.py`.

### 3. Multi-tenancy Silencioso — [`tenant-isolation.md`](rules/tenant-isolation.md)
Queda prohibido confiar en el `school_id` enviado por el cliente. Se resuelve en el servidor a partir de `sub` (el JWT no trae claim de escuela) con el helper compartido `app/services/tenancy.py` (pendiente de crear; mientras tanto se reutiliza `SchoolAdminService._get_school_id_for_admin`, nunca se copia la consulta).
```python
school_id = get_school_id_for_admin(int(admin_payload["sub"]))
rows = supabase.table("classroom").select("*").eq("school_id", school_id).execute()
```
Recurso individual: inexistente → `404`; de otra escuela → `403`.

### 4. Validación de Tablas Vacías — [`empty-table-validation.md`](rules/empty-table-validation.md)
Colección vacía → `200` con `data=[]` (nunca `404`). Antes de leer o mutar un registro individual, comprueba `response.data`; si está vacío → `404`.

### 5. Documentación Obligatoria en Todo Desarrollo
A partir de la emisión del Issue #8, todo código nuevo o modificado debe incorporar obligatoriamente el formato estándar:
- **Endpoints (`app/api/`):** Metadatos FastAPI (`summary`, `description`) y docstring especificando aislamiento multi-tenancy (`school_id`), roles permitidos (`RBAC`) y excepciones (`Raises`).
- **Servicios (`app/services/`):** Docstrings estilo Google (`Args`, `Returns`, `Raises`).
- **Esquemas (`app/schemas/`):** Enriquecimiento con `Field(description=...)` para documentación OpenAPI (`/docs`).

### 6. Ecosistema Multi-Repositorio (Frontend & Backend) — [`cross-repo-e2e.md`](rules/cross-repo-e2e.md)
Vitaly opera con una arquitectura desacoplada de dos repositorios hermanos:
- **Backend (Este repositorio):** API REST en FastAPI, cliente supabase-py, PostgreSQL/Supabase.
- **Frontend (Repositorio hermano):** Ubicado de forma relativa en `../vitaly-care-for-families` (SPA en React 18 + TypeScript + Vite + Tailwind + TanStack Query).

**Directivas para orquestación End-to-End (E2E):**
1. **Resolución Relativa Estricta:** Resuelve siempre el repositorio hermano mediante `../vitaly-care-for-families` o `$(git rev-parse --show-toplevel)/../vitaly-care-for-families`. Queda **terminantemente prohibido** incluir rutas absolutas del entorno local del desarrollador (`/Users/...`, `C:\...`).
2. **Autoridad de Esquemas:** El backend es la única fuente de la verdad para contratos de datos. Cualquier cambio en esquemas Pydantic (`*Read`, `*Create`) debe coordinarse con las interfaces TypeScript correspondientes en el frontend.
3. **Independencia de Commits:** Cada repositorio gestiona su propio historial de Git. NUNCA mezcles cambios de ambos repositorios en un único commit.

### 7. Base de Datos y Esquemas
- Cambios de esquema: migración en `supabase/migrations/` con confirmación explícita del usuario — [`database_migration_protocol.md`](rules/database_migration_protocol.md).
- Esquemas nuevos con sufijos `*Base`/`*Create`/`*Update`/`*Read`/`*Filter` — [`schema-naming-convention.md`](rules/schema-naming-convention.md).

### 8. Flujo Git
Ramas `<tipo>/GH-<n>` desde `development` (hotfix desde `main`), commits gitmoji Conventional Commits y PRs según `.claude/pr-config.json` — [`branch-naming.md`](rules/branch-naming.md), [`commit-conventions.md`](rules/commit-conventions.md), [`pull-request.md`](rules/pull-request.md). Flujo orquestado en la skill `vitaly-branch-pr`.

---
*Este documento es la ley suprema del backend. Cualquier desviación debe ser justificada por el Backend Architect.*


