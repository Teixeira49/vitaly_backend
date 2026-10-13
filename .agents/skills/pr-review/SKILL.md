---
name: pr-review
description: "Trigger: review a pull request or diff against its linked GitHub issue (revisar PR, review pull request, revisa este PR, evaluar cambios de un PR). Honest non-alarmist PR review of business logic, technical, and security faults against a ticket description, with dual reviewer/agent explanations and a CUMPLE/APRUEBO verdict."
license: Apache-2.0
metadata:
  author: Holeekey
  owner: vitaly-backend
  version: "1.1"
---

# PR Review (Vitaly)

## Activation Contract

Use this skill when the user asks to review a pull request, diff, or set of changes against an initial description (e.g. the linked GitHub issue). Requires a business/context description of what the PR is supposed to do. If that context is missing, ask for it once before reviewing.

Do not use for: generating the PR description, writing commits, or unrelated refactors.

## Hard Rules

- Be HONEST and NON-ALARMIST. Report only faults you can justify from the actual diff. No hypothetical FUD, no padding.
- If you cannot point to a concrete line, file, or missing behavior, it is NOT a fault — omit it.
- Review exactly three fault families, in this order: (1) business logic, (2) technical, (3) security.
- Severity is evidence-based: `high` = security hole, data loss, crash, or broken core behavior; `medium` = performance, maintainability, edge cases; `low` = style/readability. Do not inflate.
- Every fault AND every failing criterion AND every blocker MUST carry BOTH explanations (reviewer + agent). No exceptions.
- Run the adversarial two-judge phase (step 5) to CONFIRM criteria before deliberating with the reviewer. A finding is `Confirmed` only when both judges agree it is a real fault; single-judge findings are `Suspect`; contradictions `Escalate`.
- Classify a warning as `WARNING (real)` only if normal intended use can trigger it; a contrived/malicious/impossible path is `WARNING (theoretical)` → downgrade to INFO, never a blocker.
- Never issue the final verdict until findings pass the adversarial phase AND have been deliberated with the reviewer (confirmed or discarded).
- Match the user's language in prose. Keep code, paths, and identifiers verbatim.

## Execution Steps

1. Confirm you have the ticket/context description. Vitaly uses GitHub Issues: take `<n>` from `GH-<n>` in the branch name or `Closes #<n>` in the PR body and fetch it with `gh issue view <n> --json title,body,labels,state`. If no issue or description is available, ask for it and stop.
2. Get the real code, not just a pasted diff. Prefer `gh pr diff <number>` plus reading touched files, or a separate git worktree of the PR branch (sibling directory under the user's home, e.g. `<repo-parent>/<repo-name>-worktrees/pr-<number>`, never `/tmp`) for full-context navigation and running tests. Only if you must switch the current checkout: FIRST verify the working tree is clean (`git status --porcelain`); if it has uncommitted changes or is mid-operation (rebase/merge), STOP and ask the user how to proceed. When clean, follow the `git-safety` skill before `gh pr checkout <number>`. If none of this is possible (detached environment, no local repo, permission), review the raw diff and note that limitation in the review.
3. Read the diff and only the surrounding code needed to judge it. Anchor every finding to `path:line` or a named missing behavior.
4. Draft candidate findings across the three fault families using `references/review-lens.md`. For files under `app/api/`, `app/services/` and `app/schemas/`, apply the `fastapi-code-review` gates (G1-G8) as candidate findings, using its severity mapping.
5. Run the adversarial confirmation phase (see `references/adversarial-phase.md`): launch two blind judges on the same target and criteria. Delegate in parallel if specialized adversarial review subagents exist; otherwise, apply the inline two-lens fallback yourself (Lens A = "prove this is a real fault"; Lens B = "prove it is theoretical/non-blocking"). Synthesize into the verdict table: `Confirmed`, `Suspect`, `Escalate`, `INFO`.
6. For each surviving finding, emit BOTH blocks (see Output Contract): reviewer explanation (cause→effect, non-technical) and agent explanation (code-oriented, for follow-up sessions). Mark its adversarial status.
7. Present findings to the reviewer for deliberation. Ask them to confirm or discard each one. Wait.
8. After deliberation, emit the final verdict block using only confirmed findings.

## Output Contract

### Per-fault block (during review)

```
#### [business-logic | technical | security] — <short title> (severity: high/medium/low)
- Para revisor: <cause → effect, plain language, no jargon>
- Para agente: <file:line, code-level detail, what to verify next>
```

Group faults under the three families. If a family has no faults, state "Sin hallazgos" for it — do not invent.

### Adversarial confirmation table (after step 5, before deliberation)

```
| Hallazgo | Juez A | Juez B | Severidad | Estado |
|----------|--------|--------|-----------|--------|
| <title @ file:line> | ✅/❌ | ✅/❌ | high/medium/low | Confirmed/Suspect/Escalate/INFO |
```

Only `Confirmed` findings can become blockers. `Suspect` and `INFO` are reported but do not force CAMBIOS. `Escalate` (judges contradict) requires human decision.

### Final verdict block (after deliberation)

```
Criterios del ticket: CUMPLE / NO CUMPLE — <por qué>
Blockers: <lista, o ninguno>
Veredicto: APRUEBO / CAMBIOS
```

Each unmet criterion and each blocker MUST itself follow the dual `Para revisor` / `Para agente` format defined above.

## References

- `references/review-lens.md` — checklist of the three fault families and severity mapping (Vitaly gates live in `fastapi-code-review`).
- `references/adversarial-phase.md` — two-judge confirmation: delegation prompts, two-lens fallback, and synthesis rules.
- Skill `fastapi-code-review` — Vitaly backend stack review gates (G1-G8: auth, tenant isolation, APIResponse, sync handlers, contract parity).
- Rule `.agents/rules/pull-request.md` — target branch (`development` / `main`) and PR format for Vitaly.
