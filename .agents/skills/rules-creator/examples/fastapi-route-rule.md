---
description: "Convenciones de endpoints FastAPI: envelope APIResponse, gates de rol get_current_* y aislamiento por school_id"
globs:
  - "app/api/**/*.py"
alwaysApply: false
---

# Estándares de Endpoints FastAPI y Aislamiento Multi-Tenancy

> Ejemplo de referencia para `rules-creator`. Las reglas vigentes viven en
> `.agents/rules/` (`standard-response.md`, `rbac-enforcement.md`, `tenant-isolation.md`).

## 1. Scope & Context
- **Target Area:** Handlers en `app/api/v1/endpoints/`.
- **Roles:** Backend Architect, Security Sentinel.
- **Objetivo:** Que todo endpoint use el envelope unificado, un gate de rol explícito y aislamiento estricto por escuela.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** devuelvas diccionarios crudos ni `response.data` de supabase-py sin envolver.
- ⛔ **NUNCA** aceptes `school_id` desde el body, query o path para autorizar a roles de escuela; se resuelve en el servidor a partir de `sub`.
- 🔒 **MANDATORIO:** Todo endpoint tiene `# PUBLIC_ROUTE` o un gate `Depends(get_current_*)` de `app/api/deps.py`.
- 🔒 **MANDATORIO:** Declara siempre `response_model=APIResponse[SchemaRead]`.

## 3. Directivas Prescriptivas
1. **Envelope:** Retorna `APIResponse(data=result, message="...")`.
2. **Delegación:** Toda consulta y cálculo de negocio vive en el servicio de `app/services/`.
3. **Documentación:** Metadatos FastAPI (`summary`, `description`) y docstring con aislamiento, roles y `Raises`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: sin gate de rol, school_id del cliente, acceso directo a datos y sin envelope
@router.post("/students")
def create_student(payload: dict):
    row = supabase.table("student").insert(payload).execute()
    return row.data
```

### ✅ Patrón Estándar (DO)
```python
# Bien: esquemas explícitos, gate de rol, delegación al servicio y envelope
@router.post(
    "/students",
    response_model=APIResponse[StudentRead],
    status_code=status.HTTP_201_CREATED,
    summary="Registrar nuevo estudiante",
    description="Crea un estudiante en la escuela del administrador autenticado.",
)
def create_student(
    payload: StudentCreate,
    admin_payload: dict = Depends(get_current_admin_escuela),
) -> APIResponse[StudentRead]:
    """Crea un estudiante asociado a la escuela del usuario autenticado.

    Aislamiento: el school_id se resuelve en el servicio a partir de `sub`.
    Roles: admin_escuela.

    Raises:
        HTTPException: 403 si el administrador no está vinculado a ninguna escuela.
    """
    user_id = int(admin_payload["sub"])
    student = school_admin_service.create_student(user_id=user_id, data=payload)
    return APIResponse(data=student, message="Estudiante registrado exitosamente")
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El endpoint tiene `response_model=APIResponse[...]`.
  - [ ] El `school_id` se resuelve en el servidor, nunca desde el payload.
  - [ ] La lógica de negocio está en `app/services/`.
- **Comando de Verificación:** `pytest tests/api/`
