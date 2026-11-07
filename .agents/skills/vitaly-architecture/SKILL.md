---
name: vitaly-architecture
description: "Vitaly backend layering as it really is (endpoints -> module-level service singletons -> global supabase-py client), dependency direction, the school_admin_service.py god-file rule, the tolerated-legacy inventory and the Boy Scout rule for migrating legacy code. Trigger: deciding where code belongs, adding a layer or abstraction, refactoring or splitting a service, touching legacy endpoints/schemas, or proposing repositories, hexagonal/clean architecture, async handlers or an ORM."
---

# Vitaly architecture — the real layering

**Source of truth:** `.agents/rules/*.md` and the root `CLAUDE.md`. To create a new feature,
follow `vitaly-module-scaffold`. This skill says what goes where and what NOT to build.

## Layers and dependency direction

```
app/api/v1/endpoints/<role>_<feature>.py   (sync def, Depends(get_current_<role>))
        │ imports singleton
        ▼
app/services/<role>_<feature>_service.py   (class + `x_service = XService()`)
        │ imports
        ▼
app/core/database.py → global `supabase` client (supabase-py, sync)

app/schemas/*.py      ← imported by endpoints and services; imports nothing from them
app/api/deps.py       ← role gates, used only by endpoints
app/core/exceptions.py← turns HTTPException / validation errors into the APIResponse envelope
```

Hard rules:

- Endpoints MUST NOT import `supabase` in new code. All data access goes through a service.
- Services MUST NOT import `app.api.*` (no deps, no routers). They receive plain `user_id`/values.
- Schemas MUST NOT import services or endpoints.
- Services are module singletons imported directly; never injected with `Depends`.
- Handlers are sync `def`: supabase-py is blocking, and FastAPI runs `def` in a threadpool.
- Services are a class + module singleton. `profile_photo_service.py` (module-level functions)
  is tolerated legacy; do not copy it.
- `school_id` resolution is shared: target `app/services/tenancy.py` (module-level functions, e.g.
  `get_school_id_for_admin(user_id) -> int`, 403 if unlinked). It does not exist yet; until it
  does, reuse `SchoolAdminService._get_school_id_for_admin` (`school_admin_service.py:37`) instead
  of copying the query, and move that logic into `tenancy.py` when you create it.

## Why services may raise HTTPException

It is the project convention: `app/core/exceptions.py` converts every `HTTPException` into the
`APIResponse` error envelope, so a service raising 403/404 yields a consistent response with no
translation layer. It couples services to FastAPI; that tradeoff is accepted while FastAPI is
the only entry point. Do not introduce a parallel domain-exception hierarchy.

`app/main.py:45-46` registers handlers only for `RequestValidationError` and
`StarletteHTTPException`: any other exception (e.g. supabase `APIError`) yields a plain 500
without the envelope. Wrap unexpected errors as `HTTPException(500, ...)` in the service
(existing pattern: `app/api/v1/endpoints/academic_year.py:40-41`).

## God-file rule

`app/services/school_admin_service.py` (~2000 lines) is closed for growth.

- NO new public methods there. A new school-admin feature gets its own
  `app/services/school_admin_<feature>_service.py` (precedent: `school_admin_event_service.py`).
- Bug fixes inside it are fine. Extracting a cohesive group of methods into its own service is a
  refactor: its own commit, its own PR if large.

## Tolerated legacy (do not copy into new code)

| Legacy pattern | Where | New code uses |
|---|---|---|
| `*Response` / `*Request` schema names | `app/schemas/*` | `*Read` / `*Create` / `*Update` |
| `response_model=APIResponse[dict]` | many endpoints | `APIResponse[XRead]` |
| `# PUBLIC_ROUTE` inside the docstring | `catalogs.py` | comment above the decorator stack |
| Endpoint querying `supabase` directly | `catalogs.py`, `school.py`, `academic_year.py`, `parent.py` | a service method |
| Per-service duplicate school_id helpers | `school_admin_service.py:37`, `school_admin_event_service.py:13` (`_get_admin_record`) | shared helper in `app/services/tenancy.py` (target; reuse `_get_school_id_for_admin` until it exists) |
| Module-level functions instead of class + singleton | `profile_photo_service.py` | class + `x_service = XService()` |
| `async def` handler calling blocking supabase | `app/main.py:56` (`/health`), `:73` (`/health-visual`) | sync `def` |
| Public route with no marker at all | `school.py:9`, `auth.py` register/login, `main.py` `/`, `/health`, `/health-visual` | `# PUBLIC_ROUTE` comment above the decorator |
| Mutating route with no gate and no marker | `academic_year.py:9` (POST), `:43` (PATCH `/sync-current`) | a `get_current_*` gate (likely `admin_sistema`; confirm with the user) |

## Boy Scout rule (touching legacy)

Before editing legacy code, evaluate migration eligibility. Migrate ONLY IF all hold:

1. The function is < 50 lines.
2. It is isolated (no callers or helpers that would have to change with it).
3. Any schema rename (`*Response` → `*Read`) is coordinated with the frontend DTOs
   (`vitaly-contracts-parity`). Renames change the OpenAPI contract.

Otherwise leave a marker and ship only the fix:

```python
# TODO: [TECH-DEBT] move supabase query to school_service - blocked by: shared helper in parent.py
```

- The fix goes in its own commit FIRST; the migration in a separate `♻️ refactor` commit.
  The fix never waits for the migration.
- If the migration would push the PR over 400 changed lines, defer it (see `vitaly-chained-pr`).
- Hotfix under time pressure: TODO marker only, no migration.

## Anti-patterns — do NOT introduce

- ❌ Repository classes or a `repositories/` folder wrapping supabase calls.
- ❌ Ports/adapters, or `domain/` / `application/` / `infrastructure/` layers.
- ❌ `async def` handlers or services calling blocking supabase-py (blocks the event loop).
- ❌ An ORM, `app/models/`, or SQLAlchemy sessions. Only after an explicit, approved migration
  decision; `sqlalchemy-postgres` and `sqlalchemy-code-review` are parked in `.agents/future-skills/` for that future scenario.
- ❌ Injecting services with `Depends(...)` or creating them per request.
- ❌ Inline role checks in handlers (use `vitaly-rbac`) or trusting a client `school_id`
  (use `vitaly-tenant-isolation`).
- ❌ New methods in `school_admin_service.py`.
