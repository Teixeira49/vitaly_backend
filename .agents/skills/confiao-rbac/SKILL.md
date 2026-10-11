---
name: confiao-rbac
description: Control de permisos de Confiao Chatbot — catálogo Permission, matriz por rol de tenant y de plataforma, y el gate require_permission que declara cada endpoint. Úsala siempre que se añada o modifique un endpoint de FastAPI, se cree un router o un slice, se hable de permisos, roles, autorización, 403, owner/editor/viewer, superadmin/support, consola de administración o break-glass. También al tocar src/shared/rbac.py o el espejo PERMISSIONS de @confiao/contracts. Un endpoint sin permiso declarado es un agujero de autorización, así que en cuanto aparezca una ruta nueva esta skill aplica.
---

# Permisos y roles

Cada endpoint declara qué permiso exige. No hay reglas implícitas, no hay rutas que hereden
autorización de su prefijo: si un handler no pasa por el gate, cualquiera con sesión válida llega a
él. Ese es el defecto que esta skill previene, y no lo detecta ningún linter ni el tipado.

## Dos ejes independientes

El sistema tiene dos dimensiones que se suman, no se anulan:

- **Rol de tenant** — qué puede hacer alguien dentro de su organización. En el MVP solo se emite
  `owner`; `editor` y `viewer` ya están definidos en la matriz para crecer sin migrar el modelo.
- **Rol de plataforma** — supervisión transversal: `superadmin` y `support`. El administrador es un
  tenant más; su capacidad de plataforma vive en un eje aparte precisamente para que no se confunda
  con ser dueño de una organización.

`resolve_permissions(tenant_role, platform_role)` calcula la unión de ambos conjuntos al construir
el `TenantContext`. Un usuario de soporte con rol `owner` en su propio tenant tiene los permisos de
las dos listas, y eso es intencional.

## El patrón del endpoint

```python
@router.get("", response_model=Page[BotResponse])
async def list_bots(
    context: TenantContext = Depends(require_permission(Permission.BOT_READ)),
    session: AsyncSession = Depends(get_tenant_db),
) -> Page[BotResponse]:
    ...
```

Dos dependencias, siempre juntas: `require_permission` responde *quién puede*, `get_tenant_db`
responde *sobre qué datos*. Una sin la otra deja un flanco abierto — ver `confiao-tenant-isolation`
para el segundo.

`require_permission` acepta varios permisos y los exige todos:

```python
Depends(require_permission(Permission.BOT_WRITE, Permission.FLOW_WRITE))
```

Cuando falta alguno lanza `ForbiddenError` con `detail={"missing_permissions": [...]}`, de modo que
el 403 dice qué faltaba en lugar de limitarse a negar. Mantén esa costumbre: un 403 opaco convierte
un error de configuración en una sesión de depuración.

## Permiso nuevo: los tres puntos de alta

Un permiso vive en tres archivos, dos lenguajes y ningún compilador cruza esa frontera. Si te
saltas el tercero, el panel dibuja botones para acciones que la API rechaza.

1. **Catálogo** — `src/shared/rbac.py`, clase `Permission`:

   ```python
   MI_RECURSO_READ: Final = "mi_recurso:read"
   MI_RECURSO_WRITE: Final = "mi_recurso:write"
   ```

2. **Matriz** — el mismo archivo. Añádelo a cada rol que deba tenerlo en
   `TENANT_ROLE_PERMISSIONS` o en `PLATFORM_ROLE_PERMISSIONS`. Recuerda que `editor` y `viewer`
   existen aunque hoy no se emitan: dejarlos desactualizados es acumular deuda silenciosa para la
   fase 2.

3. **Espejo** — `packages/contracts/src/auth.ts`, objeto `PERMISSIONS`. El panel decide con esa
   lista qué acciones ofrece.

### Convención de nombres

`<recurso>:<acción>` para el eje de tenant, `platform:<recurso>:<acción>` para el de plataforma.
Las acciones en uso son `read`, `write` y `delete`. Resiste la tentación de inventar verbos nuevos
—`manage`, `admin`, `full`— porque diluyen el grano: si una operación no encaja en leer, escribir o
borrar, casi siempre es que merece su propio recurso.

## La consola de administración

Los endpoints de `/admin` combinan permiso de plataforma con sesión transversal:

```python
context: TenantContext = Depends(require_permission(Permission.PLATFORM_TENANT_READ)),
session: AsyncSession = Depends(get_platform_db),
```

`get_platform_db` no fija `app.tenant_id`, así que el aislamiento de base de datos queda suspendido
a propósito. A cambio, toda acción de este tipo se registra con `record_audit(...)` y marca de
break-glass. Ese registro no es burocracia: es lo que permite responder «quién miró los datos de
qué cliente y cuándo» cuando un cliente lo pregunte.

## Comprobar el permiso, no el rol

```python
# Mal: ata la lógica al rol y se rompe cuando se emitan editor y viewer
if context.tenant_role == "owner":
    ...

# Bien: pregunta por la capacidad
if context.has_permission(Permission.BOT_DELETE):
    ...
```

La matriz existe para que el rol sea un detalle de configuración. En cuanto una comparación de rol
se cuela en la lógica de negocio, agregar un rol deja de ser editar un diccionario y pasa a ser
buscar condicionales por todo el código.

La misma regla aplica en el panel: decide con `user.permissions`, que viene en la respuesta de
login, no con `user.tenant_role`.

## Cómo comprobarlo

La prueba que aporta valor es la negativa: un usuario sin el permiso recibe 403, y el cuerpo nombra
lo que faltaba.

```python
async def test_listar_bots_exige_permiso(client, sesion_sin_permisos):
    response = await client.get("/api/bots")
    assert response.status_code == 403
    assert "bot:read" in response.json()["detail"]["missing_permissions"]
```

Para el conjunto, una prueba barata y muy rentable recorre todas las rutas montadas en la app y
verifica que ninguna carezca de gate. Al agregar un endpoint sin permiso, esa prueba lo señala sola
en vez de esperar a que alguien lo note en revisión.

## Señales de alarma

- Un endpoint cuyo único `Depends` es la sesión de base de datos.
- Un permiso en `rbac.py` que no existe en `PERMISSIONS` de contracts, o al revés.
- `if context.tenant_role == ...` dentro de un caso de uso.
- Un endpoint de `/admin` con permiso de tenant en vez de permiso `platform:*`.
- Un `record_audit(...)` ausente en una acción que usó `get_platform_db`.
