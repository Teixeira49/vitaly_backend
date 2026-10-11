---
description: "Convenciones de nombres y enriquecimiento de esquemas Pydantic para OpenAPI"
globs:
  - "app/schemas/**/*.py"
alwaysApply: false
---

# Convención de Nombres de Esquemas (Pydantic)

## 1. Scope & Context
- **Target Area:** Todos los modelos Pydantic ubicados en `app/schemas/`.
- **Roles:** Backend Architect.
- **Objetivo:** Estandarizar la nomenclatura de esquemas para evitar duplicación caótica y garantizar que la documentación de Swagger/OpenAPI (`/docs`) sea auto-explicativa.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** uses sufijos o nombres ambiguos como `UserDTO`, `UserData`, `UserInfo` o `UserResponse`.
- ⛔ **NUNCA** devuelvas contraseñas, hashes o datos de seguridad en esquemas de lectura (`*Read`).
- 🔒 **MANDATORIO:** Todo esquema debe adherirse a los sufijos estándar según el flujo de datos: `*Base`, `*Create`, `*Update`, `*Read`, `*Filter`.
- 🔒 **MANDATORIO:** Documenta los atributos principales utilizando `Field(description=...)` para enriquecer la documentación interactiva.

## 3. Directivas Prescriptivas
1. **`*Base`**: Campos comunes compartidos entre creación y lectura (ej. `email`, `nombre`).
2. **`*Create`**: Datos recibidos en peticiones POST para crear una entidad (incluye contraseñas planas si aplica).
3. **`*Update`**: Datos recibidos en peticiones PUT/PATCH (todos los campos editables como `Optional`).
4. **`*Read`**: Modelo que el backend envía al cliente (incluye `id`, `created_at`, omite hashes). Debe configurarse con `model_config = ConfigDict(from_attributes=True)` para serializar modelos SQLAlchemy.
5. **`*Filter`**: Parámetros de consulta en endpoints de búsqueda y listados.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Nomenclatura caótica, mezcla de propósitos y exposición de secretos
class UserDTO(BaseModel):
    id: int
    email: str
    password_hash: str # ❌ Expone datos sensibles
    
class UserData(BaseModel): # ❌ Nombre ambiguo
    name: str
```

### ✅ Patrón Estándar (DO)
```python
# Bien: Nomenclatura sistemática y segura
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    email: EmailStr = Field(description="Correo electrónico institucional")
    name: str = Field(description="Nombre completo del usuario")

class UserCreate(UserBase):
    password: str = Field(min_length=8, description="Contraseña en texto plano para registro")

class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(default=None, description="Nuevo correo electrónico")
    name: Optional[str] = Field(default=None, description="Nuevo nombre completo")

class UserRead(UserBase):
    id: int = Field(description="Identificador único del usuario")
    created_at: datetime = Field(description="Fecha y hora de creación")

    model_config = ConfigDict(from_attributes=True)
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Los esquemas utilizan exclusivamente sufijos `*Create`, `*Update`, `*Read`, `*Filter` o `*Base`.
  - [ ] Los esquemas `*Read` tienen `from_attributes=True` y no exponen credenciales.
  - [ ] Campos documentados con `Field(description=...)`.
- **Comando de Verificación:** `ruff check app/schemas/`
