---
title: "[♻️ Deuda técnica] Crear helper compartido app/services/tenancy.py"
labels: [tech-debt, P2, services, agents]
issue: 22
url: https://github.com/Teixeira49/vitaly_backend/issues/22
---

## Descripción
La resolución del `school_id` de un `admin_escuela` está duplicada en dos servicios con la misma consulta a `school_administrator`. La documentación de agentes (`AGENTS.md`, reglas y skills) ya define como objetivo un helper compartido `app/services/tenancy.py` con `get_school_id_for_admin(user_id)`, pero el módulo no existe. Los ejemplos que lo importan fallarían con `ImportError` si se copian tal cual.

## Evidencia
- `app/services/school_admin_service.py:37-50` — `_get_school_id_for_admin`: consulta `school_administrator` por `user_id` y lanza 403 si no hay vínculo.
- `app/services/school_admin_event_service.py:13-27` — `_get_admin_record`: misma consulta (añade `sch_admin_id`) y mismo 403.
- `ls app/services/tenancy.py` → no existe.
- Documentación que ya lo referencia como objetivo: `.agents/AGENTS.md` (§3 Multi-tenancy), `.agents/rules/tenant-isolation.md`, skills `vitaly-tenant-isolation`, `vitaly-module-scaffold` (el ejemplo importa `from app.services.tenancy import get_school_id_for_admin`), `vitaly-architecture`, `supabase-integration`, `vitaly-feature-testing`.

## Comportamiento actual vs esperado
- **Actual:** cada servicio resuelve el `school_id` con su propia copia de la consulta; el módulo documentado no existe.
- **Esperado:** un único helper en `app/services/tenancy.py` reutilizado por todos los servicios, como exige `tenant-isolation.md` §3.2 ("Reutiliza ese helper en lugar de repetir la consulta").

## Impacto
- ¿Expone datos médicos/PHR o PII? No directamente.
- ¿Fuga entre escuelas (school_id)? No hoy, pero cada copia de la consulta es un punto donde una divergencia futura (filtro olvidado, código de error distinto) puede romper el aislamiento.
- Roles afectados: `admin_escuela` (indirectamente, todos los endpoints de escuela).

## Propuesta de solución
Crear `app/services/tenancy.py` con funciones de módulo:
- `get_school_id_for_admin(user_id: int) -> int` (403 si no hay vínculo).
- Opcional: `get_admin_record(user_id: int) -> dict` para los casos que necesitan `sch_admin_id`.

Migrar `SchoolAdminService._get_school_id_for_admin` y `SchoolAdminEventService._get_admin_record` para que deleguen en el helper (o reemplazar sus llamadas), sin cambiar el contrato de los endpoints. Pregunta abierta: ¿se incluyen ya los resolvers de `doctor` (`doctor_to_school`) y `representante` (`parent`), o se agregan cuando se necesiten?

## Criterios de aceptación
- [ ] Existe `app/services/tenancy.py` con `get_school_id_for_admin` documentado (estilo Google, `Raises`).
- [ ] Ningún servicio repite la consulta a `school_administrator` para resolver el `school_id` (`grep -rn 'table("school_administrator")' app/services`).
- [ ] Los endpoints existentes responden igual que antes (mismos 403/404/200).
- [ ] Tests en `tests/` cubren el helper: usuario vinculado → `school_id`; no vinculado → 403.
- [ ] Las notas "pendiente de crear / interino" se retiran de `AGENTS.md`, reglas y skills.

## Referencias
- `.agents/rules/tenant-isolation.md`, `.agents/AGENTS.md` §3.
- Skills `vitaly-tenant-isolation`, `vitaly-module-scaffold`, `vitaly-architecture`, `vitaly-feature-testing`.
