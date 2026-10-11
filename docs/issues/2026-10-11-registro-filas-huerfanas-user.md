---
title: "[🐛 Bug] El registro de usuarios puede dejar filas huérfanas en la tabla user"
labels: [bug, P2, services]
issue: 19
url: https://github.com/Teixeira49/vitaly_backend/issues/19
---

## Descripción

El registro de cualquier rol ejecuta varias inserciones independientes con supabase-py (`user` → `user_roles` → tabla de perfil del rol) sin transacción ni compensación. Si una inserción posterior falla (error de red, violación de constraint, FK inválida como un `school_id` inexistente), la fila de `user` ya creada queda huérfana. Además, el usuario no puede reintentar el registro: la comprobación de duplicados encuentra la fila huérfana y responde 400.

## Evidencia

- `app/services/auth_service.py:44` — `supabase.table("user").insert(user_data).execute()` (primera escritura, ya persistida).
- `app/services/auth_service.py:56` — `supabase.table("user_roles").insert(role_data).execute()`; el resultado no se comprueba.
- Inserciones de perfil posteriores, sin comprobación ni rollback:
  - `app/services/auth_service.py:63-66` — `system_administrator` (`register_system_admin`).
  - `app/services/auth_service.py:73-78` — `school_administrator` con `school_id` del payload (`register_school_admin`).
  - `app/services/auth_service.py:85-89` — `doctor` (`register_doctor`).
  - `app/services/auth_service.py:96-101` — `parent`, seguido de `parent_service.link_students_by_identity` en `:105-108` (`register_parent`).
- `app/services/auth_service.py:12-21` — en un reintento, el `select` por email encuentra la fila huérfana; si falta `user_roles`, responde 400 "El usuario ya existe bajo el rol: desconocido" (`:17`).
- No hay ningún `try/except` ni `delete` compensatorio en el módulo: `grep -nwE "try|except|rpc|delete" app/services/auth_service.py` no devuelve coincidencias.

## Comportamiento actual vs esperado

- **Actual:** un fallo a mitad del registro deja `user` (y a veces `user_roles`) sin perfil; el cliente recibe 500 y el email queda bloqueado para siempre.
- **Esperado:** el registro es atómico: o se crean todas las filas, o ninguna; un reintento tras un fallo funciona.

## Impacto

- ¿Expone datos médicos/PHR o PII? No se exponen, pero quedan PII (nombre, email, documento de identidad, fecha de nacimiento) almacenados en registros huérfanos sin ciclo de vida.
- ¿Fuga entre escuelas? No.
- Roles afectados: todos los registros públicos (`admin_sistema`, `admin_escuela`, `doctor`, `representante`). El caso más probable es `register_school_admin` con un `school_id` inválido. Los usuarios bloqueados requieren limpieza manual en base de datos.

## Propuesta de solución

- **Solución de fondo:** mover la escritura multi-tabla a una función `plpgsql` (una por rol, o una con parámetro de rol) ejecutada en una sola transacción e invocada con `supabase.rpc(...)`. Requiere una migración en `supabase/migrations/`, que debe seguir `.agents/rules/database_migration_protocol.md` (informe de impacto y **confirmación explícita del usuario** antes de aplicarla).
- **Mitigación a corto plazo:** envolver las inserciones posteriores a `user` en `try/except` y, ante fallo, borrar de forma compensatoria las filas ya creadas (`user_roles`, `user`) antes de relanzar un `HTTPException` controlado. Comprobar `.data` de cada insert.

**Decisión abierta:** ¿se aplica primero la compensación (sin migración) y la función `rpc` como seguimiento, o se va directamente a la función transaccional?

## Criterios de aceptación

- [ ] Si falla la inserción del perfil (p. ej. `school_id` inexistente), no queda ninguna fila en `user` ni en `user_roles` para ese email.
- [ ] Un reintento con el mismo email tras el fallo completa el registro.
- [ ] Se comprueba el resultado de cada inserción.
- [ ] Tests en `tests/` (supabase-py simulado) que fuerzan el fallo de cada paso y verifican la compensación o el rollback.
- [ ] Si se opta por `rpc`, la migración se presenta y aprueba según el protocolo antes de aplicarse.

## Referencias

- `.agents/rules/database_migration_protocol.md`
- `.agents/rules/empty-table-validation.md` (comprobar `response.data` antes de continuar)
- Skills `supabase-integration` (transacciones vía `.rpc()`), `vitaly-feature-testing`
