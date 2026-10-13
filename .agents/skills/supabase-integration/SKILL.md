---
name: supabase-integration
description: "How Vitaly talks to Supabase: the shared sync supabase-py client from app/core/database.py, select/eq/execute().data queries filtered by school_id, count='exact' + range() pagination, insert/update returning .data, empty-result handling, no multi-table transactions (use a Postgres function via .rpc() if atomicity is needed), and SQL migrations in supabase/migrations/ under the migration protocol. Trigger: writing or reviewing a supabase.table(...) query in app/services/, adding a table, column, index, RLS policy or migration, or asking about pagination, transactions or connection setup."
---

# Supabase integration (Vitaly)

Vitaly uses **Supabase Postgres through the supabase-py REST client**. There is no ORM, no
SQLAlchemy session, no async client and no direct Postgres connection in the backend. All data
access goes through one shared client, from the service layer.

Related law and skills:
- Tenancy (`school_id` resolution, foreign row 403): `vitaly-tenant-isolation` + rule `tenant-isolation.md`.
- Schema changes: rule `database_migration_protocol.md` (report + explicit human confirmation).
- Empty results: rule `empty-table-validation.md` (single row 404, collection 200 + `[]`).
- Layering (endpoints → service singletons → client): `vitaly-architecture`.

## 1. The shared client

```python
# app/core/database.py (exists; do not duplicate)
supabase = get_supabase_client()   # create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# In a service module
from app.core.database import supabase
```

- Import the global `supabase` in **services only**; endpoints call the service singleton.
- Never call `create_client` elsewhere, never build a per-request client, never add `acreate_client`
  / async handlers: handlers are sync `def` and FastAPI runs them in a threadpool.
- `SUPABASE_KEY` is backend-only. If it is the service-role key, it bypasses RLS, so the
  explicit `school_id` filter is the real protection. Never expose it to the frontend.
- Tests patch it where it is used: `patch("app.services.<module>.supabase")` (see `vitaly-feature-testing`).

## 2. Reading

```python
response = (
    supabase.table("classroom")
    .select("id, category, level, section, academic_year_id")   # explicit columns, not "*"
    .eq("school_id", school_id)                                 # tenant filter, always
    .eq("is_deleted", False)                                    # soft-delete flag
    .order("category")
    .execute()
)
rows = response.data            # list[dict], [] when nothing matches (never None in practice)
```

- `school_id` comes from the server-side resolver, never from the request. Target: module function
  `get_school_id_for_admin(user_id)` in `app/services/tenancy.py` (403 if unlinked; not created yet).
  Until then reuse `SchoolAdminService._get_school_id_for_admin` (`school_admin_service.py:37`);
  never copy the query into another service.
- Select only the columns the schema returns; never select `password` or internal fields such as
  `photo_file_id` into a response.
- Embedded relations use PostgREST syntax in `select` (e.g. `"*, user(*)"`), as in `doctor_service`.
- Filters available on the builder: `eq`, `neq`, `in_`, `is_("end_date", "null")`, `gte`, `lte`,
  `ilike`, `order(col, desc=True)`, `limit`, `range`.

### Empty results

```python
# Single resource: look up by id, then check ownership (tenant standard)
res = supabase.table("classroom").select("id, school_id").eq("id", classroom_id).execute()
if not res.data:
    raise HTTPException(status_code=404, detail=f"No existe ningún salón con ID {classroom_id}.")
if res.data[0]["school_id"] != school_id:
    raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este salón: pertenece a otra escuela.")
row = res.data[0]

# Collection: empty is a valid answer (never raise 404 for an empty list)
return []                                                     # paginated legacy: {"data": [], "total": 0, ...}
```

Never index `response.data[0]` before checking it is non-empty (that is the silent 500).

## 3. Pagination: `count="exact"` + `.range()`

Pattern from `app/services/school_admin_event_service.py`. The nested
`{"data", "total", "page", "size"}` dict it returns (also `admin_service.py:25-31`) is **tolerated
legacy**: new paginated endpoints return `(rows, total)` and the endpoint builds
`meta=PaginationMeta(...)`. Migrating existing ones requires coordinating the frontend via
`vitaly-contracts-parity`.

```python
count_res = (
    supabase.table("event")
    .select("id", count="exact")          # count travels in response.count
    .in_("id", event_ids)
    .eq("is_deleted", False)
    .execute()
)
total = count_res.count or 0
if total == 0:
    return {"data": [], "total": 0, "page": page, "size": size}   # legacy shape

offset = (page - 1) * size
page_res = (
    supabase.table("event")
    .select("id, title, description, init_time, ent_time, created_at")
    .in_("id", event_ids)
    .eq("is_deleted", False)
    .order("init_time", desc=True)        # stable order before range
    .range(offset, offset + size - 1)     # inclusive bounds
    .execute()
)
return {"data": page_res.data, "total": total, "page": page, "size": size}   # legacy shape
```

