---
description: Validación obligatoria de tabla vacía antes de cualquier acción
---
# Validación de Tabla Vacía Obligatoria

Para garantizar la integridad y el correcto manejo de errores del sistema, todos los servicios y endpoints que realicen acciones sobre una tabla de la base de datos (Supabase/PostgreSQL) deben verificar primero si la tabla contiene datos.

## Reglas
1. **Verificación Previa**: Antes de ejecutar cualquier consulta de selección, actualización o eliminación masiva, se debe comprobar si existen registros en la tabla objetivo.
2. **Manejo de Error**: Si la tabla está vacía, se debe lanzar una excepción controlada (ej. `HTTPException` con código 404 o 200 con mensaje descriptivo, según el caso de uso) indicando que no hay registros disponibles para procesar.
3. **Optimización**: Para verificar si una tabla está vacía, se recomienda usar una consulta de conteo (`count="exact"`) o una selección limitada a un solo registro (`limit(1)`) para evitar sobrecarga.

## Ejemplos

### Escenario: Listado de Usuarios

#### Incorrecto
```python
@router.get("/users")
def get_users():
    # Intenta obtener datos sin verificar si hay alguno
    response = supabase.table("user").select("*").execute()
    return APIResponse(data=response.data, message="Lista obtenida") # Puede devolver data=[] sin contexto
```

#### Correcto
```python
@router.get("/users")
def get_users():
    # Primero verifica si existe al menos un registro
    check = supabase.table("user").select("id", count="exact").limit(1).execute()
    
    if not check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron registros en la tabla de usuarios. La tabla está vacía."
        )
    
    response = supabase.table("user").select("*").execute()
    return APIResponse(data=response.data, message="Lista de usuarios obtenida exitosamente")
```

### Escenario: Actualización de Escuela

#### Correcto
```python
def update_school(school_id: int, data: dict):
    # Verificar si existe la escuela
    check = supabase.table("school").select("sch_id").eq("sch_id", school_id).execute()
    
    if not check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="La escuela solicitada no existe o la tabla de escuelas está vacía."
        )
    
    # Proceder con la acción
    supabase.table("school").update(data).eq("sch_id", school_id).execute()
```
