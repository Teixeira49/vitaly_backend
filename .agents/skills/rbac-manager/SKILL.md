---
name: rbac-manager
description: Role-Based Access Control (RBAC) patterns for FastAPI. Implements role checks, dependency injection for authorization, and data isolation strategies. Use when defining access levels, protecting routes, or handling multi-tenancy.
---

# RBAC Manager

This skill defines the engineering best practices for implementing Role-Based Access Control (RBAC) in FastAPI, focusing on the **Vitaly** system with administrator, health, and representation roles.

## When to use this skill

- Use this when you need to **define new user roles** or modify existing ones.
- Use this when you need to **protect a FastAPI route** or a complete router from unauthorized access.
- Use this to implement **Data Isolation (Multitenancy)**, ensuring institutional admins only see their own school's data.
- Use this when validating **resource ownership** (e.g., a representative can only see their own students).

## Decision Tree

**How should you enforce access control?**
- **Is the requirement purely role-based (e.g., Admins only)?** -> Use the `RoleChecker` dependency class in the route's `dependencies` list.
- **Does the whole module require the same roles?** -> Apply the `RoleChecker` dependency at the `APIRouter` level.
- **Is the access dependent on the user's institution (School)?** -> Enforce a "Data Isolation" pattern by filtering by the `escuela_id` found in the authenticated user's object.
- **Is the access dependent on a parent-child relationship?** -> Implement an "Ownership Validation" check in the service layer, checking if the resource is linked to the user's ID.

## How to use it

### 1. Role Definitions (Type Safety)

Use an `Enum` to centralize roles and avoid typos.

```python
from enum import Enum

class UserRole(str, Enum):
    ADMIN_SISTEMA = "admin_sistema"  # Total control
    ADMIN_ESCUELA = "admin_escuela"  # Institution control
    DOCTOR = "doctor"                # Health management
    REPRESENTANTE = "representante"  # Parents/Guardians
```

### 2. Dependency Injection: The RoleChecker

Implement a `Callable` class to guard your routes.

```python
from fastapi import Depends, HTTPException, status
from typing import List

class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_active_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user
```

### 3. API Implementation

- **Protecting a single route:**
  ```python
  @router.post("/escuelas", dependencies=[Depends(RoleChecker([UserRole.ADMIN_SISTEMA]))])
  async def create_school(data: SchoolCreate):
      return await service.create(data)
  ```

- **Protecting a whole router:**
  ```python
  router = APIRouter(
      prefix="/salud",
      dependencies=[Depends(RoleChecker([UserRole.DOCTOR, UserRole.ADMIN_ESCUELA]))]
  )
  ```

### 4. Data Isolation (Multitenancy) Strategy

Never trust a `school_id` from the request body for institution-specific admins. Always use the authenticated user's context.

```python
@router.get("/estudiantes")
async def get_students(current_user: User = Depends(get_current_active_user)):
    # Force filter by the admin's school
    if current_user.role == UserRole.ADMIN_ESCUELA:
        return await service.get_by_school(current_user.escuela_id)
    return await service.get_all()
```

## Best Practices

- **PoLP (Least Privilege):** Only grant the minimum access required for the user's function.
- **Role Hierarchies:** Implement inheritance logic within the `RoleChecker` if necessary.
- **JWT vs DB:** Store roles in the JWT for speed (UI), but re-validate against the database for high-security endpoints.
- **Ownership Check:** Always verify parent-child or patient-doctor relationships beyond just checking roles.
