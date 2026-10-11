# Review Lens — three fault families

Apply against the diff, anchored to `path:line`. Honest, non-alarmist: only report what the code shows.

## 1. Business logic faults

Does the code do what the ticket says, and only that?

- Requirement mismatch: implemented behavior diverges from the ticket's intent.
- Missing case: a stated scenario (or an obvious edge case of it) is not handled.
- Wrong invariant: state transitions, calculations, or rules that violate the domain (e.g. money rounding, quantity going negative, expired-status handling).
- Scope creep / gap: changes beyond the ticket, or a stated acceptance criterion left uncovered.
- Silent data mutation: writes/deletes not implied by the ticket.

## 2. Technical faults

Is the change correct, maintainable, and safe to run?
*(For Vitaly backend, cross-check against the gates in `fastapi-code-review`)*

- Correctness: null/undefined handling, off-by-one, unhandled promise/error, race conditions.
- Sync/async discipline (G8): Handlers and services calling supabase-py must be sync `def` (FastAPI threadpool). Flag `async def` with blocking I/O calls.
- API contract & envelope (G3, G7): Endpoints must return `APIResponse[T]`. Schema changes must maintain contract parity with `../vitaly-care-for-families`.
- Empty vs. missing (G4): Empty collections return 200 + `data=[]` (never 404). 404 is strictly for missing single resources.
- Resource use: N+1 queries, unbounded loops, leaks, missing pagination.
- Testing: new behavior without tests; regression risk in touched paths.
- Maintainability & docs (G5, G6): Schema naming conventions, FastAPI endpoint docstrings and Google-style service docstrings.

## 3. Security faults

Focus on what the diff introduces or exposes.
*(For Vitaly backend, critical zero-tolerance areas)*

- AuthZ/AuthN (G1): missing or incomplete permission checks; route lacking both `Depends(get_current_*)` and `# PUBLIC_ROUTE`; inline role checks outside `deps.py`.
- Multi-tenancy & IDOR (G2): `school_id` taken from client input instead of server-resolved from user token `sub`; school-scoped queries missing school filter.
- Sensitive data & PII/PHR: student health records exposed across schools; secrets in code; password hashes in user responses; tokens leaked.
- Injection: SQL/NoSQL/command/XSS from unsanitized input reaching a sink.
- Input trust: missing validation on external input, mass-assignment, unsafe deserialization.

## Severity mapping

- `high`: security vulnerability, data loss, crash, or broken core behavior from the ticket.
- `medium`: performance, maintainability, or a real but non-critical edge case.
- `low`: style, readability, non-critical best practice.

Do not inflate severity to force a CAMBIOS verdict. The verdict follows from confirmed blockers, not from the number of findings.
