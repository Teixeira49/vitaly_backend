---
name: vitaly-issue
description: "File GitHub Issues for Vitaly backend in the approved format: verified file:line evidence, type/priority/area labels, a reviewable draft in docs/issues/, and gh issue create only after explicit written approval. Trigger: creating, reporting or filing an issue, bug report, feature request, security finding, tech debt or chore ticket."
metadata:
  author: vitaly
  owner: vitaly-backend
  version: '1.0'
---

# Vitaly Issue — filing GitHub Issues

Vitaly tracks work in **GitHub Issues** (repo `Teixeira49/vitaly_backend`), not Jira.
Issues feed the branch name (`<tipo>/GH-<n>`, see `.agents/rules/branch-naming.md`) and the
PR title (`[<icon> <Type>: GH-<n>] - <title>`, see `.agents/rules/pull-request.md`). A vague
issue produces a vague branch, PR and fix. This skill makes every issue verifiable.

Human-facing equivalents live in `.github/ISSUE_TEMPLATE/` (bug, feature, security,
tech-debt). Keep them aligned with this file.

## Hard Constraints

- NEVER run `gh issue create`, `gh issue edit` or `gh label create` without the user's
  **explicit written approval** of that specific draft (e.g. "apruebo", "créalo", "adelante").
  Approval of an earlier draft does not cover a changed one.
- NEVER claim a defect you have not verified in the current code. Every claim needs
  `file:line` evidence or a reproducible command.
- NEVER paste secrets, tokens, `.env` values, real student/medical data (PHR/PII) or absolute
  local paths (`/Users/...`, `C:\...`) into a draft or issue. Use repo-relative paths and
  synthetic data.
- For **security** findings, describe impact and location, but do not publish a working
  exploit payload. If the repo is public and the finding is P0, ask the user whether to file
  it publicly or report it privately (GitHub Security Advisory) before filing.
- Issue title and body are in **neutral professional Spanish**. Code, paths and identifiers
  stay as written.

## Format

### Title

```
[<icon> <Tipo>] <descripción breve>
```

Keep it under ~80 characters, specific and observable (what fails, where).

| Tipo | Icon | Type labels |
| --- | --- | --- |
| Bug | 🐛 | `bug` |
| Feature | ✨ | `enhancement` |
| Seguridad | 🔒 | `security` + `bug` |
| Deuda técnica | ♻️ | `tech-debt` |
| Docs | 📝 | `documentation` |
| Chore | 🔧 | `chore` |

Plus exactly one **priority** label and one or more **area** labels:

| Priority | Meaning |
| --- | --- |
| `P0` | Data leak, auth bypass, PHR exposure or production down. Fix now. |
| `P1` | Broken core flow with no workaround. |
| `P2` | Wrong behavior or rule violation with a workaround or limited blast radius. |
| `P3` | Hygiene, tooling, minor inconsistency. |

| Area | Scope |
| --- | --- |
| `api` | `app/api/`, `app/main.py`, `app/core/exceptions.py`, routing, gates |
| `services` | `app/services/` |
| `schemas` | `app/schemas/` |
| `agents` | `.agents/`, rules, skills, roles |

### Body (Spanish headings, in this order)

```markdown
## Descripción
<Qué pasa, en 2-4 frases.>

## Evidencia
- `app/path/file.py:LINE` — <qué muestra esa línea>
- Request/response o comando de reproducción (`curl ...`, `pytest ...`, `grep -n ...`).

## Comportamiento actual vs esperado
- **Actual:** ...
- **Esperado:** ... (cita la regla si aplica)

## Impacto
- ¿Expone datos médicos/PHR o PII? ...
- ¿Fuga entre escuelas (school_id)? ...
- Roles afectados: ...

## Propuesta de solución
<Cambio sugerido. Si hay una decisión abierta, plantéala como pregunta; no la decidas.>

## Criterios de aceptación
- [ ] <Condición verificable, idealmente con un test o comando.>

## Referencias
- `.agents/rules/<rule>.md`, skill `<skill>`, issues relacionados.
```

## Workflow

### 1. Gather evidence

- Read the code involved. Record exact `file:line` for every claim (`grep -n`, `sed -n`).
- Prefer a reproduction: a `curl` against `uvicorn app.main:app`, a `pytest` target, or a
  `grep` that shows the gap.
- Check for duplicates: `gh issue list --state all --search "<keywords>"`. If one exists,
  propose a comment or edit on it instead of a new issue.

### 2. Classify

- Pick `Tipo` from the table. Auth bypass, missing gate, tenant leak or PHR exposure is
  always `Seguridad`.
- Pick priority with the table. When unsure between two levels, state both and ask.
- Pick area labels from the touched paths.

### 3. Write the draft

Write it to `docs/issues/<YYYY-MM-DD>-<slug>.md` (date from `date +%F`, slug in
lowercase kebab-case ASCII). Use YAML front matter so the draft carries its labels:

```markdown
---
title: "[🐛 Bug] <descripción breve>"
labels: [bug, P2, services]
issue: null
---

## Descripción
...
```

### 4. Show it and ask for approval

Show the user the full draft (title, labels, body) and list any labels that do not exist yet
(`gh label list --limit 200`). Ask one question: approve as is, or what to change. **Stop and
wait** for written approval.

### 5. Create (only after approval)

1. Create missing labels, covered by the same approval:
   ```bash
   gh label create "<name>" --description "<desc>" --color "<hex>"
   ```
2. Write the body (everything after the front matter) to a temp file in your scratchpad, then:
   ```bash
   gh issue create --title "<title>" --body-file "<body-file>" \
     --label "<type>" --label "<priority>" --label "<area>"
   ```
3. Return the issue URL to the user.

### 6. Update the draft

Set `issue:` in the front matter to the issue number and add `url: <issue URL>`. The draft
stays in `docs/issues/` as the local record. If the issue is later edited with
`gh issue edit`, update the draft to match.

## Checklist

- [ ] Every claim has `file:line` evidence verified against the current code.
- [ ] Title follows `[<icon> <Tipo>] ...`; labels = type + one priority + area(s).
- [ ] All seven body sections present, in order, in Spanish.
- [ ] `Impacto` answers PHR/PII, cross-school leak and affected roles.
- [ ] `Criterios de aceptación` are verifiable checkboxes.
- [ ] No secrets, real patient data or absolute local paths.
- [ ] Explicit written approval received before any `gh` write command.
- [ ] Draft updated with the issue number and URL.
