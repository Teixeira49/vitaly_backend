---
name: vitaly-tenant-isolation
description: "Vitaly multi-tenant isolation by school: derive school_id server-side from the authenticated user, filter every supabase-py query by it, and treat Supabase RLS as optional defense in depth. Trigger: creating or modifying a service in app/services/, an endpoint that reads or writes school-scoped data, a table or migration in supabase/migrations/, or discussing escuela_id, school_id, tenants, RLS or data leaks between schools."
---

# Vitaly tenant isolation — one school never sees another

**Source of truth:** `.agents/rules/tenant-isolation.md` (the law). This skill is the how-to
for the current code (FastAPI + supabase-py, no ORM).

A leak of student health data between schools is the worst incident this product can have.
Isolation rests on layers, so one forgotten line is not enough to cause harm:

```
1. Context  school_id is resolved server-side from the JWT `sub`, never from the client
2. Filter   every supabase query on school-scoped data adds .eq("school_id", school_id)
3. RLS      (not active today) Postgres would reject the row even if the filter is missing
```

## 1. Where the tenant comes from

The JWT has **no** school id claim. Services resolve it from the authenticated user id:

```python
user_id = int(admin_payload["sub"])                        # from get_current_admin_escuela
school_id = get_school_id_for_admin(user_id)              # school_administrator.school_id, 403 if unlinked
```

Resolution is a shared helper, not a private one per service. Target: `app/services/tenancy.py`
(module-level functions such as `get_school_id_for_admin(user_id: int) -> int`). It does not exist
yet: until it does, reuse `SchoolAdminService._get_school_id_for_admin`
(`school_admin_service.py:37`) instead of copying the query; when you create `tenancy.py`, move
that logic there (Boy Scout). `school_admin_event_service.py:13` `_get_admin_record` is a known
duplicate to migrate. For doctors the scope is `doctor_to_school`; for representantes it is
`student_representative` (see `vitaly-rbac`, ownership checks).

Never accept the tenant from outside:

```python
# Bad: client picks the school
def list_students(school_id: int = Query(...)): ...
payload.school_id  # trusted from body

# Good: client does not participate
def list_students(admin_payload: dict = Depends(get_current_admin_escuela)):
    return service.list_students(user_id=int(admin_payload["sub"]))
```

Exception: `admin_sistema` endpoints under `/admin/schools` legitimately take a `school_id` path
param, because that role audits all schools. Only behind `get_current_admin_sistema`.

## 2. Filter every query

```python
supabase.table("classroom").select("id, level, section").eq("school_id", school_id).execute()
```

- Reads, updates and deletes on school-scoped tables chain `.eq("school_id", school_id)`.
- For rows that reach the school indirectly (student → classroom_registration → classroom),
  fetch the parent row and compare: `if cr["school_id"] != school_id: raise HTTPException(403, ...)`
  (pattern used in `get_student_detail`, `get_students_by_classroom`).
- On writes, set `school_id` from the resolved value, never from the payload.
- Global catalogs (`states`, `school_type`, `classroom_category`, `system_status`,
  `academic_year`) are not school-scoped and correctly have no `school_id` filter.
- Mutations: check first, then mutate. Fetch the row by id (404 if absent), compare its
  `school_id` (403 if foreign), then run the update/delete with **both** `.eq("id", ...)` and
  `.eq("school_id", school_id)` as a second line of defense.

### Status code standard: foreign row = 403, missing row = 404

Project decision, applies to every module (rule `tenant-isolation.md`, directive 5):

| Situation | Response |
|---|---|
| Row id does not exist (or is soft-deleted) | `404` — `HTTPException(status_code=404, detail="... no existe")` |
| Row exists but belongs to another school | `403` — `HTTPException(status_code=403, detail="... pertenece a otra escuela.")` |
| User not linked to any school (`get_school_id_for_admin`) | `403` |
| Collection with no rows for this school | `200` + `data=[]` (never 404) |

```python
row = supabase.table("classroom").select("id, school_id").eq("id", classroom_id).execute().data
if not row:
    raise HTTPException(status_code=404, detail=f"No existe ningún salón con ID {classroom_id}.")
if row[0]["school_id"] != school_id:
    raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este salón: pertenece a otra escuela.")
```

Do not collapse both cases into a single `.eq("id", ...).eq("school_id", ...)` lookup that
returns 404: it hides the 403 the standard requires. A combined filter is fine for the mutation
itself, after the check.

## 3. RLS: defense in depth (recommended, not present)

Honest status: `supabase/migrations/` contains no `ENABLE ROW LEVEL SECURITY` or policies, and
the backend client is created from `settings.SUPABASE_KEY`. If that key is the service-role key,
RLS is **bypassed** anyway. Today layers 1 and 2 are the only protection.

If the team adopts RLS, it must go through `.agents/rules/database_migration_protocol.md`
(report + explicit user confirmation before applying). Key points to carry over:

- Policies only protect when the backend uses a key/role that RLS applies to (anon/authenticated
  with a JWT carrying the school claim), not the service role.
- Add both `USING` (reads) and `WITH CHECK` (writes); without `WITH CHECK` a row can be inserted
  into another school.
- A missing tenant setting must yield zero rows, not an error and not all rows.
- Keep the explicit `.eq("school_id", ...)` filter even with RLS; RLS is the net, not the line.

## How to verify

- Service tests: assert the mocked query chain received `.eq("school_id", <resolved id>)`, and
  that a foreign-school row produces 403 and a missing row 404 (see `vitaly-feature-testing`).
- **Mocks do not prove isolation.** A `MagicMock` supabase client returns whatever you tell it;
  it only proves the filter was *called*. Real isolation (and any RLS policy) needs a test against
  a real Postgres/Supabase instance with two schools: user of school A must get zero rows of B.
- Read-only check for RLS state (allowed without confirmation):
  `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname = '<table>';`

## Red flags

- `school_id` read from query, path or body on a non-`admin_sistema` route.
- A `supabase.table(...)` call on a school-scoped table with no `school_id` filter or ownership check.
- A new school-scoped table without a `school_id` column (and index) in its migration.
- A test claiming "isolation verified" that only uses mocks.
- A foreign-school row answered with 404 (standard is 403), or a missing row answered with 403.
