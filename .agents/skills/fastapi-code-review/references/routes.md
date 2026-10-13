# Routes

Endpoints live in `app/api/v1/endpoints/*.py`, are aggregated in `app/api/v1/router.py`, and mounted in `app/main.py` under `settings.API_V1_STR` (`/api/v1`).

## 1. Missing envelope or response_model (`standard-response.md`)

```python
# BAD - raw dict, no response_model
@router.get("/students/{student_id}")
def get_student(student_id: int, admin_payload: dict = Depends(get_current_admin_escuela)):
    return {"id": student_id}

# GOOD
@router.get(
    "/students/{student_id}",
    response_model=APIResponse[StudentRead],
    summary="Get student detail",
    description="Student of the authenticated admin's school.",
)
def get_student(student_id: int, admin_payload: dict = Depends(get_current_admin_escuela)) -> APIResponse[StudentRead]:
    """Get a student. Tenant: school_id from `sub`. RBAC: admin_escuela.

    Raises:
        HTTPException: 404 if the student does not exist; 403 if it belongs to another school.
    """
    student = school_admin_service.get_student(user_id=int(admin_payload["sub"]), student_id=student_id)
    return APIResponse(data=student, message="Estudiante obtenido exitosamente")
```

`APIResponse[dict]` on existing endpoints is legacy-tolerated; new endpoints use a typed `*Read`.

## 2. Missing auth gate or public marker (`rbac-enforcement.md`)

Every route needs `Depends(get_current_*)` (handler or `APIRouter(dependencies=[...])`) or:

```python
# PUBLIC_ROUTE
@router.get("/states", response_model=APIResponse[List[StateResponse]])
def get_states(): ...
```

Legacy: some public routes put `# PUBLIC_ROUTE` inside the docstring; when touched, move it above the function.

## 3. Missing docs metadata (Issue #8)

New or modified endpoints need `summary`, `description`, and a docstring with tenant scope, allowed role(s), and `Raises`.

## 4. Wrong HTTP methods / status codes

- GET reads, POST creates, PUT/PATCH updates, DELETE removes. No mutations via GET.
- Creates may use `status_code=201` and still return the envelope.
- Avoid `status_code=204` on routes that return `APIResponse` (204 must have no body); return 200 with a message instead.

## 5. Generic exceptions instead of HTTPException

`raise ValueError(...)` becomes an un-enveloped 500 (there is no catch-all handler). Raise `HTTPException(status_code=404|403|409, detail="...")`; the global handler puts `detail` into `message`.

Same for unexpected failures in services (supabase `APIError` from `.execute()`): `app/main.py:45-46` registers only `RequestValidationError` and `StarletteHTTPException`, so services must wrap them as `HTTPException(status_code=500, detail="...")`.

## 6. Path/query validation

Constrain ids and pagination: `Path(..., gt=0)`, `Query(1, ge=1)`, `Query(10, ge=1, le=100)`.

## Review questions

1. `response_model=APIResponse[...]` and `return APIResponse(...)` on every route?
2. Gate or `# PUBLIC_ROUTE` on every route?
3. `summary`, `description`, docstring present on new/modified routes?
4. Methods and status codes semantically correct, with no 204 + body?
5. Expected failures raised as `HTTPException`?
