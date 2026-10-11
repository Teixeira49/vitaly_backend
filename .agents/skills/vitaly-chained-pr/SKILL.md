---
name: vitaly-chained-pr
description: "Trigger: PRs over 400 lines, stacked PRs, review slices in Vitaly backend. Split oversized changes into chained PRs targeting development, following the repo branch/PR/commit rules. Use this instead of the generic global chained-pr skill in this repository."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Load this skill when a planned PR may exceed **400 changed lines**, SDD forecasts `400-line budget risk: High` or `Chained PRs recommended: Yes`, or the user asks for chained/stacked PRs, review slices, or reviewer-load control.

## Repository Conventions (Vitaly)

Sources of truth — this skill never overrides them:

- `.agents/rules/branch-naming.md` — branch base and names (`feat/GH-12`, `fix/GH-12-1`...).
- `.agents/rules/pull-request.md` — PR target, title format, mandatory description sections, `triggerMode`.
- `.agents/rules/commit-conventions.md` — gitmoji Conventional Commits (`✨ feat(scope): subject`).

| Item | Value |
|---|---|
| Default PR base | `development` (`baseBranch`) |
| Hotfix PR base | `main` (`productionBranch`) — only for `hotfix/` branches |
| `staging` | Not covered by any rule: never target it without explicit user confirmation |
| PR title | `[<icon> <Type>: GH-<n>] - <issue title>` (e.g. `[✨ Feat: GH-12] - Paginated student list`) |
| Commits | `<emoji> type(scope): subject` per the mandatory type → emoji table |

"Main" in generic stacked-PR literature means **the repo base branch**: here that is `development` (or `main` only when the whole chain is a hotfix).

## Hard Rules

- Split PRs over **400 changed lines** unless a maintainer explicitly accepts `size:exception`.
- Keep each PR reviewable in about **≤60 minutes**.
- Use one deliverable work unit per PR; keep tests/docs with the unit they verify.
- State start, end, prior dependencies, follow-up work, and out-of-scope items in every chained PR.
- Every child PR must include a dependency diagram marking the current PR with `📍`.
- In Feature Branch Chain, create a draft/no-merge tracker PR; child PR #1 targets the tracker branch, later children target the immediate parent branch.
- Treat polluted diffs as base bugs: retarget or rebase until only the current work unit appears.
- Do not mix chain strategies after the user chooses one.

## Decision Gates

| Condition | Action |
|---|---|
| PR ≤400 changed lines and focused | Keep single PR. |
| PR >400, each slice can land independently | Use Stacked PRs to the base branch (`development`). |
| PR >400, feature must integrate before reaching `development` | Use Feature Branch Chain with tracker. |
| Generated/vendor/migration diff cannot split cleanly | Ask maintainer for `size:exception`. |
| SDD provides `delivery_strategy` | Follow it before apply/PR creation. |

## Execution Steps

1. Estimate changed lines and identify independent work units.
2. Ask for a chain strategy when none is cached and the budget is exceeded.
3. Create branches/PRs using the chosen strategy only.
4. Add Chain Context to each PR without replacing the mandatory sections from `.agents/rules/pull-request.md` (Description, Type of Change, ¿Cómo se ha probado esto?, Lista de Verificación).
5. Verify each PR independently: CI/tests/docs/manual checks, rollback scope, and clean diff.
6. Keep tracker PR draft/no-merge until all child PRs are reviewed and integrated.

## Output Contract

Return the chosen strategy, PR order, current PR boundary, dependency diagram, review budget (`additions + deletions`), verification plan, and any `size:exception` rationale.

## References

- [references/chaining-details.md](references/chaining-details.md) — strategy diagrams, PR body section, branch commands, and reviewer guidance.
