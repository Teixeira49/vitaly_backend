---
name: export-patterns
description: FastAPI CSV/Excel export endpoints for Vitaly - StreamingResponse, Content-Type/Content-Disposition headers, CSV injection sanitization, school_id filtering, role gates, mandatory audit entry and streaming for large sets. Trigger: adding or modifying an export, report download or file-generating endpoint.
metadata:
  author: vitaly
  owner: vitaly-backend
  version: "1.0"
  format: agent-skills-v1
---

# Export Patterns (Vitaly, FastAPI)

## Envelope exception

`.agents/rules/standard-response.md` documents an explicit exception for file downloads: they cannot be wrapped in JSON, so exports return a raw `StreamingResponse` on success. Per that rule, declare `response_class=StreamingResponse` plus `responses={200: {"content": {"text/csv": {}}}}` so `/docs` stays honest. **Errors (401/403/404/422) still use the JSON envelope** via the global exception handlers.

## Rules

1. **Role gate** with the existing `get_current_*` dependency from `app/api/deps.py` (see `vitaly-rbac`).
2. **Tenant filter**: `school_id` resolved server-side and applied to every query (see `vitaly-tenant-isolation`). Never accept it from query params for school roles.
3. **Sanitize every cell** (including headers) against CSV/formula injection.
4. **Audit before streaming** with `critical=True` (see `audit-logging`): type, record count, filters.
5. **Sync `def`** handler and service, consistent with the rest of the codebase (blocking supabase-py runs in the threadpool).
6. **No cache** and an attachment filename with a date.
7. Generation logic lives in a service (e.g. `school_admin_export_service.py`); the endpoint only wires HTTP.

## CSV injection

A value starting with `=`, `+`, `-`, `@`, tab (`\t`) or CR (`\r`) can be executed as a formula by Excel/Sheets. Prefix it with `'`. Let the `csv` module handle quoting.

```python
DANGEROUS_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

def sanitize_cell(value: object) -> str:
    text = "" if value is None else str(value)
    return "'" + text if text.startswith(DANGEROUS_PREFIXES) else text
```

## CSV endpoint

Illustrative: `get_school_id`, `school_admin_export_service` and `audit_service` are names to create, not existing code.

```python
import csv, io
from datetime import date
from fastapi.responses import StreamingResponse

def _iter_csv(header: list[str], rows):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([sanitize_cell(h) for h in header])
    yield "\ufeff" + buf.getvalue()  # BOM so Excel reads UTF-8 accents
    for row in rows:
        buf.seek(0); buf.truncate(0)
        writer.writerow([sanitize_cell(v) for v in row])
        yield buf.getvalue()

@router.get("/students/export", response_class=StreamingResponse,
            summary="Export students (CSV)",
            responses={200: {"content": {"text/csv": {}}}})
def export_students(current_user: dict = Depends(get_current_admin_escuela)):
    """Export the school's students as CSV. Scoped by school_id; admin_escuela only.

    Raises:
        HTTPException: 401/403 from the gate; 500 if the audit insert fails.
    """
    school_id = school_admin_service.get_school_id(current_user["sub"])
    rows = school_admin_export_service.iter_students(school_id)  # paginated generator
    audit_service.record(actor=current_user, action="export", entity="student",
                         entity_id="*", school_id=school_id,
                         metadata={"export_type": "students_csv"}, critical=True)
    filename = f"students_{date.today().isoformat()}.csv"
    return StreamingResponse(
        _iter_csv(["ID", "Name", "Grade"], rows),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Cache-Control": "no-store"},
    )
```

If an exact `record_count` is required in the audit row, count first (`select("id", count="exact")`) with the same filters.

## Excel (.xlsx)

- Media type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- Use `openpyxl` with `Workbook(write_only=True)` for large sets, save to `io.BytesIO`, and return it through `StreamingResponse`. Adding the dependency is a `build` change: declare it in the PR.
- Sanitize string cells the same way (formulas in xlsx are just as dangerous).

## Large datasets

- Page through supabase-py with `.range(start, end)` (e.g. 1000 rows per page) inside a generator; never `select("*")` the whole table into memory.
- Select only the exported columns; never export PHR fields unless the feature explicitly requires them and the role is allowed.

## Anti-patterns

- Building the whole file in memory for unbounded tables.
- Writing raw values without `sanitize_cell`.
- Missing `Cache-Control: no-store` on health data.
- Accepting `school_id` from the client, or skipping the audit entry.
- `async def` handlers calling blocking supabase-py.

## Checklist

- [ ] `get_current_*` gate and server-side `school_id` filter.
- [ ] Every cell and header goes through `sanitize_cell`.
- [ ] `Content-Type`, `Content-Disposition` (dated filename) and `Cache-Control: no-store` set.
- [ ] Audit recorded with `critical=True` before streaming.
- [ ] Paginated generator for large sets; only required columns.
- [ ] Endpoint follows the file-download exception in `standard-response.md` (`response_class` + `responses={200: {"content": ...}}`).
- [ ] Tests: role matrix, tenant isolation, injection payload (`=1+1`) is prefixed (see `vitaly-feature-testing`).

## References

- Rule `.agents/rules/standard-response.md` — explicit envelope exception for file downloads and OpenAPI declarations.
- Skill `vitaly-tenant-isolation` — server-side `school_id` resolution from token `sub`.
- Skill `vitaly-rbac` — role gates using `Depends(get_current_*)`.
- Skill `audit-logging` — audit entry schema, sensitivity handling, and recording before streaming.
- Skill `fastapi-code-review` — sync `def` handlers to avoid event loop blocking with `supabase-py`.