- `page`/`size` are validated in the endpoint with `Query(1, ge=1)` / `Query(20, ge=1, le=100)`.
- Apply the **same filters** to the count query and the page query, or totals drift.
- Always `.order(...)` before `.range(...)`; unordered pages can repeat or skip rows.
- Envelope `meta` (`PaginationMeta`) is the target for **new** endpoints only; the nested dict above is
  legacy. See `standard-api-responses`.

## 4. Writing

```python
# Insert: returns the inserted rows in .data
created = supabase.table("event").insert({**payload, "school_id": school_id}).execute()
if not created.data:
    raise HTTPException(status_code=500, detail="No se pudo crear el evento.")
event = created.data[0]

# Update: check existence/ownership first (404/403), then filter by id AND school_id
updated = (
    supabase.table("classroom")
    .update({"section": "B"})
    .eq("id", classroom_id)
    .eq("school_id", school_id)
    .execute()
)
if not updated.data:                       # zero rows matched
    raise HTTPException(status_code=404, detail="Recurso no encontrado")
```

- Set `school_id` (and any owner column) from the server-resolved value, never from the payload.
- Convert `date`/`datetime` to ISO strings before sending (`value.isoformat()`); supabase-py
  serializes JSON, not Python dates.
- A failed `.execute()` (constraint violation, bad column, network) raises postgrest `APIError`,
  which no global handler covers (`app/main.py:45-46` only registers `RequestValidationError` and
  `StarletteHTTPException`): it becomes a plain 500 without the `APIResponse` envelope. Wrap
  unexpected errors in the service as `HTTPException(status_code=500, detail="...")`.
- Deletion is **soft** in this codebase (`is_deleted` / `is_canceled` flags via `.update(...)`);
  reads filter `.eq("is_deleted", False)`. Use hard `.delete()` only when the domain requires it,
  and filter it by id and `school_id`.

## 5. No multi-table transactions

supabase-py sends one HTTP request per `.execute()`; there is no `BEGIN/COMMIT` across calls.
A sequence of inserts can partially fail. Real example: registration in `auth_service`
(`_create_base_user` inserts `user` then `user_roles`; `register_*` then inserts the role table) —
a failure in step 2 or 3 leaves an orphan `user`.

When an operation must be atomic across 2+ tables:

1. Write a Postgres function (`plpgsql`) that does all the writes; a function body runs in a
   single transaction and rolls back on error.
2. Ship it as a migration (section 7).
3. Call it from the service with `supabase.rpc("fn_name", {"p_school_id": school_id, ...}).execute()`
   and read `.data`.
4. Pass `school_id` from the server as an argument; do not let the function trust client input.

Status: **no `.rpc()` call exists in `app/` today**. Until a function exists, order writes so the
least harmful partial state comes first and compensate on failure (delete/flag what was already
written), and say so in the PR. Do not reach for `db.transaction()`-style patterns: this stack has
no transaction object; the `.rpc()` Postgres function is the only atomic path.

## 6. RLS and connections

- RLS: no table in `supabase/migrations/` enables RLS today, and a service-role key bypasses it.
  Treat RLS as optional defense in depth; design and rollout live in `vitaly-tenant-isolation`.
  If added, policies need both `USING` and `WITH CHECK`, and the explicit `.eq("school_id", ...)`
  stays.
- Connections: the REST client talks HTTPS to PostgREST; Supabase pools the Postgres side. There
  is no connection string, Supavisor port or pool size to tune in the backend. If a direct
  Postgres connection is ever introduced (reports, batch jobs), that is an architecture decision
  for `vitaly-architecture`, not a local change.

## 7. Migrations

- Location: `supabase/migrations/`, file name `YYYYMMDDHHMMSS_short_description.sql`
  (e.g. `20261009000000_add_user_photo_file_id.sql`). Timestamps must be increasing.
- Make DDL idempotent where possible: `ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`,
  `CREATE OR REPLACE FUNCTION`. Quote reserved table names (`public."user"`).
- New school-scoped table: `school_id` column `NOT NULL` with FK to `public.school(sch_id)` and an
  index on `school_id` (plus soft-delete flag `is_deleted boolean NOT NULL DEFAULT false` to match
  the codebase).
- Comment the intent at the top of the file and flag internal-only columns.
- **Never apply** (`supabase db push`, `apply_migration`, `execute_sql`, any DDL) without the report
  and explicit user confirmation required by `database_migration_protocol.md`. Writing the `.sql`
  file is fine; running it is not, until approved. Read-only `SELECT` checks are allowed.
- After a schema change, update the Pydantic schemas and the frontend DTOs (`vitaly-contracts-parity`).

## Red flags

- `create_client(...)` outside `app/core/database.py`, or an async client.
- `supabase.table(...)` in an endpoint instead of a service.
- A school-scoped query without `.eq("school_id", ...)` or an ownership check.
- `response.data[0]` without a prior emptiness check.
- 404 raised for an empty list.
- Count and page queries with different filters, or `.range()` without `.order()`.
- Several dependent inserts with no compensation and no `.rpc()` function.
- A migration applied without the protocol report and confirmation.
- SQLAlchemy, Alembic or `pgvector` snippets: none of these exist in this repo.
