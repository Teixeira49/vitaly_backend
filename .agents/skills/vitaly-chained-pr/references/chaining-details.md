# Chained PR Details

> Vitaly conventions: base branch is `development` (hotfix chains use `main`).
> Branch names follow `.agents/rules/branch-naming.md`; PR titles and bodies follow
> `.agents/rules/pull-request.md`; commits follow `.agents/rules/commit-conventions.md`.
> `GH-12` below is a placeholder GitHub issue number (`GH-<n>`).

## Strategy Notes

| | Stacked PRs to `development` | Feature Branch Chain |
|---|---|---|
| Speed | Each slice can ship in order | Full feature waits for tracker merge |
| Rollback | Revert individual PRs on `development` | Revert/hold the whole feature branch |
| Risk | Partial behavior may land | Nothing lands until the chain completes |
| Complexity | Simpler retarget/rebase flow | Requires tracker and strict diff hygiene |

## Feature Branch Chain

Use when the feature branch accumulates the final integration while child PRs are reviewed as focused slices.

```text
development
 └── feat/GH-12                 ← tracker/final integration branch
      ↑ PR #1 base: feat/GH-12
      └── feat/GH-124
           ↑ PR #2 base: feat/GH-124
           └── feat/GH-125
                ↑ PR #3 base: feat/GH-125
                └── feat/GH-126
```

Child branches use their own GitHub issue numbers (`GH-<n>`). If the slices share one ticket,
apply the attempt rule from `branch-naming.md` (`feat/GH-12-1`, `feat/GH-12-2`...).

Steps:

1. Create the feature/tracker branch from an up-to-date `development` (`main` only for a hotfix chain).
2. Open the tracker PR to `development`; mark it draft/no-merge.
3. Create PR #1 from a child branch and target it to the tracker branch.
4. Create each later child branch from the previous PR branch and target it to that parent branch.
5. Merge/integrate children in order; merge the tracker only after the chain is complete.

## Stacked PRs to the Base Branch

Use when each slice can land on `development` in order.

```text
development <- PR 1: foundation
          └── PR 2: feature slice built on PR 1
                └── PR 3: docs/tests built on PR 2
```

After a parent PR merges, rebase/retarget the next PR so GitHub shows only the current slice.

## Chain Context Section

Append this section after the mandatory sections from `.agents/rules/pull-request.md` (Description, Type of Change, ¿Cómo se ha probado esto?, Lista de Verificación); never replace them.

```markdown
## Chain Context

| Field | Value |
|-------|-------|
| Chain | <feature or stack name> |
| Tracker PR | <#NNN or "Not needed"> |
| Position | <N of total> |
| Base | `<target branch>` |
| Depends on | <PR/issue/link or "None"> |
| Follow-up | <next PR or "None"> |
| Review budget | <changed lines> / 400 |
| Starts at | <branch, PR, or state this builds on> |
| Ends with | <standalone result delivered by this PR> |

### Chain Overview

```text
development
 └── #NNN Previous PR
      └── 📍 #NNN This PR
           └── #NNN Next PR
```

### Scope
- Includes: <focused unit>
- Excludes: <deferred work>

### Autonomy
- [ ] CI is expected to pass for this PR branch
- [ ] This PR has one deliverable scope
- [ ] This PR can be rolled back without unrelated changes
- [ ] Tests, docs, or manual verification cover this unit
```

## Commands

```bash
gh pr view <PR_NUMBER> --json additions,deletions,changedFiles,title,url
# Tracker PR (draft, no-merge) against the base branch
gh pr create --draft --base development --head feat/GH-12 \
  --title "[✨ Feat: GH-12] - Student health dashboard" \
  --body-file docs/pull-requests/feat-GH-12.md

# Child PRs target their immediate parent branch
gh pr create --base feat/GH-12 --head feat/GH-124 \
  --title "[✨ Feat: GH-124] - Student metrics schemas and service" \
  --body-file docs/pull-requests/feat-GH-124.md
gh pr create --base feat/GH-124 --head feat/GH-125 \
  --title "[✨ Feat: GH-125] - Student metrics endpoints" \
  --body-file docs/pull-requests/feat-GH-125.md

# Commits inside each slice use gitmoji Conventional Commits
git commit -m "✨ feat(metrics): add StudentMetricRead schema and service"
```

## Reviewer Guidance

- Ask for a split when a PR exceeds 400 changed lines without `size:exception`.
- Recommend Feature Branch Chain when work must integrate before reaching `development`.
- Recommend stacked PRs when each slice can merge independently into `development`.
- Respect `triggerMode` in `.claude/pr-config.json` (default `manual`: write the PR markdown, do not push).
- Review child PRs against immediate parent branches; a polluted diff is a branching bug.
