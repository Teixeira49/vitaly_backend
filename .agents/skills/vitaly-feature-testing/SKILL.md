---
name: vitaly-feature-testing
description: "Pytest suites for Vitaly features (FastAPI TestClient + mocked supabase-py): APIResponse envelope, tenant isolation by server-resolved school_id (foreign row 403, missing row 404, empty list 200 + []), RBAC matrix via get_current_* overrides (wrong role 403, bad/revoked token 401) and 422 validation. Trigger: creating or modifying an endpoint in app/api/, a service in app/services/, or writing tests in tests/."
---

# Vitaly Feature Testing

How to test a Vitaly feature against the code as it really is: sync `def` handlers, module-level
service singletons, the global supabase-py client (`app/core/database.py`), the `APIResponse`
envelope and the `get_current_*` gates in `app/api/deps.py`.

**Runnable reference:** `examples/template_feature_test.py` targets the real endpoint
`GET /api/v1/school-admin/classrooms/{classroom_id}/students`. Copy it to `tests/test_<feature>.py`
and adapt. Pre-PR checklist: `resources/test_matrix_checklist.md`.

## When to use

- Implementing or changing an endpoint in `app/api/` or a service in `app/services/`.
- Writing `tests/test_<feature>.py` (tests live with the code, see `work-unit-commits`).
- Before opening a PR, to cover envelope, tenancy and RBAC.

Not here: the guard test that fails on any ungated route lives in `vitaly-rbac`
(`tests/api/test_route_protection.py`). Envelope details: `standard-api-responses`.

## Facts the tests depend on (verified in app/)

| Fact | Where |
|---|---|
| No `get_current_user`, no `RoleChecker`, no `current_user` object. Gates: `get_current_user_token`, `get_current_admin_sistema`, `get_current_admin_escuela`, `get_current_doctor`, `get_current_representante`; each returns the JWT payload `dict`. | `app/api/deps.py` |
| Payload claims: `sub` (user id as **string**), `email`, `role`, `name`, `gender`, plus role extras (`administrative_position`, `school` name for admin_escuela; `especially`, `doc_license_number` for doctor; `type_representative` for representante). **No `school_id` claim.** | `app/services/auth_service.py` (login) |
| Role values: `admin_sistema`, `admin_escuela`, `doctor`, `representante`. | `app/schemas/enums.py` (`UserRole`) |
| Tenant column is `school_id` (table `school` PK `sch_id`). For admin_escuela it is resolved by `SchoolAdminService._get_school_id_for_admin(user_id)` (403 if unlinked). | `app/services/school_admin_service.py` |
| Services import the client as `from app.core.database import supabase`, so patch it **where it is used**: `patch("app.services.<module>.supabase")`. | each service |
| `HTTPException` and 422 are rewritten by global handlers: error bodies are `{"success": false, "message": ..., "errors": ...}`. There is **no** `detail` key in responses. | `app/core/exceptions.py` |
| Bad JWT or revoked token (`auth_service.is_token_revoked`) → 401; wrong role → 403. | `app/api/deps.py` |

## The 5 laws

| # | Dimension | Expected | How to assert |
|---|---|---|---|
| 1 | Envelope | Every response is `APIResponse` | `success`, `message`, `data` on 2xx; `success is False` + `message` on errors |
| 2 | Tenancy | `school_id` resolved server-side, never from the client | Service resolver called with the token `sub`; filter `.eq("school_id", ...)` called; **foreign row → 403** |
| 3 | Deterministic mocks | No network, no real Supabase | `patch("app.services.<module>.supabase")` + chainable query mock |
| 4 | Empty / missing | Never a silent 500 | **Missing single row → 404**; **empty collection → 200 + `data=[]`** (never 404) |
| 5 | RBAC | Gates in `Depends`, not inline | Allowed role 2xx, **wrong role 403**, **invalid/revoked token 401** |

Law 1 limit: `app/main.py:45-46` registers handlers only for `RequestValidationError` and
`StarletteHTTPException`. Any other exception (e.g. a raw supabase/postgrest error) becomes a
plain 500 **without** the envelope, and `TestClient` (default `raise_server_exceptions=True`)
re-raises it inside the test. Services must wrap unexpected errors as `HTTPException(500, ...)`.

Status code standard (rule `tenant-isolation.md`, directive 5): row does not exist → 404; row
exists in another school → 403. A test that accepts "404 or 403" is wrong.

## Minimum test matrix per feature

1. `test_<feature>_success` — happy path, status 200/201, envelope, service called with `user_id=int(sub)`.
2. `test_<feature>_tenant_*` — resolver used, `school_id` filter applied, foreign-school row → 403.
3. `test_<feature>_missing_returns_404` — single resource lookup returns `data=[]` → 404.
4. `test_<feature>_empty_returns_empty_list` — collection with no rows → 200 + `data=[]`.
5. `test_<feature>_wrong_role_403`, `_invalid_token_401`, `_revoked_token_401`.
6. `test_<feature>_invalid_input_422` — bad path/query/body → 422 with `errors`.
7. `test_<feature>_unexpected_error_500` — supabase mock raises (`execute.side_effect = Exception(...)`);
   the service wraps it as `HTTPException(500)` → assert 500 + `success is False` envelope.

