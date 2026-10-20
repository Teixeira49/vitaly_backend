---
name: vitaly-rbac
description: "Vitaly route authorization: the get_current_* role gates in app/api/deps.py, # PUBLIC_ROUTE marking, ownership checks, and the test that fails on any ungated route. Trigger: adding or modifying a FastAPI endpoint or router in app/api/, touching app/api/deps.py, or discussing roles, permissions, 401/403, JWT claims or public routes."
---

# Vitaly RBAC — gating every route

**Source of truth:** `.agents/rules/rbac-enforcement.md` (the law). This skill is the how-to
for the code as it exists today. Legacy gaps are listed in "Legacy notes".

A handler that does not pass through a gate is reachable by anyone on the internet. No linter
or type checker catches that. This skill prevents it.

## The real gates (`app/api/deps.py`)

| Dependency                   | Allows                    | Returns           |
| ---------------------------- | ------------------------- | ----------------- |
| `get_current_user_token`     | any valid, non-revoked JWT | decoded payload `dict` |
| `get_current_admin`          | `scope=admin` token (admin portal: `ADMIN_SISTEMA`) | payload `dict` |
| `get_current_client`         | `scope=client` token (client portal: `ADMIN_ESCUELA`, `DOCTOR`, `REPRESENTANTE`) | payload `dict` |
| `get_current_admin_sistema`  | `UserRole.ADMIN_SISTEMA` (on `get_current_admin`)  | payload `dict`    |
| `get_current_admin_escuela`  | `UserRole.ADMIN_ESCUELA` (on `get_current_client`) | payload `dict`    |
| `get_current_doctor`         | `UserRole.DOCTOR` (on `get_current_client`)        | payload `dict`    |
| `get_current_representante`  | `UserRole.REPRESENTANTE` (on `get_current_client`) | payload `dict`    |

Chain: `get_current_user_token` decodes the HS256 JWT and rejects revoked tokens (logout) with
401; the scope gate (`get_current_admin` / `get_current_client`) rejects a token without
`scope` with 401 (issued before the portal split: forces a fresh login) and a token from the
other portal with 403; the role gate raises 403. Each login portal stamps `scope`:
`POST /auth/admin/login` → `admin`, `POST /auth/login` → `client` (`TokenScope` and
`SCOPE_ROLES` in `app/schemas/enums.py`). Payload claims: `sub` (user id as string), `role`,
`scope`, `email`, `name`, plus role extras (`school` name for admin_escuela,
`especially` for doctor, `type_representative` for representante). There is **no**
`school_id` claim — see `vitaly-tenant-isolation`.

## Endpoint pattern

```python
@router.get("/students/{student_id}", response_model=APIResponse[StudentRead], summary="...")
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela),
) -> APIResponse[StudentRead]:
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_detail(user_id=user_id, student_id=student_id)
    return APIResponse(data=result, message="...")
```

- Pick the narrowest gate. A route for several roles needs a new gate in `deps.py` (e.g. a
  small factory `require_roles(*roles)` built on `get_current_user_token`), never an inline check.
- If a whole router shares one role, prefer `APIRouter(dependencies=[Depends(get_current_x)])`
  and still inject the payload where the handler needs `sub`.
- Keep 403 details explicit about what was required (deps.py already names the role).

## Check the gate, not the role inline

```python
# Bad: authorization hidden in the handler body
if payload["role"] != "doctor":
    raise HTTPException(403)

# Good: the dependency is the authorization
doctor_payload: dict = Depends(get_current_doctor)
```

Inline role checks scatter authorization across handlers; adding a role then becomes a grep hunt.

## Public routes

Mark every intentionally public handler with a `# PUBLIC_ROUTE` comment exactly above the
function definition, i.e. above its decorator stack (as in the rule's example). Legitimately
public today: `/auth/register-*`, `/auth/login`, `/auth/admin/login`, `/catalogs/*`, `GET /schools`, `/`, `/health`
and `GET /health-visual` (`app/main.py:72`). Of these, `/`, `/health`, `/health-visual`
and `school.py` have no marker at all (`catalogs.py` has it in the
docstring): mark them before the guard test can go green.

## Ownership checks (role is not enough)

A valid role gate only answers "who"; the service must also answer "which rows":

- **representante → own students**: resolve `parent.id` from `parent.user_id == sub`, then only
  touch students linked in `student_representative` (`parent_id`, `is_deleted = False`).
- **doctor → own schools**: scope through `doctor_to_school` for the doctor resolved from `sub`.
- **admin_escuela → own school**: `school_id` resolved from `school_administrator` (see tenant skill).

Status codes are a project-wide standard (rule `tenant-isolation.md`, directive 5): the row
does not exist → **404**; the row exists but belongs to another school, parent or doctor →
**403** (`HTTPException(status_code=403, detail="...")`). Look the row up by id first, then
compare ownership; never answer a foreign row with 404.

## Re-validate the role for high-risk actions

The `role` claim is frozen at login: a demoted or deactivated user keeps it until the token
expires. For high-risk actions (approving users, changing roles, deleting PHR/medical data,
cross-school admin operations), re-read the user's current role and active status from the
`user` table in the service before acting, instead of trusting the JWT alone. Routine reads can
rely on the token.

## Guard test: no ungated route

Cheap, high-value: walk every mounted route and fail when one has no auth dependency and no
`# PUBLIC_ROUTE` marker. `inspect.getcomments` finds the canonical comment above the decorators;
the `getsource` fallback tolerates legacy placements (docstring) until they are migrated. Since every role gate depends on `get_current_user_token`, checking for
that one callable in the dependency tree covers them all.

```python
# tests/api/test_route_protection.py
import inspect
from fastapi.routing import APIRoute
from app.main import app
from app.api.deps import get_current_user_token

def _calls(dependant):
    for dep in dependant.dependencies:
        yield dep.call
        yield from _calls(dep)

def _is_public(endpoint) -> bool:
    comments = inspect.getcomments(endpoint) or ""
    return "# PUBLIC_ROUTE" in comments or "# PUBLIC_ROUTE" in inspect.getsource(endpoint)

def test_every_route_is_gated_or_public():
    offenders = [
        f"{sorted(r.methods)} {r.path}"
        for r in app.routes
        if isinstance(r, APIRoute) and r.include_in_schema
        and get_current_user_token not in set(_calls(r.dependant))
        and not _is_public(r.endpoint)
    ]
    assert not offenders, f"Ungated routes without # PUBLIC_ROUTE: {offenders}"
```

Pair it with negative tests per gate: wrong role → 403, missing/revoked token → 401. Missing
token → 401 is guaranteed by the pinned `fastapi[standard]>=0.122.0` (`requirements.txt`):
security classes such as `HTTPBearer()` in `deps.py` return 401 since 0.122.0. Override
gates with `app.dependency_overrides[get_current_doctor] = lambda: {"sub": "1", "role": "doctor", "scope": "client"}`
(real tokens and `get_current_user_token` overrides must carry `scope`, or the scope gate answers 401).

## Legacy notes

- Legacy `# PUBLIC_ROUTE` placement: see the legacy note in `.agents/rules/rbac-enforcement.md` §2.
- **Real gap:** `POST /academic-year` and `PATCH /academic-year/sync-current` mutate data with no
  gate and no marker ("No requiere JWT"). Do not copy this; flag it to the user.

## Red flags

- A handler whose only dependencies are path/body params.
- `payload["role"]` compared anywhere outside `app/api/deps.py`.
- A new public route without `# PUBLIC_ROUTE`.
- A role-gated read that takes a foreign id (student, parent, case) without an ownership filter.
- A foreign-owned row answered with 404 instead of 403.
