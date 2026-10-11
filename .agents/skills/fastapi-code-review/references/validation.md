# Validation

Pydantic v2 throughout. Naming and docs follow `schema-naming-convention.md`.

## 1. Use Pydantic models, not manual parsing

```python
# BAD - manual body parsing
def create_classroom(request: Request, admin_payload: dict = Depends(get_current_admin_escuela)): ...

# GOOD
def create_classroom(payload: ClassroomCreate, admin_payload: dict = Depends(get_current_admin_escuela)): ...
```

Validation errors are wrapped by `validation_exception_handler` into
`APIResponse(success=False, message="Validation error", errors=[...])` with 422. Don't re-implement it.

## 2. Schema naming and documentation

- New schemas: `*Base`, `*Create`, `*Update` (all optional), `*Read`, `*Filter`.
- Legacy `*Response` / `*Request` tolerated; rename only when touching the endpoint and coordinating the frontend (`vitaly-contracts-parity`).
- Every main field has `Field(description=...)`.
- `*Read` never includes passwords, hashes, or tokens.

```python
class ClassroomRead(BaseModel):
    id: int = Field(description="Classroom id")
    level: str = Field(description="Grade level")
    section: str = Field(description="Section letter")

    model_config = ConfigDict(from_attributes=True)
```

## 3. Never trust tenant fields from the client

A `*Create`/`*Update` must not carry `school_id` for school-role routes; the service sets it from the resolved value (`tenant-isolation.md`).

## 4. Pydantic v2 APIs only in new code

| v1 (flag) | v2 |
|-----------|----|
| `.dict()` / `.json()` | `.model_dump()` / `.model_dump_json()` |
| `class Config: orm_mode = True` | `model_config = ConfigDict(from_attributes=True)` |
| `@validator` / `@root_validator` | `@field_validator` / `@model_validator` |
| `GenericModel` | `BaseModel, Generic[T]` |

`app/schemas/responses.py` still uses `class Config: from_attributes = True`; accepted, don't churn it.

## 5. Constraints

Use `Field(gt=0)`, `Field(min_length=...)`, `EmailStr`, enums from `app/schemas/enums.py`, and `extra="forbid"` where unknown keys should be rejected.

## 6. Specific HTTPException messages

`detail` becomes the envelope `message` shown to users: make it specific ("Salón no encontrado"), and don't leak internals (supabase error text, SQL).

## 7. Empty vs missing (`empty-table-validation.md`)

- `response.data == []` on a list → 200 with `data=[]`.
- `not response.data` on a single fetch or a filtered mutation → 404.

## Review questions

1. Are bodies typed Pydantic models with `Field(description=...)`?
2. New schema names follow the suffix convention; no secrets in `*Read`?
3. Any `school_id` accepted from the client?
4. Any Pydantic v1 APIs in new code?
5. Empty collections 200, missing resources 404?
