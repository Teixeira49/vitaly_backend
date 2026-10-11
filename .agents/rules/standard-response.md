---
description: Obligatoriedad de usar el formato de respuesta estándar
---
# Respuesta Estándar Obligatoria

Para mantener la consistencia en el consumo de la API por parte del frontend, todos los endpoints deben envolver sus respuestas en el esquema base unificado.

## Reglas
1. **Nunca** devuelvas diccionarios de Python directamente (`return {"id": 1}`).
2. **Nunca** devuelvas instancias de la base de datos sin envolver (`return user`).
3. **Siempre** usa `APIResponse[T]` en el `response_model` del decorador del router.
4. **Siempre** retorna una instancia de `APIResponse(data=...)` en el cuerpo de la función.

## Ejemplos

### Incorrecto
```python
@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return await get_user_from_db(user_id) # ❌ Mala práctica
```

### Correcto
```python
@router.get("/users/{user_id}", response_model=APIResponse[UserSchema])
async def get_user(user_id: int):
    user = await get_user_from_db(user_id)
    return APIResponse(data=user, message="User retrieved") # ✅ Buena práctica
```
