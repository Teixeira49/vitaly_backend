---
description: "Obligatoriedad de envolver todas las respuestas en APIResponse[T] y FastAPI metadata"
globs:
  - "app/api/**/*.py"
alwaysApply: false
---

# Formato de Respuesta Estándar Unificado

## 1. Scope & Context
- **Target Area:** Todos los endpoints y routers en `app/api/`.
- **Roles:** Backend Architect.
- **Objetivo:** Uniformar la estructura de salida de la API para que el frontend pueda procesar de forma predecible `success`, `data`, `message` y metadatos.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** devuelvas diccionarios de Python directamente (`return {"id": 1}`).
- ⛔ **NUNCA** devuelvas filas crudas de Supabase sin envolver (`return response.data`).
- 🔒 **MANDATORIO:** Especifica siempre `response_model=APIResponse[...]` en el decorador de la ruta. En endpoints nuevos usa un esquema tipado (`APIResponse[SchemaRead]` o `APIResponse[list[SchemaRead]]`); varios endpoints existentes usan `APIResponse[dict]`, que se tolera como legado y se tipa de forma oportunista coordinando con el frontend (`cross-repo-e2e.md`).
- 🔒 **MANDATORIO:** Retorna siempre una instancia de `APIResponse(data=..., message="...")` en el cuerpo del controlador. `success` vale `True` por defecto (`app/schemas/responses.py`); declararlo explícitamente es opcional.
- 🔒 **MANDATORIO — Errores 500:** `app/main.py` solo registra handlers para `RequestValidationError` y `HTTPException`. Cualquier otra excepción (ej. `APIError` de supabase-py, `ResponseValidationError`) produce un 500 en texto plano **sin** envelope. Los servicios deben capturar los errores inesperados y relanzarlos como `HTTPException(status_code=500, detail="...")`, registrándolos antes con `logger.exception`.
- ⚠️ **EXCEPCIÓN DOCUMENTADA — Descargas/exportaciones de archivos:** los endpoints que devuelven un archivo (CSV/Excel vía `StreamingResponse`) **no** usan el envelope en la respuesta exitosa, porque un archivo binario/texto no puede envolverse en JSON. Condiciones obligatorias:
  - Declarar `response_class=StreamingResponse` y `responses={200: {"content": {"text/csv": {}}}}` (o el media type correspondiente, ej. `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`) para que `/docs` sea fiel.
  - Los **errores** (401/403/404/422/500) **siguen** devolviendo el envelope JSON `APIResponse` a través de los handlers globales de excepciones, siempre que se lancen como `HTTPException` (ver la restricción de errores 500 más abajo): valida y lanza `HTTPException` **antes** de empezar a transmitir el archivo.
  - Seguir el skill `export-patterns` (headers, sanitización anti CSV-injection, filtrado por `school_id`, gate de rol y auditoría).

## 3. Directivas Prescriptivas
1. **Modelos de Respuesta:** Define esquemas Pydantic específicos para lectura (`*Read`) y úsalos como parámetro genérico en `APIResponse[T]`.
2. **Mensajes Descriptivos:** Incluye un `message` claro que explique brevemente el resultado de la acción al cliente (ej. `"Usuario creado exitosamente"`).
3. **Manejo de Respuestas Vacías:** Cuando una lista no tenga elementos, devuelve `data=[]` con `success=True`.
4. **Paginación:** Los listados paginados **nuevos** devuelven la lista en `data` y la paginación en `meta` (`PaginationMeta`: `page`, `size`, `total`, `total_pages`). Los endpoints existentes anidan `{data, total, page, size}` dentro de `data`; ese formato se tolera como legado y **no** se migra sin coordinar el cambio con el frontend (`cross-repo-e2e.md`, skill `vitaly-contracts-parity`), porque el cliente desempaqueta esa estructura.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Retorna filas de Supabase sin envolver
@router.get("/users/{user_id}")
def get_user(user_id: int, admin_payload: dict = Depends(get_current_admin_sistema)):
    response = supabase.table("user").select("*").eq("id", user_id).execute()
    return response.data[0] # ❌ Sin response_model, sin envelope APIResponse y sin validar existencia
```

### ✅ Patrón Estándar (DO)
```python
# Bien: Envuelto en APIResponse y con esquema Pydantic en response_model
@router.get(
    "/users/{user_id}",
    response_model=APIResponse[UserRead],
    summary="Obtener usuario por ID"
)
def get_user(
    user_id: int,
    admin_payload: dict = Depends(get_current_admin_sistema),
) -> APIResponse[UserRead]:
    # El servicio consulta con supabase-py y lanza 404 si response.data está vacío
    user = admin_service.get_user_details(user_id=user_id)
    return APIResponse(
        success=True,
        data=user,
        message="Usuario obtenido exitosamente"
    )
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El decorador tiene `response_model=APIResponse[Schema]` (o, si es una descarga de archivo, `response_class=StreamingResponse` + `responses={200: {"content": {...}}}`).
  - [ ] El `return` final invoca `APIResponse(data=..., message=...)`.
  - [ ] La documentación en `/docs` muestra el modelo envelope esperado.
- **Comando de Verificación:** `pytest tests/`
