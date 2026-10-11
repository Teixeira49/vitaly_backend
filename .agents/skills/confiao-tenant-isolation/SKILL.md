---
name: confiao-tenant-isolation
description: Aislamiento multi-tenant de Confiao Chatbot con Row-Level Security de PostgreSQL y el ajuste de sesión app.tenant_id. Úsala siempre que se cree o modifique una tabla, un modelo SQLAlchemy, un repositorio, una migración de Alembic o un endpoint que lea o escriba datos de un cliente — y también cuando se hable de tenant_id, RLS, políticas, aislamiento entre clientes, fugas de datos, get_tenant_db, get_platform_db o de agregar un slice nuevo al backend. Aunque el cambio parezca trivial (una columna más, un SELECT más), si toca datos de tenant esta skill aplica: el aislamiento es el requisito no funcional más crítico del producto.
---

# Aislamiento por tenant

Una fuga de datos entre clientes compromete el modelo de negocio completo de la plataforma. Por eso
el aislamiento no descansa en una sola comprobación: descansa en tres capas independientes, y una
consulta mal escrita tiene que atravesar las tres para causar daño.

```
1. Contexto   El tenant sale del JWT de sesión, nunca de la URL ni del cuerpo
2. Filtro     El repositorio filtra explícitamente por tenant_id
3. RLS        PostgreSQL rechaza la fila aunque el filtro falte
```

La tercera capa es la red de seguridad, no la primera línea. Escribir el filtro explícito sigue
siendo obligatorio: RLS existe para que un olvido no se convierta en incidente.

## De dónde sale el tenant

`get_current_context` lee la cookie de sesión, decodifica el JWT y toma `tenant_id` del claim. Ese
es el único origen legítimo.

Nunca aceptes el tenant desde fuera aunque parezca cómodo:

```python
# Mal: el cliente elige a qué tenant pertenece
@router.get("/bots")
async def list_bots(tenant_id: UUID = Query(...)): ...

# Bien: el tenant viene de la sesión, el cliente no participa
@router.get("/bots")
async def list_bots(
    context: TenantContext = Depends(require_permission(Permission.BOT_READ)),
    session: AsyncSession = Depends(get_tenant_db),
): ...
```

## Qué dependencia de sesión usar

La elección determina si RLS está activo, así que no es un detalle de estilo.

| Dependencia        | Fija `app.tenant_id` | Cuándo                                                            |
| ------------------ | -------------------- | ----------------------------------------------------------------- |
| `get_tenant_db`    | Sí                   | Todo endpoint que opera dentro de un tenant. Es el caso normal.    |
| `get_db`           | No                   | Rutas públicas sin sesión: login, aceptar invitación, recuperación |
| `get_platform_db`  | No                   | Solo `/admin`, que consulta varios tenants a la vez                |

`get_platform_db` exige `context.is_platform_admin` y su uso se registra en el audit-log global
marcado como break-glass. Si un endpoint de `/admin` puede resolverse dentro de un solo tenant,
prefiere `get_tenant_db`: reserva el acceso transversal para cuando de verdad haga falta.

## Cómo actúa RLS

`apply_tenant_guc` ejecuta `set_config('app.tenant_id', <uuid>, true)` dentro de la transacción. El
tercer argumento en `true` significa alcance local: el valor muere al terminar la transacción y no
se filtra a la siguiente petición que reutilice la conexión del pool. Esa es la razón de usar
`SET LOCAL` y no `SET`.

La política que evalúa cada tabla protegida:

```sql
ALTER TABLE <tabla> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <tabla> FORCE ROW LEVEL SECURITY;
CREATE POLICY <tabla>_tenant_isolation ON <tabla>
  USING       (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK  (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
```

Tres detalles que conviene no tocar sin entenderlos:

- **`FORCE`** aplica la política también al dueño de la tabla. Sin él, el rol propietario la ignora
  y la protección desaparece justo donde corre la aplicación.
- **`NULLIF(..., '')`** convierte el ajuste vacío en `NULL`, de modo que una sesión sin tenant fijado
  no ve nada en lugar de fallar con un error de casteo.
