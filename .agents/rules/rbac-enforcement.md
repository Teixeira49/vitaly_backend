---
description: "Protección obligatoria de rutas con los gates get_current_* de app/api/deps.py y declaración explícita de rutas públicas"
globs:
  - "app/api/**/*.py"
alwaysApply: false
---

# Protección de Rutas con RBAC

## 1. Scope & Context
- **Target Area:** Todos los routers y endpoints en `app/api/`, y las dependencias de autorización en `app/api/deps.py`.
- **Roles:** Security Sentinel, Backend Architect.
- **Objetivo:** Garantizar que ninguna ruta sensible quede desprotegida o sin control de acceso por roles.
- **Guía práctica:** El cómo (tabla de gates, claims del JWT, ownership checks y test de guardia) vive en la skill `vitaly-rbac`.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** crees un endpoint sin control de acceso, a menos que esté documentado explícitamente como público.
- ⛔ **NUNCA** realices validaciones manuales de rol dentro de la función (ej. `if payload["role"] != "doctor": raise HTTPException(...)`). Toda validación debe resolverse en las dependencias de FastAPI definidas en `app/api/deps.py`.
- ⛔ **NUNCA** compares `payload["role"]` fuera de `app/api/deps.py`.
- 🔒 **MANDATORIO:** Las rutas públicas (ej. login, registro, catálogos, salud/ping) deben incluir el comentario `# PUBLIC_ROUTE` exactamente encima de la definición de la función, por encima de sus decoradores (`@router.get(...)`).
  - **Nota de legado:** algunas rutas existentes (ej. `app/api/v1/endpoints/catalogs.py`) colocan `# PUBLIC_ROUTE` dentro del docstring, y otras públicas no tienen marcador. Al tocar esos archivos, migra el marcador a un comentario encima de la función.

## 3. Directivas Prescriptivas
1. **Gates disponibles (`app/api/deps.py`):** Todos dependen de `get_current_user_token` (decodifica el JWT HS256, rechaza tokens revocados con 401) y retornan el payload decodificado como `dict`. Cada gate de rol lanza 403 si el rol no coincide. El enum de roles es `UserRole` (`app/schemas/enums.py`).

   | Dependencia                  | Permite                    |
   | ---------------------------- | -------------------------- |
   | `get_current_user_token`     | cualquier JWT válido y no revocado |
   | `get_current_admin_sistema`  | `UserRole.ADMIN_SISTEMA`   |
   | `get_current_admin_escuela`  | `UserRole.ADMIN_ESCUELA`   |
   | `get_current_doctor`         | `UserRole.DOCTOR`          |
   | `get_current_representante`  | `UserRole.REPRESENTANTE`   |

2. **Rutas Individuales:** Declara el gate más estrecho posible e inyecta el payload. En código nuevo usa la forma `Annotated` (recomendada por FastAPI): `admin_payload: Annotated[dict, Depends(get_current_admin_escuela)]`; la forma `admin_payload: dict = Depends(get_current_admin_escuela)` se tolera como legado. El id del usuario autenticado se obtiene con `int(admin_payload["sub"])`.
   - Los handlers y sus dependencias son `def` síncronos mientras el acceso a datos sea supabase-py (cliente bloqueante): FastAPI los ejecuta en un threadpool. No uses `async def` con llamadas bloqueantes, porque congela el event loop.
3. **Rutas a Nivel Router:** Cuando un grupo completo de endpoints comparta el mismo rol, define la dependencia en el constructor: `APIRouter(dependencies=[Depends(get_current_admin_sistema)])`, e inyecta el payload igualmente en los handlers que necesiten `sub`.
4. **Varios Roles:** Si una ruta debe admitir más de un rol, crea un nuevo gate en `app/api/deps.py` construido sobre `get_current_user_token` (ej. una pequeña factoría de roles). Nunca lo resuelvas dentro del handler.
5. **Manejo Centralizado de Excepciones:** Los gates de `deps.py` son los únicos responsables de lanzar `HTTPException(status_code=403, ...)` por rol insuficiente y 401 por token inválido o revocado. El 401 por token **ausente** lo emite `HTTPBearer()` (`app/api/deps.py`); está garantizado por la versión fijada `fastapi[standard]>=0.122.0` en `requirements.txt` (las versiones anteriores respondían 403).

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Ruta sin gate de rol, validando el rol manualmente dentro del controlador
@router.delete("/students/{student_id}")
def delete_student(student_id: int, payload: dict = Depends(get_current_user_token)):
    # ❌ Lógica de autorización mezclada en el controlador
    if payload.get("role") != UserRole.ADMIN_ESCUELA.value:
        raise HTTPException(status_code=403, detail="Solo administradores de escuela")
    ...
```

### ✅ Patrón Estándar (DO)

#### Opción A: A Nivel de Router (Recomendado para módulos de un solo rol)
```python
# Bien: Todo el módulo protegido uniformemente
from app.api.deps import get_current_admin_sistema

router = APIRouter(dependencies=[Depends(get_current_admin_sistema)])
```

#### Opción B: Endpoint Específico o Ruta Pública
```python
# Bien: Endpoint con el gate de rol inyectado (patrón real de school_admin_students.py)
from app.api.deps import get_current_admin_escuela

@router.get("/students/{student_id}", response_model=APIResponse[dict])
def get_student_detail(
    student_id: int,
    admin_payload: dict = Depends(get_current_admin_escuela),
):
    user_id = int(admin_payload["sub"])
    result = school_admin_service.get_student_detail(user_id=user_id, student_id=student_id)
    return APIResponse(data=result, message="Detalle del estudiante obtenido exitosamente")

# PUBLIC_ROUTE
@router.get("/states", response_model=APIResponse[List[StateResponse]])
def get_states():
    ...
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Todo endpoint no público tiene un gate `Depends(get_current_*)` de `app/api/deps.py` (individual o en router).
  - [ ] Toda ruta pública tiene el comentario `# PUBLIC_ROUTE` encima de la función.
  - [ ] Cero comprobaciones de `payload["role"]` escritas a mano dentro del cuerpo de la función.
  - [ ] Las rutas multi-rol usan un gate dedicado en `deps.py`.
- **Comando de Verificación:** `pytest tests/` (el test de guardia que falla ante cualquier ruta sin gate ni `# PUBLIC_ROUTE` está descrito en la skill `vitaly-rbac`; aún no existe en `tests/`).
