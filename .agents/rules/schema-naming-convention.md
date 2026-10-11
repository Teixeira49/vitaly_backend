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
- **Contexto técnico:** El backend no usa ORM; los servicios devuelven `dict` obtenidos de `supabase.table(...).execute().data`, que Pydantic valida directamente.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** uses sufijos o nombres ambiguos como `UserDTO`, `UserData` o `UserInfo` en esquemas nuevos.
- ⛔ **NUNCA** devuelvas contraseñas, hashes o datos de seguridad en esquemas de lectura (`*Read` / `*Response`).
- 🔒 **MANDATORIO (esquemas nuevos):** Todo esquema nuevo debe adherirse a los sufijos estándar según el flujo de datos: `*Base`, `*Create`, `*Update`, `*Read`, `*Filter`.
- 🔒 **MANDATORIO:** Documenta los atributos principales utilizando `Field(description=...)` para enriquecer la documentación interactiva.
- ⚠️ **Legado tolerado:** Existen esquemas con sufijo `*Response` (ej. `StateResponse`, `StudentResponse`, `UserResponse`, `PaginatedSchoolsResponse`, `PaginatedStudentsResponse`) y algunos `*Request` (ej. `ApproveUserRequest`). Se toleran; renómbralos de forma oportunista (al tocar el endpoint) y **siempre** coordinando el cambio con las interfaces TypeScript del frontend según `cross-repo-e2e.md`. No crees esquemas nuevos con esos sufijos.

## 3. Directivas Prescriptivas
1. **`*Base`**: Campos comunes compartidos entre creación y lectura (ej. `email`, `name`).
2. **`*Create`**: Datos recibidos en peticiones POST para crear una entidad (incluye contraseñas planas si aplica).
3. **`*Update`**: Datos recibidos en peticiones PUT/PATCH (todos los campos editables como `Optional`).
4. **`*Read`**: Modelo que el backend envía al cliente (incluye `id`, `created_at`, omite hashes). `model_config = ConfigDict(from_attributes=True)` es **opcional**: al no haber ORM no es necesario, aunque es inofensivo y algunos esquemas existentes lo declaran.
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
from pydantic import BaseModel, EmailStr, Field
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
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Los esquemas nuevos utilizan exclusivamente sufijos `*Create`, `*Update`, `*Read`, `*Filter` o `*Base`.
  - [ ] Cualquier renombrado de un `*Response` legado se coordinó con el frontend.
  - [ ] Los esquemas de lectura no exponen credenciales.
  - [ ] Campos documentados con `Field(description=...)`.
- **Comando de Verificación:** `ruff check app/schemas/`
