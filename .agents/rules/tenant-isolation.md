---
description: "Aislamiento estricto multi-tenancy por escuela_id en endpoints y consultas"
globs:
  - "app/api/**/*.py"
  - "app/services/**/*.py"
alwaysApply: false
---

# Aislamiento de Datos por Escuela (Multi-Tenancy)

## 1. Scope & Context
- **Target Area:** Endpoints (`app/api/`), Servicios (`app/services/`) y Consultas SQLAlchemy.
- **Roles:** Security Sentinel, Database Specialist, Backend Architect.
- **Objetivo:** Prevenir fugas de información entre instituciones educativas garantizando el aislamiento estricto de datos en cada operación.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** confíes en el `escuela_id` enviado en el cuerpo (`body`), headers o `query params` por el cliente para scopes de usuarios con rol de escuela (`ADMIN_ESCUELA`, `DOCTOR`, etc.).
- ⛔ **NUNCA** realices validaciones de rol en línea dentro del handler (ej. `if user.role == "admin":`); la autorización pertenece a `Depends(RoleChecker(...))`.
- 🔒 **MANDATORIO:** El `escuela_id` debe obtenerse exclusivamente del token validado (`current_user.escuela_id`).
- 🔒 **MANDATORIO:** Toda consulta de lectura, actualización o borrado debe incluir el filtro `Model.escuela_id == current_user.escuela_id` (excepto para `ADMIN_SISTEMA` cuando audite el sistema global).

## 3. Directivas Prescriptivas
1. **Inyección en Rutas:** Protege la ruta con `Depends(RoleChecker([...]))` e inyecta el `current_user` autenticado.
2. **Delegación a Servicios:** Pasa `current_user.escuela_id` explícitamente al método del servicio correspondiente.
3. **Filtrado en Servicios:** En el servicio, concatena siempre `.filter(Model.escuela_id == escuela_id)`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Acepta escuela_id del cliente o hace validaciones de roles manuales en el cuerpo
@router.post("/estudiantes")
def create_student(
    payload: StudentCreate, # El cliente podría enviar {"escuela_id": 999} ajeno ❌
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # ❌ Antipatrón de autorización inline
    if user.role == UserRole.ADMIN_ESCUELA:
        payload.escuela_id = user.escuela_id
    elif user.role != UserRole.ADMIN_SISTEMA:
        raise HTTPException(status_code=403, detail="No autorizado")

    student = Student(**payload.model_dump())
    db.add(student)
    db.commit()
    return student
```

### ✅ Patrón Estándar (DO)
```python
# Bien: RBAC declarado en dependencias y tenant_id inyectado limpiamente desde current_user
@router.post(
    "/estudiantes",
    response_model=APIResponse[StudentRead],
    summary="Registrar nuevo estudiante"
)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN_ESCUELA, RoleEnum.DOCTOR]))
) -> APIResponse[StudentRead]:
    # El escuela_id proviene de forma garantizada del token seguro ✅
    student = student_service.create(
        db=db,
        obj_in=payload,
        escuela_id=current_user.escuela_id
    )
    return APIResponse(
        success=True,
        data=student,
        message="Estudiante registrado exitosamente"
    )
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] No se lee `escuela_id` del payload entrante para autorizar.
  - [ ] El endpoint cuenta con `Depends(RoleChecker(...))`.
  - [ ] Los métodos de servicio reciben y filtran por `escuela_id`.
- **Comando de Verificación:** `pytest tests/api/test_multi_tenancy.py`