- **`WITH CHECK`** cubre la escritura. Sin esa cláusula se podría insertar una fila con el
  `tenant_id` de otro cliente aunque no se pudiera leer.

## Tabla nueva: la lista completa

Cuando agregues una tabla de alcance de cliente, los cuatro pasos van juntos. Saltarse el tercero o
el cuarto produce una tabla que parece protegida y no lo está.

1. **Modelo** — hereda de `Base` y los mixins que apliquen:

   ```python
   class MiEntidad(Base, UuidPkMixin, TenantScopedMixin, TimestampMixin):
       __tablename__ = "mi_entidad"
   ```

   `TenantScopedMixin` aporta la columna `tenant_id` indexada. Si la entidad no pertenece a un
   cliente —`tenants`, `users`, `revoked_tokens`— no lleva el mixin y tampoco lleva política.

2. **Registro** — importa el modelo en `src/shared/models_registry.py`. Alembic solo ve lo que está
   importado; un modelo sin registrar produce una migración que borra la tabla en lugar de crearla.

3. **Lista de tablas protegidas** — agrega el nombre a `TENANT_SCOPED_TABLES`. Ojo: esa tupla existe
   **en dos sitios**, en `models_registry.py` y dentro de la migración inicial, y no se sincronizan
   solas. La de la migración es la que ejecuta el `ALTER TABLE`; la de `models_registry` es la que
   documenta el conjunto. Actualiza ambas.

4. **Migración** — `make migration m="agrega mi_entidad"` y después **edítala a mano**:
   `--autogenerate` compara metadata de SQLAlchemy contra la base y no sabe nada de políticas, así
   que jamás las escribe. Añade el bloque `ENABLE` + `FORCE` + `CREATE POLICY` de arriba, y su
   `DROP POLICY` en el `downgrade`.

`audit_events` es la excepción del esquema: admite eventos globales con `tenant_id` nulo, y por eso
lleva una política propia en lugar de la genérica. Si creas otra tabla con esa característica,
cópiala de ahí en vez de forzar la política estándar.

## Repositorios

El filtro explícito vive en el repositorio, que recibe el tenant al construirse y lo aplica en cada
consulta:

```python
repository = SqlAlchemyBotRepository(session, context.tenant_id)
```

Esto mantiene el caso de uso ignorante del aislamiento y concentra el filtro en un solo lugar por
slice. Si te encuentras escribiendo `where(Modelo.tenant_id == ...)` dentro de un router o de un
caso de uso, la lógica está en la capa equivocada.

## Cómo comprobar que funciona

Una tabla protegida se verifica desde dos ángulos, y ambos son baratos:

```sql
-- ¿La política existe y es forzada?
SELECT relname, relrowsecurity, relforcerowsecurity
FROM pg_class WHERE relname = 'mi_entidad';

SELECT polname, pg_get_expr(polqual, polrelid) FROM pg_policy
WHERE polrelid = 'mi_entidad'::regclass;
```

En pruebas, la comprobación que importa es la negativa: con `app.tenant_id` fijado al tenant A, una
consulta sin filtro no debe devolver ni una fila del tenant B. Esa prueba falla ruidosamente si
alguien olvida la política, que es exactamente lo que se busca.

Las pruebas corren sobre SQLite con `aiosqlite`, donde no hay RLS: `apply_tenant_guc` no hace nada
si la URL no empieza por `postgresql`. Por eso una prueba de aislamiento real necesita PostgreSQL —
si la escribes contra SQLite, pasará siempre y no estará midiendo nada.

## Señales de alarma

- Un endpoint de datos de cliente con `Depends(get_db)` en vez de `get_tenant_db`.
- Un `tenant_id` que llega por query string, path o cuerpo de la petición.
- Una migración generada automáticamente que crea una tabla con `tenant_id` y no menciona políticas.
- `get_platform_db` fuera de `src/admin`.
- Una consulta cruda con `text()` sobre tablas de tenant: RLS la cubre, pero el filtro explícito
  desaparece y con él la primera capa.
