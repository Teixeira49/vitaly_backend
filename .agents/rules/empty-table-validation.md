---
description: "Validación de existencia previa de registros y manejo de tablas vacías con el cliente supabase-py"
globs:
  - "app/services/**/*.py"
  - "app/api/**/*.py"
alwaysApply: false
---

# Validación de Existencia y Tablas Vacías

## 1. Scope & Context
- **Target Area:** Servicios (`app/services/`) y endpoints (`app/api/`) que interactúan con PostgreSQL/Supabase mediante el cliente supabase-py.
- **Roles:** Database Specialist, Backend Architect.
- **Objetivo:** Prevenir errores 500 silenciosos y fallos en cascada al operar sobre registros o tablas sin datos previos, respetando la semántica de la API REST.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** devuelvas `HTTPException(404)` al consultar colecciones o listas vacías (`GET /users`). Las colecciones vacías deben responder con `200 OK` y `data=[]`.
- ⛔ **NUNCA** ejecutes mutaciones (`update`, `delete`) asumiendo que el registro existe sin validar previamente o comprobar que `response.data` no esté vacío.
- ⛔ **NUNCA** crees clientes ad-hoc (`create_client(...)` fuera de `app/core/database.py`) ni hagas llamadas HTTP directas a la API REST de Supabase (`httpx`/`requests` contra `/rest/v1/...`) que eludan el cliente compartido.
- 🔒 **MANDATORIO:** La capa de acceso a datos es el cliente supabase-py compartido: `from app.core.database import supabase`. La lógica de consulta debe vivir preferentemente en `app/services/` (algunos endpoints legados, como `catalogs.py`, consultan directamente; no repliques ese patrón en código nuevo).

## 3. Directivas Prescriptivas

1. **Listados y Colecciones:**
   - `response = supabase.table(...).select(...).execute()` retorna `response.data` como lista (vacía si no hay filas).
   - Si la lista está vacía, devuelve `APIResponse(success=True, data=[], message="No se encontraron registros")`.
2. **Operaciones sobre Recurso Individual (`GET /item/{id}`, `PUT`, `PATCH`, `DELETE`):**
   - Consulta el registro por su ID (y por `school_id` cuando la tabla tenga alcance de escuela, ver `tenant-isolation.md`) y comprueba `if not response.data`.
   - Si no existe, lanza de inmediato `HTTPException(status_code=404, detail="...")`. Si existe, usa `response.data[0]`.
   - En mutaciones filtradas por id (y `school_id`), trata un `response.data` vacío como recurso no encontrado.
3. **Tablas Catálogo / Prerrequisitos de Negocio:**
   - Si una operación requiere que existan datos base configurados (ej. `academic_year` vigente, categorías de salón), realiza una verificación ligera (`.select("id").limit(1)` o `count="exact"`) antes de procesar operaciones complejas.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Retorna 404 al listar una colección vacía y crea un cliente ad-hoc
from supabase import create_client

@router.get("/schools", response_model=APIResponse[list[SchoolRead]])
def list_schools():
    client = create_client(url, key)  # ❌ Cliente fuera de app/core/database.py
    schools = client.table("school").select("*").execute().data
    if not schools:
        # ❌ ERROR: Rompe el estándar REST (debería ser 200 con lista vacía)
        raise HTTPException(status_code=404, detail="No hay escuelas registradas")
    return APIResponse(success=True, data=schools, message="Escuelas obtenidas")
```

### ✅ Patrón Estándar (DO)
```python
# Servicio: colección retorna lista (posiblemente vacía); recurso individual valida existencia
from fastapi import HTTPException
from app.core.database import supabase

def list_schools(self) -> list[dict]:
    response = supabase.table("school").select("sch_id, name, rif").eq("is_deleted", False).execute()
    return response.data

def get_school_detail(self, school_id: int) -> dict:
    rows = (
        supabase.table("school")
        .select("sch_id, name, rif, address, is_active")
        .eq("sch_id", school_id)
        .execute()
    )
    if not rows.data:
        raise HTTPException(status_code=404, detail=f"No existe ninguna escuela con ID {school_id}.")
    return rows.data[0]

# Endpoint: colección vacía responde 200 con data=[]
@router.get("/", response_model=APIResponse[list[SchoolRead]], summary="Listar escuelas")
def list_schools(admin_payload: dict = Depends(get_current_admin_sistema)):
    schools = admin_service.list_schools()
    message = "Escuelas recuperadas exitosamente" if schools else "No hay escuelas registradas actualmente"
    return APIResponse(success=True, data=schools, message=message)
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Colecciones (`GET /recursos`) retornan código 200 y array vacío cuando no hay registros.
  - [ ] Recursos individuales (`GET/PUT/PATCH/DELETE /recursos/{id}`) lanzan 404 si `response.data` está vacío.
  - [ ] Uso exclusivo del cliente compartido `supabase` de `app/core/database.py`; sin clientes ad-hoc ni llamadas REST directas.
- **Comando de Verificación:** `pytest tests/ -k "not_found or empty"`
