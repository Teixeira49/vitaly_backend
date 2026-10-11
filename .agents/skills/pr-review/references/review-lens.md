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

- Correctness: null/undefined handling, off-by-one, unhandled promise/error, race conditions.
- Resource use: N+1 queries, unbounded loops, leaks, missing pagination.
- API contract: breaking changes to signatures, response shapes, or persisted schemas without migration.
- Testing: new behavior without tests; regression risk in touched paths.
- Maintainability (low severity unless it hides a bug): duplication, dead code, misleading names.

## 3. Security faults

Focus on what the diff introduces or exposes.

- Injection: SQL/NoSQL/command/XSS from unsanitized input reaching a sink.
- AuthZ/AuthN: missing or incomplete permission checks on new endpoints/mutations; privilege escalation.
- Sensitive data: secrets in code, PII in logs, tokens in responses, weak crypto.
- Input trust: missing validation on external input, mass-assignment, unsafe deserialization.
- Exposure: overly broad CORS, verbose error leaks, IDOR (object access without ownership check).

## Severity mapping

- `high`: security vulnerability, data loss, crash, or broken core behavior from the ticket.
- `medium`: performance, maintainability, or a real but non-critical edge case.
- `low`: style, readability, non-critical best practice.

Do not inflate severity to force a CAMBIOS verdict. The verdict follows from confirmed blockers, not from the number of findings.
