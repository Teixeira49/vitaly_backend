---
name: standard-api-responses
description: Standardized API response patterns for FastAPI using a unified envelope (success, message, data, errors, meta) with Pydantic and global error handling. Use when creating new endpoints, defining schemas, or implementing error handlers.
---

# Standardized API Responses

This skill defines the engineering standard for API responses in FastAPI, ensuring consistency, scalability, and ease of consumption for the frontend.

## When to use this skill

- When creating or modifying **FastAPI endpoints**.
- When designing **Pydantic schemas** for API outputs.
- When implementing **Global Error Handlers** or Exception Handlers.
- When you need to ensure the frontend receives a predictable JSON structure (`success`, `message`, `data`, `errors`, `meta`).

## Decision Tree

**How should you structure the response?**
- **Is it a single resource or action?** -> Use `APIResponse[YourModel]` with the `data` field populated.
- **Is it a collection of items?** -> Use `APIResponse[List[YourModel]]` and include the `meta` field for pagination.
- **Did an error occur (Validation/422)?** -> Use the `validation_exception_handler` pattern to return the `errors` list.
- **Did a manual exception occur (404/403/401)?** -> Raise `HTTPException` and ensure the global handler wraps it in the `APIResponse` envelope.

## How to use it

### 1. Unified Envelope Architecture

All API responses must follow a predictable "envelope" structure.

```json
{
  "success": boolean,
  "message": string | null,
  "data": object | array | null,
  "errors": array | null,
  "meta": object | null
}
```

### 2. Implementation with Pydantic Generics

Use `typing.Generic` to maintain schema integrity in Swagger documentation.

```python
from typing import Generic, TypeVar, Optional, List, Union
from pydantic import BaseModel
from pydantic.generics import GenericModel

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

class APIResponse(GenericModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    errors: Optional[List[ErrorDetail]] = None
    meta: Optional[PaginationMeta] = None

    class Config:
        orm_mode = True
```

### 3. Global Error Handling

Implement these handlers to ensure even crashes return the standard envelope.

```python
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# 1. Validation Error Handler (422)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [ErrorDetail(loc=err["loc"], msg=err["msg"], type=err["type"]) for err in exc.errors()]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=APIResponse(success=False, message="Validation error", errors=errors).dict()
    )

# 2. HTTP Exception Handler (4xx)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=APIResponse(success=False, message=str(exc.detail)).dict()
    )
```

### 4. Implementation Example

```python
@router.get("/users", response_model=APIResponse[List[UserSchema]])
async def list_users(page: int = 1, size: int = 10):
    users, total = await service.get_users(page, size)
    return APIResponse(
        data=users,
        meta=PaginationMeta(
            page=page,
            size=size,
            total=total,
            total_pages=(total + size - 1) // size
        )
    )
```

## Best Practices

- **Keep skills focused:** Use this skill specifically for response consistency.
- **Write clear descriptions:** Ensure Pydantic models in `data` are well-documented.
- **Predictability:** Never return a JSON structure that doesn't follow the `APIResponse` envelope.
- **Resilience:** The error middleware must catch all unhandled exceptions.
