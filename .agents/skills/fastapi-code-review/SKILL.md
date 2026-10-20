---
name: fastapi-code-review
description: Verdict-free checklist (gates G1-G8 with evidence and severity) for Vitaly FastAPI code (sync def handlers, supabase-py services, APIResponse envelope, get_current_* gates) covering routing, dependencies, validation, blocking I/O, auth, tenant isolation and contract parity. Use when reviewing files changed under app/api/, app/services/ or app/schemas/, or when invoked by pr-review. Not for a bare PR review request; that is pr-review.
---

# FastAPI Code Review (Vitaly)

Stack facts the review must assume: sync `def` handlers on purpose, shared blocking supabase-py
client (`app/core/database.py`, no ORM, no sessions), Pydantic v2, `APIResponse` envelope
(`app/schemas/responses.py`), global handlers (`app/core/exceptions.py`), role gates in
`app/api/deps.py`. The rules in `.agents/rules/` are the law; cite them in findings.

This is a **verdict-free** checklist: it lists gate failures with evidence and severity, and never
issues CUMPLE/APRUEBO. `pr-review` invokes it as its technical checklist for files under `app/api/`,
`app/services/` and `app/schemas/` and owns the PR verdict; standalone, use it for file review.

## Quick reference

| Area | Reference |
|------|-----------|
| Decorators, response_model, status codes, docs metadata | [references/routes.md](references/routes.md) |
| Depends(), auth gates, shared client | [references/dependencies.md](references/dependencies.md) |
| Pydantic v2 schemas, HTTPException, 422 | [references/validation.md](references/validation.md) |
| sync vs async, blocking I/O | [references/async.md](references/async.md) |

## Vitaly review gates (each failure is a finding)

| # | Gate | Pass condition | Source |
|---|------|----------------|--------|
| G1 | Auth | Route has a `Depends(get_current_*)` gate (handler or `APIRouter(dependencies=...)`) **or** a `# PUBLIC_ROUTE` comment right above the function. No `payload["role"]` checks outside `deps.py`. | `rbac-enforcement.md`, `vitaly-rbac` |
| G2 | Tenant | School-scoped reads/writes resolve `school_id` server-side from `sub` and chain `.eq("school_id", school_id)` or an ownership check. Never `school_id` from body/query/path (except `admin_sistema`). Foreign-school record → 403, missing → 404. | `tenant-isolation.md`, `vitaly-tenant-isolation` |
| G3 | Envelope | `response_model=APIResponse[...]` and `return APIResponse(...)`. No raw dict / `response.data` returns. `APIResponse[dict]` is legacy-tolerated, not for new code. File exports (`StreamingResponse`) are exempt on 200 (`standard-response.md` §2, `export-patterns`). | `standard-response.md`, `standard-api-responses` |
| G4 | Empty vs missing | Empty collection → 200 + `data=[]`. Missing single resource → 404. Mutations check `response.data` before assuming success. | `empty-table-validation.md` |
| G5 | Schema naming | New schemas use `*Base/*Create/*Update/*Read/*Filter`, `Field(description=...)`, no secrets in `*Read`. Legacy `*Response` tolerated. | `schema-naming-convention.md` |
| G6 | Docs (Issue #8) | Endpoints: `summary` + `description` and a docstring stating tenant scope, allowed role, `Raises`. Services: Google-style docstrings. | `CLAUDE.md` §4 |
| G7 | Contract parity | Any added/renamed/removed/nullable-changed field in a `response_model` or payload has a matching change in `../vitaly_frontend/vitaly-care-for-families/src/services`. | `cross-repo-e2e.md`, `vitaly-contracts-parity` |
| G8 | Sync/async | Handlers calling supabase-py (or any blocking I/O) are `def`. `async def` only if every I/O call inside is awaited async. | [references/async.md](references/async.md) |

## Severity mapping

| Gates | Severity | Why |
|-------|----------|-----|
| G1, G2 | `high` | auth / tenant isolation (security, cross-school data leak) |
| G3, G4, G7, G8 | `medium` | contract, envelope, correctness, blocking I/O |
| G5, G6 | `low` | naming / docs (exception: secrets in a `*Read` schema under G5 → `high`) |

## Valid patterns (do NOT flag)

- **Sync `def` handlers and services**: deliberate. FastAPI runs them in a threadpool, so the blocking supabase-py call does not stall the event loop.
- **Gate payload as `dict`** (`admin_payload: dict = Depends(get_current_admin_escuela)`) and `int(payload["sub"])` for the user id.
- **Module-level `supabase` client import** in services: it is the shared client, not an ad-hoc one.
- **`HTTPException` raised from services**: the global handler wraps it into the envelope.
- **Omitting `success=True`**: it is the default.
- **Existing `APIResponse[dict]` / `*Response` schemas** in untouched code: legacy, tolerated by the rules.
- **Pydantic body models without manual checks**: Pydantic already validates; the 422 handler wraps errors.

## Flag these

- `async def` handler or dependency that calls supabase-py, `requests`, `time.sleep`, or file I/O (blocks the loop for every request).
- `return {...}`, `return response.data`, or a route without `response_model`.
- Route with neither a gate nor `# PUBLIC_ROUTE`; inline role checks.
- `school_id` taken from the client; school-scoped query without a school filter.
- 404 on empty lists; `response.data[0]` without an emptiness check.
- `create_client(...)` outside `app/core/database.py`, or raw HTTP calls to `/rest/v1/...`.
- Pydantic v1 APIs in new code (`.dict()`, `orm_mode`, `@validator`, `GenericModel`).
- Bare `except:` / `except Exception: pass` hiding supabase errors.
- Services letting unexpected errors (supabase `APIError`, `ValueError`) escape instead of wrapping them as `HTTPException(500, ...)`: `app/main.py:45-46` only handles `RequestValidationError` and `StarletteHTTPException`, so anything else is a plain 500 without envelope.

## Evidence before reporting

For every finding, anchor `file:line` from the repo (not memory):
1. Decorator line: method, `response_model`, `status_code`, `summary` (or explicitly absent).
2. Handler body range; for blocking claims, `file:line` of each blocking call in an `async def`.
3. Auth claims: search the handler and its `APIRouter(...)` for `Depends(get_current_` and `# PUBLIC_ROUTE`; report paths searched and match count.
4. Validation claims: confirm the argument isn't already a Pydantic model or constrained `Query`/`Path`.
5. Parity claims: name the frontend file/interface checked, or state that the sibling repo is absent.

If a step fails, withdraw the finding, downgrade it, or phrase it as a question.
