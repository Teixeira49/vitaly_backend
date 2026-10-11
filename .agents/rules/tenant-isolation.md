---
description: Prevención de fuga de datos entre escuelas (Multi-tenancy)
---
# Aislamiento de Datos por Escuela

Dado que en Vitaly conviven datos de múltiples instituciones, se debe garantizar el aislamiento estricto de los registros para prevenir fugas de información y accesos indebidos.

## Reglas
1. **Nunca** confíes en el `escuela_id` enviado por el cliente en el cuerpo de una petición JSON o como parámetro en la URL si el usuario es un administrador de escuela.
2. Si un usuario con el rol `admin_escuela` o `doctor` realiza una consulta a la base de datos o crea un registro, se le debe asignar (o usar en el filtro SQL) automáticamente el valor de `current_user.escuela_id`.
3. Solo los administradores del sistema (`admin_sistema`) están exentos del filtro automático.

## Ejemplos

### Incorrecto
```python
# Un administrador malintencionado podría enviar un `escuela_id` ajeno
@router.post("/estudiantes")
async def create_student(
    student_data: StudentCreate, # El cliente manda {"escuela_id": "otr-escuela-id"}  ❌
    user: User = Depends(get_current_active_user)
):
    ...
```

### Correcto
```python
@router.post("/estudiantes")
async def create_student(
    student_data: StudentCreate,
    user: User = Depends(get_current_active_user)
):
    # La aplicación fuerza el tenant del usuario actual ✅
    if user.role == UserRole.ADMIN_ESCUELA:
        student_data.escuela_id = user.escuela_id
    elif user.role != UserRole.ADMIN_SISTEMA:
        raise HTTPException(status_code=403, detail="No autorizado")
    ...
```
