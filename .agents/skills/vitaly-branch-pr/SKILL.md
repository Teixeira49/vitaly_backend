---
name: vitaly-branch-pr
description: >
  GitHub-Issues-driven branch, commit, and pull request workflow for Vitaly backend.
  Orchestrates the repo rules (branch-naming, commit-conventions, pull-request)
  without restating them. Use this instead of the generic global branch-pr skill
  in this repository. Trigger: creating a branch, committing for review,
  or creating, opening, or preparing a pull request.
metadata:
  author: vitaly
  version: '2.0'
---

## Source of Truth

This skill only orchestrates. Formats live in the rules. If they conflict with this file, the rules win:

| Concern | Rule |
| --- | --- |
| Branch base, name, intento suffix | `.agents/rules/branch-naming.md` |
| Commit header, gitmoji mapping | `.agents/rules/commit-conventions.md` |
| PR title, body sections, triggerMode, labels, reviewers, base | `.agents/rules/pull-request.md` |

Read the relevant rule before you act. Do not copy formats from memory.

## Hard Constraints

- Do not open a PR against `productionBranch` unless the branch is `hotfix/*`.
- In `manual` mode, write the draft only. Do not commit, push, or open a PR.
- In `ask` mode, wait for the user's explicit written approval before `gh pr create`.
- Do not add `Co-Authored-By` or AI attribution trailers.
- Do not mix backend and frontend (`../vitaly-care-for-families`) changes in one commit or PR.
- Do not write absolute local paths in branch names, commits, drafts, or PR bodies.
- Follow the `git-safety` skill before any destructive git operation.

## Workflow

### 1. Load config

Read `.claude/pr-config.json`. If it is missing, use these defaults and tell the user the file should be created:

```json
{
  "triggerMode": "manual",
  "draftsDir": "docs/pull-requests/",
  "reviewers": [],
  "baseBranch": "development",
  "productionBranch": "main"
}
```

### 2. Resolve the GitHub issue

Vitaly tracks work in **GitHub Issues** (not Jira).

- Ask for the issue number (for example `12`) if you don't have it.
- Fetch it with `gh issue view <n> --json title,body,labels,state`, and keep `title`, `body`, `labels[].name`, and `state`. Warn the user if `state` is `CLOSED`.
- If `gh` fails, ask the user to paste the issue title and labels.
- If there is no issue, offer to file one first with the `vitaly-issue` skill. If the user declines, ask what the work is so you can pick the branch `tipo`, then use the no-issue naming case.

### 3. Create the branch (skip if it already exists)

1. Choose the base: `productionBranch` for `hotfix`, otherwise `baseBranch`.
2. Build the base name from `branch-naming.md`: `<tipo>/GH-<n>` (for example `feat/GH-12`), with no descriptive title.
3. Apply the intento rule by checking local and remote branches:
   ```bash
   git branch --list "<name>"
   git ls-remote --heads origin "<name>"
   ```
   Then try `<name>-1`, `<name>-2`, and so on until a name is free.
4. Create it:
   ```bash
   git checkout <base> && git pull && git checkout -b <name>
   ```

### 4. Plan and write commits

- Split the work into reviewable units. Use the `work-unit-commits` skill, and `vitaly-chained-pr` if the diff is over 400 lines.
- Write each header in the gitmoji format from `commit-conventions.md`, and keep the commit `type` consistent with the branch `tipo`.
- Before each commit, run `git status` and `git diff --staged`.
- Before pushing, run `pytest` (at least `pytest tests/`). Note the result for the PR checklist.

### 5. Generate the PR draft (always)

1. Collect commits from the PR base, not from `main` blindly:
   ```bash
   git log <pr-base>..<branch> --oneline --no-merges
   ```
2. Build the title `[<icon> <Type>: GH-<n>] - <issue title>` using the label → type mapping in `pull-request.md`. Show it in chat as the suggested title and apply any edits.
3. Build the body. Use `.github/pull_request_template.md` if it exists, otherwise the embedded template. Always include the four mandatory sections in order, and a `Closes #<n>` line in the description. Derive the test checklist from the real changes: endpoints, `curl` or `/docs` calls, and `pytest` targets.
4. Write it to `<draftsDir>/<branch-with-slashes-as-dashes>.md`.

### 6. Act on `triggerMode`

| Mode | Action |
| --- | --- |
| `manual` | Report the draft path and stop. |
| `ask` | Show the full draft, the PR base, reviewer candidates, and suggested labels. Wait for written approval. |
| `auto` | Infer labels, add only matching configured reviewers, and open the PR without asking. |

### 7. Open the PR (`ask` after approval, or `auto`)

```bash
git push -u origin <branch>
gh pr create --base <pr-base> --head <branch> \
  --title "<title>" --body-file "<draft-path>" \
  [--label "<label>" ...] [--reviewer "<user>" ...]
```

- `<pr-base>` is `productionBranch` for `hotfix/*`, otherwise `baseBranch`.
- The body must be the draft file, not rewritten text.
- If `gh` is unavailable, fall back to a GitHub MCP connector. If neither is available, behave as `manual`.
- Return the PR URL.
