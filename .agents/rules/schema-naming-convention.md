---
description: Convenciones de nombres para modelos (Schema) de Pydantic
---
# Convención de Nombres de Esquemas (Pydantic)

FastAPI y Swagger dependen de los nombres de los esquemas (modelos Pydantic) para generar una documentación legible y ordenada. Una mala convención de nombres origina modelos duplicados o confusos (`User`, `UserDB`, `UserInfo`, `UserResponse`).

## Reglas
Todos los modelos de Pydantic (`BaseModel`) deben estar nombrados bajo los siguientes prefijos según el flujo de datos:

1. **`*Create`**: Petición de cliente para crear algo (ej. `UserCreate`).
2. **`*Update`**: Petición de cliente para modificar (campos `Optional`, ej. `UserUpdate`).
3. **`*Read`**: Respuesta de la base de datos para mostrar al cliente (suele ignorar el password hash e incluir id, datetime, ej. `UserRead`).
4. **`*Filter`**: Esquema para los alias o query params opcionales de búsqueda `?name=...` (ej. `UserFilter`).

## Ejemplos


```python
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    # Base compartida por varios schemas
    email: EmailStr
    name: str

class UserCreate(UserBase):
    # Lo que recibe el Endpoint POST
    password: str

class UserUpdate(BaseModel):
    # Lo que recibe el Endpoint PATCH/PUT
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    password: Optional[str] = None

class UserRead(UserBase):
    # Lo que el Endpoint le devuelve al Frontend (Se insertará dentro del `APIResponse[T]`)
    id: int
    created_at: datetime
```
