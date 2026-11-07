---
name: standard-api-responses
description: How Vitaly's unified APIResponse envelope (success, message, data, errors, meta) and its global exception handlers work, mirrored from app/schemas/responses.py and app/core/exceptions.py. Use when creating or modifying endpoints in app/api/, choosing a response_model, paginating a list, or touching error handlers.
---

# Standard API Responses (Vitaly)

The law is `.agents/rules/standard-response.md` (wrap every return in `APIResponse(...)`,
always declare `response_model=APIResponse[...]`, never return raw dicts or `response.data`).
This skill is the **how**: what the envelope is, how errors get wrapped, and how to paginate.
Related: `empty-table-validation.md` (200 + `[]` vs 404), `vitaly-rbac` (gates),
`vitaly-tenant-isolation` (school filter), `vitaly-contracts-parity` (frontend DTOs).

## Decision tree

- Single resource or action → `response_model=APIResponse[XRead]`, `return APIResponse(data=..., message=...)`.
- Collection → `APIResponse[list[XRead]]`; empty list is `data=[]` with 200, never 404.
- Paginated collection (**new** endpoints) → same, plus `meta=PaginationMeta(...)`. Existing endpoints
  nest `{"data", "total", "page", "size"}` inside `data` (`admin_service.py:25-31`, `Paginated*Response`
  in `app/schemas/school.py`): tolerated legacy; migrating them to `meta` requires coordinating the
  frontend via `vitaly-contracts-parity`.
- File download/export (`StreamingResponse`) → the documented exception in `standard-response.md` §2:
  no envelope on 200, errors still enveloped. See `export-patterns`.
- Not found / forbidden / conflict → `raise HTTPException(...)` in the service or handler; the global handler wraps it.
- Bad input → let Pydantic raise; the 422 handler wraps it with `errors`.

## 1. The envelope (verbatim from `app/schemas/responses.py`)

```python
from typing import Generic, TypeVar, Optional, List, Union, Any
from pydantic import BaseModel

T = TypeVar("T")

class PaginationMeta(BaseModel):
    page: int
    size: int
    total: int
    total_pages: int

class ErrorDetail(BaseModel):
    loc: Optional[List[Union[str, int]]] = None
    msg: str
    type: str

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[ErrorDetail]] = None
    meta: Optional[PaginationMeta] = None

    class Config:
        from_attributes = True
```

Notes:
- Pydantic v2 generic: `BaseModel` + `Generic[T]` (no `GenericModel`, no `orm_mode`).
- `class Config: from_attributes = True` is the v1-style config syntax still accepted by v2
  (deprecation warning). New schemas should use `model_config = ConfigDict(from_attributes=True)`;
  don't change this file without a reason.
- `success` defaults to `True`, so `success=True` is optional on happy paths.
- Serialize with `.model_dump()` (v2), never `.dict()`.

Wire shape the frontend unwraps (`APIResponse.data`):

```json
{ "success": true, "message": "...", "data": {}, "errors": null, "meta": null }
```

## 2. Global handlers (verbatim from `app/core/exceptions.py`)

```python
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [ErrorDetail(loc=err["loc"], msg=err["msg"], type=err["type"]) for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(success=False, message="Validation error", errors=errors).model_dump()
    )

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(success=False, message=str(exc.detail)).model_dump()
    )
```

Registered in `app/main.py`:

```python
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
```

Consequences:
- `HTTPException(detail=...)` becomes `message`; `errors` stays `null` for non-422 errors.
- `headers` on the exception (e.g. `WWW-Authenticate` from the 401 gates) are **not** forwarded
  by this handler.
- There is **no** catch-all `Exception` handler: an unhandled error returns FastAPI's default
  500 body, not the envelope. Raise `HTTPException` for expected failures.
- `app/main.py:45-46` registers handlers only for `RequestValidationError` and
  `StarletteHTTPException`. Anything else (supabase `APIError`, `ResponseValidationError`) is a plain
  500 without envelope, so services must wrap unexpected errors as `HTTPException(500, ...)`.

