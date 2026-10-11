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
- ⛔ **NUNCA** devuelvas instancias de modelos SQLAlchemy crudas (`return db_user`).
- 🔒 **MANDATORIO:** Especifica siempre `response_model=APIResponse[SchemaRead]` en el decorador de la ruta.
- 🔒 **MANDATORIO:** Retorna siempre una instancia de `APIResponse(success=True, data=..., message="...")` en el cuerpo del controlador.

## 3. Directivas Prescriptivas
1. **Modelos de Respuesta:** Define esquemas Pydantic específicos para lectura (`*Read`) y úsalos como parámetro genérico en `APIResponse[T]`.
2. **Mensajes Descriptivos:** Incluye un `message` claro que explique brevemente el resultado de la acción al cliente (ej. `"Usuario creado exitosamente"`).
3. **Manejo de Respuestas Vacías:** Cuando una lista no tenga elementos, devuelve `data=[]` con `success=True`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Retorna diccionarios o modelos de DB sin envolver
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    return user # ❌ Sin response_model y sin envelope APIResponse
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
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.ADMIN_SISTEMA]))
) -> APIResponse[UserRead]:
    user = user_service.get_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    return APIResponse(
        success=True,
        data=user,
        message="Usuario obtenido exitosamente"
    )
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] El decorador tiene `response_model=APIResponse[Schema]`.
  - [ ] El `return` final invoca `APIResponse(success=True, data=..., message=...)`.
  - [ ] La documentación en `/docs` muestra el modelo envelope esperado.
- **Comando de Verificación:** `pytest tests/api/`
