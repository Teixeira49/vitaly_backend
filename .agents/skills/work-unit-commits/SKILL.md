---
name: work-unit-commits
description: "Plan commits as reviewable work units. Trigger: implementation, commit splitting, chained PRs, or keeping tests and docs with code."
license: Apache-2.0
metadata:
  author: gentleman-programming
  owner: vitaly-backend
  version: "1.1"
---

## When to Use

Load this skill when deciding what belongs in each commit or PR.

Use it for:

- Splitting a feature into reviewable work.
- Preparing commits before opening a PR.
- Turning a large change into chained or stacked PRs.
- Keeping reviewer cognitive load healthy.
- Applying SDD tasks without accidentally producing a PR above 400 changed lines.

## Commit Message Format

Source of truth: [`.agents/rules/commit-conventions.md`](../../rules/commit-conventions.md).
Every commit uses **Conventional Commits with gitmoji** (emoji first, mandatory type → emoji table):

```text
<emoji> type(scope): subject
```

| type | emoji | type | emoji |
|------|-------|------|-------|
| `feat` | ✨ | `perf` | ⚡ |
| `fix` | 🐛 | `test` | ✅ |
| `docs` | 📝 | `build` | 👷 |
| `style` | 💄 | `ci` | 💚 |
| `refactor` | ♻️ | `chore` | 🔧 |
| `revert` | ⏪ | | |

If this table and the rule ever disagree, the rule wins.

## Critical Rules

| Rule | Requirement |
|------|-------------|
| Commit by work unit | A commit represents a deliverable behavior, fix, migration, or docs unit. |
| Do not commit by file type | Avoid `models`, then `services`, then `tests` if none works alone. |
| Keep tests with code | Tests belong in the same commit as the behavior they verify. |
| Keep docs with the user-visible change | Docs belong with the feature or workflow they explain. |
| Tell a story | A reviewer should understand why each commit exists from its diff and message. |
| Future PR-ready | Each commit should be a candidate chained PR when the change grows. |
| SDD workload guard | If SDD tasks forecast a >400-line change, group commits into chained PR slices before implementation. |
| Independent repo commits | Never mix frontend and backend changes in a single commit (`cross-repo-e2e` rule). |

## Work Unit Checklist

Before committing, confirm:

- [ ] The commit has one clear purpose.
- [ ] The repo still makes sense after applying only this commit.
- [ ] Tests or docs for this unit are included when relevant.
- [ ] Rollback is reasonable without reverting unrelated work.
- [ ] The commit message explains the outcome, not the file list.

## Split Examples

| Weak split | Better work-unit split |
|------------|------------------------|
| `add schemas` | `✨ feat(students): add StudentRead schema and list endpoint with tests` |
| `add services` | `✨ feat(students): scope student queries by school_id` |
| `add tests` | Tests included with each behavior commit (`✅ test(...)` only for test-only changes) |
| `update docs` | Docs included with the user-facing change they explain |
| `fix stuff` | `🐛 fix(metrics): return empty list instead of 404 when no records exist` |
| `cleanup` | `♻️ refactor(services): extract BMI calculation into helper` |

## PR Relationship

Use work-unit commits as the foundation for chained PRs:

1. Build the smallest independent work unit.
2. Include verification for that unit.
3. Commit it with a gitmoji Conventional Commit message (`✨ feat(scope): subject`).
4. If the PR approaches 400 changed lines, promote commits or groups of commits into chained PRs.

## SDD Relationship

When `sdd-tasks` produces a Review Workload Forecast:

- Low risk: keep work-unit commits inside one PR.
- Medium risk: commit by work unit and monitor changed lines before PR creation.
- High risk: follow SDD `delivery_strategy` — ask on `ask-on-risk`, auto-slice on `auto-chain`, require `size:exception` on over-budget `single-pr`, or record accepted `size:exception` on `exception-ok`.

Each SDD work unit should map cleanly to a commit or PR with:

- clear start state,
- clear finished state,
- verification in the same unit,
- rollback that does not remove unrelated work.

## Commands

```bash
# Review the story before committing
git diff --stat
git diff --cached --stat

# Check recent commit style
git log --oneline -5

# Example commit (header format from .agents/rules/commit-conventions.md)
git commit -m "✨ feat(students): add paginated student list endpoint"
```