## 3. Examples (sync `def`, supabase-py services, `get_current_*` gates)

Handlers are sync `def` because the shared supabase-py client (`app/core/database.py`) is blocking.

```python
from fastapi import APIRouter, Depends, Query
from app.api.deps import get_current_admin_escuela
from app.schemas.responses import APIResponse, PaginationMeta
from app.schemas.school import ClassroomRead
from app.services.school_admin_service import school_admin_service

router = APIRouter()

@router.get(
    "/classrooms",
    response_model=APIResponse[list[ClassroomRead]],
    summary="List classrooms of the admin's school",
    description="Paginated list scoped to the authenticated admin's school.",
)
def list_classrooms(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    admin_payload: dict = Depends(get_current_admin_escuela),
) -> APIResponse[list[ClassroomRead]]:
    """List classrooms. Tenant: school_id resolved from `sub`. RBAC: admin_escuela.

    Raises:
        HTTPException: 403 if the admin is not linked to a school.
    """
    items, total = school_admin_service.list_classrooms(
        user_id=int(admin_payload["sub"]), page=page, size=size
    )
    return APIResponse(
        data=items,  # [] when empty -> still 200
        message="Salones obtenidos exitosamente" if items else "No se encontraron registros",
        meta=PaginationMeta(page=page, size=size, total=total, total_pages=(total + size - 1) // size),
    )
```

`meta` is the target for **new** paginated endpoints only; existing ones keep the nested
`{"data", "total", "page", "size"}` legacy shape until migrated with the frontend (see decision tree).

Service side (paginated supabase-py query, same `count="exact"` + `.range()` pattern as
`school_admin_event_service.py`; 404/403 handled here for single resources). `school_id` comes from
`SchoolAdminService._get_school_id_for_admin` (`school_admin_service.py:37`) until the shared
`get_school_id_for_admin(user_id)` in `app/services/tenancy.py` exists; reuse it, never copy the query:

```python
from fastapi import HTTPException
from app.core.database import supabase

def list_classrooms(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
    school_id = self._get_school_id_for_admin(user_id)
    start = (page - 1) * size
    resp = (
        supabase.table("classroom")
        .select("id, level, category, section, is_deleted", count="exact")  # ClassroomRead fields
        .eq("school_id", school_id)
        .eq("is_deleted", False)
        .order("id")                       # stable order before range
        .range(start, start + size - 1)
        .execute()
    )
    return resp.data, resp.count or 0

def get_classroom(self, user_id: int, classroom_id: int) -> dict:
    school_id = self._get_school_id_for_admin(user_id)
    resp = (
        supabase.table("classroom")
        .select("id, school_id, level, category, section, is_deleted")
        .eq("id", classroom_id)            # by id only: 404 vs 403 must be distinguishable
        .execute()
    )
    if not resp.data:
        raise HTTPException(status_code=404, detail=f"No existe ningún salón con ID {classroom_id}.")
    if resp.data[0]["school_id"] != school_id:
        raise HTTPException(
            status_code=403,
            detail="No tienes permiso para acceder a este recurso: pertenece a otra escuela.",
        )
    return resp.data[0]
```

## 4. Legacy `APIResponse[dict]`

Many existing endpoints declare `response_model=APIResponse[dict]` (e.g.
`school_admin_students.py`). Per `standard-response.md` this is **tolerated as legacy**: still an
envelope, just untyped `data`. Don't add new ones; type them opportunistically
(`APIResponse[XRead]`) when you touch the endpoint, coordinating the frontend DTO via
`vitaly-contracts-parity`.

## Red flags

- `return response.data`, `return {...}`, or a route without `response_model`.
- `.dict()` instead of `.model_dump()`; `GenericModel` / `orm_mode` in new code.
- 404 on an empty collection.
- Building error JSON by hand instead of raising `HTTPException`.
- `async def` handler calling the blocking supabase client.
