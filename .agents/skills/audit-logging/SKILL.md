---
name: audit-logging
description: When and how Vitaly records audit entries for sensitive actions (student medical data/PHR access and changes, user/role approvals, cross-school admin actions, exports) via the shared supabase-py client from the service layer. Trigger: adding or modifying an operation on medical/PHR data, approvals, admin_sistema actions or data exports, or discussing traceability/audit trails.
metadata:
  owner: vitaly-backend
  format: agent-skills-v1
---

# Audit Logging (Vitaly)

## Current state (be honest)

- There is **no audit table** today: `supabase/migrations/` only contains user photo migrations, and `app/services/admin_service.py` has a comment ("audit log in the future") but no implementation.
- Creating the table is a schema change: follow `.agents/rules/database_migration_protocol.md` (impact report + exact SQL + **explicit user confirmation**) before any migration is written or applied. Never apply it yourself.

## When to audit

| Action | Example | Audit? |
|---|---|---|
| Read of student medical data / PHR | doctor opens a medical record, representante views a child's history | Yes (`read`) |
| Create/update/delete of medical data | consultation, vaccine, diagnosis, IMC metrics | Yes |
| User/role lifecycle | approve/reject a school admin or doctor, role change | Yes |
| Cross-school actions by `admin_sistema` | school detail, approvals, global queries | Yes |
| Data exports (CSV/Excel) | see `export-patterns` | Yes, always |
| Auth events | login failure bursts, logout | Optional, technical logging is enough |
| Catalog reads, health checks | `catalogs.py`, ping | No |

When in doubt about a PHR/medical operation, audit it.

## What to record

| Field | Source |
|---|---|
| `actor_id` | JWT `sub` (from the `get_current_*` gate payload) |
| `actor_role` | JWT `role` |
| `school_id` | resolved server-side (see `vitaly-tenant-isolation`); `null` only for global `admin_sistema` actions |
| `action` | `read` / `create` / `update` / `delete` / `approve` / `reject` / `export` |
| `entity` + `entity_id` | table name and primary key (e.g. `student`, `42`) |
| `changes` | before/after diff of **field names** and non-sensitive values; PHR values redacted |
| `metadata` | filters, record count (exports), reason |
| `request_id`, `ip` | from the request (pass down explicitly; services do not see `Request`) |
| `created_at` | DB default `now()` |

### PII / PHR minimization

- Never store diagnoses, notes, vitals or identity numbers in `changes`; record `{"field": "diagnosis", "changed": true}` instead.
- Never store tokens, passwords or full request bodies.
- The audit table itself is sensitive: readable only by `admin_sistema` (and, if needed later, by `admin_escuela` filtered by its `school_id`).

## Where and how

- Write from the **service layer**, after the main operation, using the global client from `app/core/database.py`. Endpoints only pass actor context.
- Append-only: no update/delete code paths; enforce with RLS/grants in the migration.
- Keep a small helper in a dedicated service (e.g. `app/services/audit_service.py`, module singleton like the other services) so call sites stay one line.

```python
import logging
from fastapi import HTTPException
from app.core.database import supabase

logger = logging.getLogger(__name__)

class AuditService:
    def record(self, *, actor: dict, action: str, entity: str, entity_id: str | int,
               school_id: int | None, changes: dict | None = None,
               metadata: dict | None = None, critical: bool = False) -> None:
        """Insert one append-only audit row.

        Raises:
            HTTPException: 500 only when ``critical`` is True and the insert fails.
                An HTTPException (not a bare re-raise) keeps the APIResponse error
                envelope, since app/main.py registers no generic Exception handler.
        """
        row = {
            "actor_id": actor["sub"], "actor_role": actor["role"],
            "school_id": school_id, "action": action, "entity": entity,
            "entity_id": str(entity_id), "changes": changes or {}, "metadata": metadata or {},
        }
        try:
            supabase.table("audit_log").insert(row).execute()
        except Exception:
            logger.exception("audit_log insert failed", extra={"entity": entity, "action": action})
            if critical:
                raise HTTPException(
                    status_code=500,
                    detail="The operation could not be audited and was not completed.",
                ) from None

audit_service = AuditService()
```

## Failure policy (decided)

| Kind | Policy |
|---|---|
| Reads of PHR, routine updates | **Best effort**: log the failure with `logger.exception` (never silently swallow) and let the main operation succeed. |
| Exports, role/user approvals, deletes of medical data | **Must succeed** (`critical=True`): if the audit insert fails, the request fails with 500 and, for exports, no file is sent. Record the audit before streaming. |

supabase-py has no multi-statement transactions, so a "must succeed" action cannot be rolled back atomically: perform the audit insert **before** irreversible side effects where possible (e.g. before an export, before a hard delete).

## Anti-patterns

- Auditing from endpoints with inline queries, or using the Supabase REST client from the frontend to write audit rows.
- `except: pass` around the audit insert.
- A bare `raise` on critical failures: it bypasses the `APIResponse` error envelope (only `HTTPException` and validation errors have global handlers).
- Copying the whole PHR row into `changes`.
- Trusting a `school_id` sent by the client for the audit row.

## Checklist

- [ ] The action is in the "When to audit" table and calls `audit_service.record(...)`.
- [ ] Actor comes from the gate payload (`sub`, `role`); `school_id` resolved server-side.
- [ ] No raw PHR values, tokens or passwords in `changes`/`metadata`.
- [ ] Failure policy matches the table (best effort vs `critical=True`).
- [ ] Any new table/column went through `database_migration_protocol.md` with user confirmation.
- [ ] Tests cover the audit call (see `vitaly-feature-testing`).
