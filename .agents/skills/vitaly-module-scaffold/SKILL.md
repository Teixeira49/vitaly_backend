---
name: vitaly-module-scaffold
description: "Step-by-step scaffold of a NEW Vitaly feature module: app/schemas/<feature>.py, app/services/<role>_<feature>_service.py (class + module singleton over the global supabase client), app/api/v1/endpoints/<role>_<feature>.py, and its include_router line in app/api/v1/router.py. Trigger: creating a new feature, module, resource, endpoint file or service in this repo, or asking where new backend code should go."
---

# Vitaly module scaffold — new feature, four files

**Source of truth:** `.agents/rules/*.md` (the law) and the root `CLAUDE.md` (Issue #8 docs).
Layering and legacy policy live in `vitaly-architecture`. This skill only lays the bricks.

## Decision tree

- New feature for one role (`school_admin`, `doctor`, `parent`, `admin`)? → full scaffold below.
- New endpoint inside an existing feature file? → extend the existing schema/service files; still follow steps 3–4.
- School-admin feature? → NEW service file, never `school_admin_service.py` (god file).
- Need settings? → `from app.core.config import get_settings` (cached with `lru_cache`).

## Delegation map (do not duplicate these here)

Auth gates and `# PUBLIC_ROUTE` → `vitaly-rbac` · `school_id` and query filters →
`vitaly-tenant-isolation` · envelope, errors, pagination → `standard-api-responses` ·
frontend DTOs → `vitaly-contracts-parity` · ALL tests → `vitaly-feature-testing`.

## Step 1 — Schemas: `app/schemas/<feature>.py`

- Suffixes only: `*Base`, `*Create`, `*Update` (all fields `Optional`), `*Read`, `*Filter`.
- Every field: `Field(description=...)`. `*Read` never exposes `password`, hashes or `photo_file_id`;
  `model_config = ConfigDict(from_attributes=True)` is optional (harmless, no ORM).
- No `school_id` in `*Create`/`*Update`: the server derives it. Schemas import nothing from services.

```python
from pydantic import BaseModel, ConfigDict, Field

class VaccineBase(BaseModel):
    name: str = Field(description="Vaccine name")
class VaccineCreate(VaccineBase):
    pass
class VaccineUpdate(BaseModel):
    name: str | None = Field(default=None, description="New vaccine name")
class VaccineRead(VaccineBase):
    id: int = Field(description="Vaccine identifier")
    model_config = ConfigDict(from_attributes=True)
```

## Step 2 — Service: `app/services/<role>_<feature>_service.py`

- A class plus a module-level singleton. Endpoints import the singleton; never `Depends(...)` it.
- Talks to the global client `from app.core.database import supabase` (sync supabase-py).
- Raising `HTTPException` is the convention; `app/core/exceptions.py` wraps it in the envelope.
  Any other exception (e.g. supabase `APIError`) bypasses it and returns a plain 500: wrap
  unexpected errors as `HTTPException(500, ...)`.
- Resolve `school_id` with the shared helper `get_school_id_for_admin` from `app/services/tenancy.py`
  (target, not created yet; until then reuse `school_admin_service._get_school_id_for_admin`, never
  copy the query). Filter EVERY list/mutation by it.
- Lists: return `[]` when empty (never 404). Single record: look up by id; missing → 404,
  other school → 403 (`vitaly-tenant-isolation`).
- Google-style docstrings (`Args`, `Returns`, `Raises`) on every public method.

```python
from fastapi import HTTPException, status
from app.core.database import supabase
from app.services.tenancy import get_school_id_for_admin  # interim: school_admin_service._get_school_id_for_admin

class SchoolAdminVaccineService:
    """Vaccine catalog management for school administrators."""

    def list_vaccines(self, user_id: int) -> list[dict]:
        """Lists the vaccines of the admin's school.

        Args:
            user_id: Authenticated user id (JWT `sub`).
        Returns:
            list[dict]: Vaccines of the school; empty list if none.
        Raises:
            HTTPException: 403 if the user is not linked to a school.
        """
        school_id = get_school_id_for_admin(user_id)
        res = supabase.table("vaccine").select("*").eq("school_id", school_id).execute()
        return res.data or []

    def get_vaccine(self, user_id: int, vaccine_id: int) -> dict:
        """Same docstring shape; Raises: HTTPException 404 if it does not exist, 403 if other school."""
        school_id = get_school_id_for_admin(user_id)
        res = supabase.table("vaccine").select("*").eq("id", vaccine_id).execute()
        if not res.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No existe ninguna vacuna con ID {vaccine_id}.")
        if res.data[0]["school_id"] != school_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="No tienes permiso para acceder a este recurso: pertenece a otra escuela.")
        return res.data[0]
    # Mutations: same check first, then update/delete with .eq("id", ...).eq("school_id", school_id).

school_admin_vaccine_service = SchoolAdminVaccineService()
```

## Step 3 — Endpoints: `app/api/v1/endpoints/<role>_<feature>.py`

- `router = APIRouter()` with NO prefix (the prefix lives in `router.py`).
- Sync `def` handlers. Gate with `Depends(get_current_<role>)` from `app/api/deps.py`;
  `user_id = int(payload["sub"])`. No inline role checks. No `supabase` import here.
- Decorator: `response_model=APIResponse[XRead]` (or `APIResponse[list[XRead]]`), `summary`, `description`.
- Docstring sections: `Multi-tenancy`, `RBAC`, `Raises` (Issue #8).

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse
from app.schemas.vaccine import VaccineRead
from app.services.school_admin_vaccine_service import school_admin_vaccine_service

router = APIRouter()

@router.get("/{vaccine_id}", response_model=APIResponse[VaccineRead],
            summary="Obtener vacuna", description="Retorna una vacuna de la escuela del administrador.")
def get_vaccine(vaccine_id: int, admin_payload: dict = Depends(get_current_admin_escuela)):
    """
    Multi-tenancy:
        school_id is resolved server-side from the JWT user, never from the request.
    RBAC:
        Requires role admin_escuela.
    Raises:
        HTTPException(403): User not linked to a school, or vaccine belongs to another school.
        HTTPException(404): Vaccine does not exist.
    """
    data = school_admin_vaccine_service.get_vaccine(int(admin_payload["sub"]), vaccine_id)
    return APIResponse(success=True, data=data, message="Vacuna obtenida exitosamente")
```

## Step 4 — Register in `app/api/v1/router.py`

Convention: endpoint file plural (`school_admin_vaccines.py`), service singular
(`school_admin_vaccine_service.py`). Add the module to the `from app.api.v1.endpoints import ...` line, then:

```python
api_router.include_router(school_admin_vaccines.router, prefix="/school-admin/vaccines",
                          tags=["Administrador de Escuela - Vacunas"])
```

Tags: Spanish `"<Role> - <Feature>"` labels. Mounted under `settings.API_V1_STR` (`/api/v1`).

## Output Contract

Confirm ALL before reporting done:

- [ ] Endpoint file `app/api/v1/endpoints/<role>_<feature>.py`: gated, sync, `APIResponse[...]`,
      `summary`/`description`, docstring with Multi-tenancy / RBAC / Raises.
- [ ] Service file `app/services/<role>_<feature>_service.py`: class + singleton, Google docstrings,
      `school_id` from the shared helper, lists/mutations filtered, `[]` for empty lists,
      404 for missing record, 403 for another school's record.
- [ ] Schemas `app/schemas/<feature>.py`: standard suffixes, `Field(description=...)`, no secrets in `*Read`.
- [ ] Registration line added in `app/api/v1/router.py` with prefix + Spanish tag.
- [ ] Tests written via `vitaly-feature-testing` (RBAC matrix, tenancy, empty table, 404).
- [ ] Frontend DTO parity checked via `vitaly-contracts-parity` (`../vitaly_frontend/vitaly-care-for-families`).
- [ ] No new method added to `school_admin_service.py`.
