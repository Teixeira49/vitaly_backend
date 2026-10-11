---
description: "Protección obligatoria de rutas con RoleChecker y declaración explícita de rutas públicas"
globs:
  - "app/api/**/*.py"
alwaysApply: false
---

# Protección de Rutas con RBAC

## 1. Scope & Context
- **Target Area:** Todos los routers y endpoints en `app/api/`.
- **Roles:** Security Sentinel, Backend Architect.
- **Objetivo:** Garantizar que ninguna ruta sensible quede desprotegida o sin control de acceso por roles.

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** crees un endpoint sin control de acceso, a menos que esté documentado explícitamente como público.
- ⛔ **NUNCA** realices validaciones manuales de rol dentro de la función (ej. `if user.role != "admin": raise HTTPException(...)`). Toda validación debe resolverse en las dependencias de FastAPI.
- 🔒 **MANDATORIO:** Las rutas públicas (ej. login, salud/ping) deben incluir el comentario `# PUBLIC_ROUTE` exactamente encima de la definición de la función.

## 3. Directivas Prescriptivas
1. **Rutas Individuales:** Declara `current_user: User = Depends(RoleChecker([RoleEnum.ADMIN_ESCUELA, ...]))`.
2. **Rutas a Nivel Router:** Cuando un grupo completo de endpoints comparta los mismos permisos, define la dependencia en el constructor de `APIRouter(dependencies=[Depends(RoleChecker([...]))])`.
3. **Manejo Centralizado de Excepciones:** `RoleChecker` debe encargarse de lanzar `HTTPException(status_code=403, detail="Permisos insuficientes")`.

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
```python
# Mal: Ruta desprotegida o validando roles manualmente dentro del controlador
@router.delete("/consultas/{consulta_id}")
def delete_consulta(consulta_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # ❌ Lógica de autorización mezclada en el controlador
    if user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="Solo doctores pueden eliminar consultas")
    ...
```

### ✅ Patrón Estándar (DO)

#### Opción A: A Nivel de Router (Recomendado para módulos)
```python
# Bien: Todo el módulo protegido uniformemente
router = APIRouter(
    prefix="/consultas",
    tags=["Consultas"],
    dependencies=[Depends(RoleChecker([RoleEnum.DOCTOR, RoleEnum.ADMIN_ESCUELA]))]
)
```

#### Opción B: Endpoint Específico o Ruta Pública
```python
# Bien: Endpoint con RoleChecker inyectado
@router.post("/consultas", response_model=APIResponse[ConsultaRead])
def create_consulta(
    payload: ConsultaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(RoleChecker([RoleEnum.DOCTOR]))
) -> APIResponse[ConsultaRead]:
    ...

# PUBLIC_ROUTE
@router.post("/auth/login", response_model=APIResponse[TokenRead])
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    ...
```

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] Todo endpoint no público tiene `Depends(RoleChecker(...))` (individual o en router).
  - [ ] Toda ruta pública tiene el comentario `# PUBLIC_ROUTE`.
  - [ ] Cero comprobaciones de `user.role` escritas a mano dentro del cuerpo de la función.
- **Comando de Verificación:** `pytest tests/api/ -k "auth or rbac or permission"`
