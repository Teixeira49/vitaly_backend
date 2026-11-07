# Dependencies

Vitaly has no DB-session dependency: data access goes through the shared supabase-py client
(`from app.core.database import supabase`) inside services. `Depends()` is used for auth.

## 1. Auth gates come from `app/api/deps.py`

| Dependency | Allows |
|------------|--------|
| `get_current_user_token` | any valid, non-revoked JWT |
| `get_current_admin_sistema` | `UserRole.ADMIN_SISTEMA` |
| `get_current_admin_escuela` | `UserRole.ADMIN_ESCUELA` |
| `get_current_doctor` | `UserRole.DOCTOR` |
| `get_current_representante` | `UserRole.REPRESENTANTE` |

All return the decoded payload `dict`; the user id is `int(payload["sub"])`.

```python
# BAD - inline role check
def delete_student(student_id: int, payload: dict = Depends(get_current_user_token)):
    if payload.get("role") != UserRole.ADMIN_ESCUELA.value:
        raise HTTPException(status_code=403, detail="...")

# GOOD - narrowest gate
def delete_student(student_id: int, admin_payload: dict = Depends(get_current_admin_escuela)): ...
```

Multi-role routes: add a composed gate in `deps.py` on top of `get_current_user_token`; never resolve roles in the handler. Details: `vitaly-rbac`.

## 2. Router-level gates

When a whole module shares a role, apply it once:

```python
router = APIRouter(dependencies=[Depends(get_current_admin_sistema)])
```

Handlers that need `sub` still inject the payload.

## 3. Don't call dependencies manually

Never call `get_current_user_token(...)` inside a handler; declare it with `Depends()` so FastAPI resolves, caches per request, and documents it in OpenAPI.

## 4. Data access belongs in services, not dependencies

- No `create_client(...)` outside `app/core/database.py`; no raw HTTP to `/rest/v1/...`.
- New code queries in `app/services/`, not in handlers (legacy `catalogs.py` queries directly; don't copy it).
- Tenant resolution (`school_id` from `sub`) happens in the service. Target: `get_school_id_for_admin(user_id)` in `app/services/tenancy.py` (403 if unlinked; not created yet); until then reuse `SchoolAdminService._get_school_id_for_admin` (`app/services/school_admin_service.py:37`). Never copy the query. See `vitaly-tenant-isolation`.

## 5. Dependencies are sync

Gates are `def` (they call `auth_service.is_token_revoked`, which queries `token_blacklist` via supabase-py). Don't convert them to `async def` (see `async.md`).

## 6. No shared mutable state

Module-level dicts used as caches across requests are race-prone and per-process; use a real cache or nothing.

## Review questions

1. Does every protected route use the narrowest `get_current_*` gate?
2. Any `payload["role"]` comparisons outside `deps.py`?
3. Any ad-hoc Supabase clients or queries in handlers for new code?
4. Is `school_id` derived server-side in the service?
