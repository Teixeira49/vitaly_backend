# Adversarial confirmation phase

Purpose: confirm criteria before the reviewer deliberates. Two blind judges assess the SAME candidate findings with identical criteria. A finding is trustworthy only when both agree. This kills alarmism: a lone "critical" that the other judge downgrades to theoretical does NOT become a blocker.

## When to delegate vs. fallback

- If dedicated adversarial review subagents exist → delegate both IN PARALLEL with the same prompt.
- By default (no external judges configured) → apply the two-lens fallback inline: run Lens A and Lens B as two separate honest passes, then synthesize as if they were two judges.

## Judge prompt (both judges, identical)

```markdown
You are an adversarial PR reviewer. Your ONLY job is to judge the candidate findings honestly.

## Ticket context
{ticket / business description}

## Target
{diff, files, feature}

## Candidate findings
{the drafted findings across the three families}

## Criteria (three fault families)
1. Business logic — behavior vs. ticket intent, missing cases, broken invariants.
2. Technical — correctness, resource use, API/schema contracts, missing tests.
3. Security — injection, authZ/authN gaps, sensitive-data exposure, input trust.

## For each candidate finding return
- Verdict: REAL FAULT | WARNING (real) | WARNING (theoretical) | NOT A FAULT
- Family: business-logic | technical | security
- Anchor: file:line or named missing behavior
- Why: one line, evidence-based
WARNING rule: normal intended use can trigger it → (real); contrived/malicious/impossible path → (theoretical).
No praise. Findings only. Do not invent faults absent from the diff.
```

## Two-lens fallback (no jd agents)

- Lens A (prosecution): assume each candidate IS a real fault; state the strongest evidence from the diff.
- Lens B (defense): assume each candidate is theoretical/non-blocking; state why normal use never triggers it.
- A finding survives as `Confirmed` only if Lens B fails to neutralize it.

## Synthesis rules

| Judge A | Judge B | Result |
|---------|---------|--------|
| REAL/WARNING (real) | REAL/WARNING (real) | **Confirmed** — can be a blocker |
| REAL | NOT A FAULT / theoretical | **Suspect** — report, do not block |
| theoretical | theoretical | **INFO** — report, never block |
| REAL | contradictory reasoning | **Escalate** — human decides |

Approved-for-verdict criterion: zero `Confirmed` high-severity findings → lean APRUEBO. Any `Confirmed` high-severity fault tied to a ticket criterion → CAMBIOS.

## Re-check after fixes

If the reviewer fixes confirmed findings during the session, re-run this phase on the changed lines before issuing the final verdict. Do not approve on a stale judgment.
