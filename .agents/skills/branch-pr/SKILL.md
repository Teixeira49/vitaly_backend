---
name: branch-pr
description: >
  PR creation workflow for estei-empresas. Overrides the global branch-pr skill
  with project-specific conventions: branching from develop, existing labels,
  CI pipeline, and PR template.
  Trigger: When creating a pull request, opening a PR, or preparing changes for review.
license: Apache-2.0
metadata:
  author: estei-empresas
  version: '1.0'
---

## When to Use

Use this skill when:

- Creating a pull request for any change
- Preparing a branch for submission
- Pushing changes that need review

---

## Critical Rules

1. **Every PR MUST link an issue** via `Closes #N`, `Fixes #N`, or `Resolves #N` — except `chore/` and `ci/` branches
2. **Every PR MUST add the matching label** from the project's label set
3. **Branches ALWAYS from `develop`**, NEVER from `main` — except `hotfix/*` from `main`
4. **PRs ALWAYS target `develop`** — except promotions (`develop` -> `staging` -> `main`) and hotfixes
5. **No `Co-Authored-By`** trailers in commits

---

## Workflow

```
1. Verify issue exists (create one if needed)
2. Create branch from develop: type/description
3. Implement changes with conventional commits
4. Push branch
5. Open PR using the template (.github/PULL_REQUEST_TEMPLATE.md)
6. Add the matching label
7. Wait for CI to pass
```

---

## Branching Strategy

This project uses **GitHub Flow + Staging Gate** (see `CONTRIBUTING.md`):

```
feat/my-feature --PR--> develop --PR--> staging --PR--> main
                          CI full       CI light        CI light
```

### Protected branches

| Branch    | Role                | Receives PRs from                          |
| --------- | ------------------- | ------------------------------------------ |
| `develop` | Daily integration   | `feat/*`, `fix/*`, `refactor/*`, `chore/*` |
| `staging` | Pre-production / QA | `develop`                                  |
| `main`    | Production          | `staging`, `hotfix/*`                      |

### Hotfixes

```
hotfix/critical-bug --PR--> main --backport--> develop
                              CI full
```

1. Create `hotfix/*` from `main` (NEVER from develop)
2. PR to `main` — CI runs FULL pipeline
3. **Mandatory backport**: after merge to main, open PR `main -> develop` or cherry-pick

---

## Branch Naming

Branch names MUST match:

```
^(feat|fix|chore|docs|style|refactor|perf|test|build|ci|revert|hotfix)\/[a-z0-9._-]+$
```

**Format:** `type/description` — lowercase, no spaces, only `a-z0-9._-` in description.

Including the ticket number is encouraged when there's a Jira/GitHub issue:

```
feat/empw-123-user-registration
fix/empw-456-iva-calculation
refactor/resolve-tech-debt-381
chore/upgrade-drizzle
hotfix/critical-payment-bug
```

---

## Labels

This project uses simple labels. Map commit types to existing labels:

| Commit type | Label to add    |
| ----------- | --------------- |
| `feat`      | `enhancement`   |
| `fix`       | `bug`           |
| `docs`      | `documentation` |
| `refactor`  | `tech-debt`     |
| `chore`     | (none required) |
| `perf`      | `enhancement`   |
| `test`      | (none required) |
| `build`     | (none required) |
| `ci`        | (none required) |

If the PR addresses tech debt, ALWAYS add `tech-debt` regardless of commit type.

---

## Issue Linkage

### Required (default)

Every PR body MUST contain one of:

```markdown
Closes #<issue-number>
Fixes #<issue-number>
Resolves #<issue-number>
```

### Exempt branches

PRs from these branch types do NOT require issue linkage:

- `chore/*` — maintenance, dependency updates, config changes
- `ci/*` — CI/CD pipeline changes

For exempt PRs, omit the `Closes #N` line. The Summary section is still required.

---

## PR Body Format

Use the template at `.github/PULL_REQUEST_TEMPLATE.md`. Sections:

### 1. Linked Issue (required except for chore/ci)

```markdown
Closes #123
```

### 2. Summary (always required)

1-3 bullet points explaining WHAT and WHY. Focus on motivation, not implementation.

### 3. Changes Table (required for PRs with 5+ files)

```markdown
| File           | Change       |
| -------------- | ------------ |
| `path/to/file` | What changed |
```

For small PRs (< 5 files), the Summary is sufficient.

### 4. Test Plan (always required)

```markdown
- [x] Tests pass: `npx vitest run`
- [x] TypeScript compiles: `npx tsc --noEmit`
- [x] No new lint errors in changed files
- [ ] Manually tested affected functionality (if UI change)
```

---

## Conventional Commits

Follow `CONTRIBUTING.md`. Format:

```
type(scope): description
```

### Types

`feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`, `ci`, `build`, `revert`

### Common scopes

| Scope       | Area                    |
| ----------- | ----------------------- |
| `users`     | User management         |
| `companies` | Companies/Organizations |
| `bookings`  | Reservations            |
| `invoices`  | Billing                 |
| `payments`  | Payments                |
| `auth`      | Authentication          |
| `api`       | REST API                |
| `ui`        | UI components           |
| `db`        | Database                |
| `estei`     | Estei API integration   |

### Rules

1. English for commit messages
2. Lowercase first letter in description
3. No period at end
4. Max 72 characters in first line
5. Imperative mood: "add" not "added" or "adding"
6. Breaking changes: add `!` after type/scope

---

## CI Pipeline

PRs to `develop` run the **full** pipeline:

| Job               | What it checks                                              |
| ----------------- | ----------------------------------------------------------- |
| `static-analysis` | ESLint + Prettier format + TypeScript typecheck             |
| `tests`           | `npm run test:coverage` (Vitest)                            |
| `build`           | `npm run build` (Vite client + esbuild server)              |
| `migration-check` | Drizzle schema drift detection                              |
| `analysis`        | `npm audit` + dead code check (informational, never blocks) |
| `ci-passed`       | Gate — all required jobs must pass                          |

### Before pushing, verify locally

```bash
npx vitest run          # tests pass
npx tsc --noEmit        # typecheck clean
npx eslint <files>      # no new errors in changed files
```

---

## Commands

```bash
# Create branch from develop
git checkout develop && git pull origin develop
git checkout -b feat/empw-123-my-feature

# Push and create PR
git push -u origin feat/empw-123-my-feature
gh pr create --base develop \
  --title "feat(scope): description" \
  --label "enhancement" \
  --body "Closes #123

## Summary

- What this PR does and why
"

# Add label if not set during creation
gh pr edit <pr-number> --add-label "enhancement"
```
