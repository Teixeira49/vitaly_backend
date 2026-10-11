---
description: Reglas de seguridad para la protección de rutas
---
# Protección de Rutas con RBAC

Se debe prevenir la creación de rutas sensibles omitiendo las comprobaciones de roles. Todas las rutas de la API deben estar protegidas o explicitamente designadas como públicas.

## Reglas
1. **Todo** endpoint debe incluir un `Depends(RoleChecker([...]))`.
2. Si se trata de múltiples rutas protegidas por los mismos roles, aplica la dependencia a nivel de `APIRouter`.
3. Si un endpoint es verdaderamente público (ej. Login o Registro), debe ser claramente etiquetado con un comentario `# PUBLIC_ROUTE` sobre la función.
4. No usar validaciones de rol en línea (como `if user.role == "admin":`), siempre usar `RoleChecker`.

## Ejemplos

### Nivel de Router (Recomendado)
```python
router = APIRouter(
    prefix="/consultas",
    dependencies=[Depends(RoleChecker([UserRole.DOCTOR, UserRole.ADMIN_ESCUELA]))]
)
```

### Ruta Pública
```python
# PUBLIC_ROUTE
@router.post("/login")
async def login(credentials: OAuth2PasswordRequestForm = Depends()):
    pass
```