Test at the cheapest layer that proves the point: endpoint tests patch the **service method**
(`patch.object(service, "method", ...)`); tenancy/empty/404/403 logic is tested on the
**service** with supabase mocked.

## Patterns

### Authenticate: override the gate with a realistic payload

```python
from app.api.deps import get_current_admin_escuela, get_current_user_token
from app.main import app

def admin_payload(user_id: int = 4) -> dict:
    return {"sub": str(user_id), "email": "admin@colegio.test", "role": "admin_escuela",
            "name": "Laura Pérez", "gender": "FEMENINO",
            "administrative_position": "Coordinadora", "school": "Colegio San Ignacio"}

@pytest.fixture
def admin_client():                      # same shape as tests/test_profile_photo.py
    app.dependency_overrides[get_current_admin_escuela] = lambda: admin_payload()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
```

- To test the **gate itself** (wrong role → 403), override `get_current_user_token`, not the
  role gate, so `get_current_<role>` really runs:
  `app.dependency_overrides[get_current_user_token] = lambda: {"sub": "30", "role": "representante"}`.
- 401 without overrides: send `Bearer not-a-jwt` (decode fails), or sign a real token with
  `app.core.security.create_access_token` and `patch.object(auth_service, "is_token_revoked", return_value=True)`.
- Missing `Authorization` header → 401. Guaranteed by the pinned `fastapi[standard]>=0.122.0`
  (`requirements.txt`): security classes such as `HTTPBearer` return 401 since 0.122.0.

### Tenant: patch the resolver, mock the supabase chain

```python
from unittest.mock import MagicMock, patch
from app.services.school_admin_service import school_admin_service

def make_query(data=None, count=None):
    q = MagicMock()
    for m in ("select", "eq", "neq", "in_", "is_", "ilike", "gte", "lte",
              "order", "range", "limit", "insert", "update", "delete"):
        getattr(q, m).return_value = q          # any chain length ends in the same execute()
    q.execute.return_value = MagicMock(data=[] if data is None else data, count=count)
    return q

def test_foreign_school_row_returns_403():
    classroom = make_query([{"id": 7, "school_id": 2}])        # row of ANOTHER school
    with patch.object(school_admin_service, "_get_school_id_for_admin", return_value=1), \
         patch("app.services.school_admin_service.supabase") as sb:
        sb.table.side_effect = lambda name: {"classroom": classroom}[name]
        with pytest.raises(HTTPException) as exc:
            school_admin_service.get_students_by_classroom(user_id=4, classroom_id=7, page=1, size=20)
    assert exc.value.status_code == 403
```

- Dispatch `supabase.table(name)` per table with `side_effect`; an unexpected table raises
  `KeyError`, which exposes unplanned queries.
- For directly scoped queries assert the filter: `classroom.eq.assert_any_call("school_id", 1)`.
- Where to patch the resolver: once the shared `app/services/tenancy.py`
  `get_school_id_for_admin(user_id)` exists, patch it **where it is imported**
  (`patch("app.services.<module>.get_school_id_for_admin")`). Until then patch the method
  `_get_school_id_for_admin` (`school_admin_service.py:37`). `school_admin_event_service.py:13`
  has a duplicate, `_get_admin_record` (returns `sch_admin_id` + `school_id`); patch that one there.
- If you patch `supabase` but not the resolver, `_get_school_id_for_admin` reads the
  `school_administrator` table from your mock; route it or patch the resolver.
- Doctor/representante scopes resolve through `doctor_to_school` / `parent` +
  `student_representative`: mock those tables the same way (see `vitaly-tenant-isolation`).

### Assert error bodies through the envelope

```python
assert response.status_code == 404
assert response.json()["success"] is False
assert "no existe" in response.json()["message"].lower()   # not response.json()["detail"]
```

Service-level tests catch the raw exception instead:
`with pytest.raises(HTTPException) as exc: ...; assert exc.value.status_code == 404`.

## Legacy code vs the standard

Some services still answer an **empty collection with 404** (e.g. `get_students_by_classroom`,
`get_academic_grades`). Do not write a test that enshrines it. Either fix the service (Boy Scout
rule, `vitaly-architecture`) or mark the standard test
`@pytest.mark.xfail(strict=True, reason="legacy 404 on empty list")` so it flips red when fixed
(the example does this).

## Mocks do not prove isolation

A `MagicMock` client returns what you give it; it proves the filter was **called**, not that
data cannot leak. Real isolation (and any RLS policy) needs a test against a real
Postgres/Supabase with two schools (see `vitaly-tenant-isolation`).

## Run

```bash
pip install -r requirements-dev.txt # pytest lives here, not in requirements.txt
pytest                              # pytest.ini: pythonpath=., testpaths=tests
pytest tests/test_<feature>.py -v
pytest tests/test_<feature>.py -x
```

Importing `app.main` builds the global supabase client from settings, so `SUPABASE_URL` and
`SUPABASE_KEY` must be set (`.env`); no request is made until a query executes.
