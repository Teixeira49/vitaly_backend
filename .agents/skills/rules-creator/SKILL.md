---
name: rules-creator
description: Design, write, structure, and standardize operational rules for AI agents following modern industry standards (.mdc, AGENTS.md, role constraints, and few-shot examples). Use when creating or refining rules for AI agents.
---

# Rules Creator

This skill guides the creation, structuring, and refinement of deterministic operational rules for AI coding agents. It enforces the 5-part anatomical standard (Scope, Hard Constraints, Prescriptive Directives, Few-Shot DO/DON'T Examples, and Self-Verification), ensuring high agent compliance while optimizing token consumption.

---

## When to use this skill

- Use when asked to **create a new rule** for AI agents (in this repo: `.agents/rules/<name>.md` + `.mdc` symlink, role files, or `.agents/AGENTS.md`).
- Use when **formalizing project guidelines**, architectural patterns, or PR review feedback into automated agent instructions.
- Use when **auditing or improving existing rules** that are vague, overly broad, or frequently ignored by the agent.
- Use when configuring role-based boundaries or domain-specific constraints (security, multi-tenancy, API standards).

---

## The 5-Part Standard Anatomy of an AI Rule

Every high-performance rule must follow this deterministic anatomy:

| Component | Purpose | Best Practice |
| :--- | :--- | :--- |
| **0. Frontmatter (YAML)** | Triggering & Scoping | Include `description`, precise `globs` (YAML list), and `alwaysApply: false` unless universally required. |
| **1. Scope & Context** | Domain definition | Specify targeted files, layers, and active roles. |
| **2. Hard Constraints** | Non-negotiable boundaries | Explicit "walls": what the agent must **NEVER** do (security, tenant leakage, forbidden imports). |
| **3. Prescriptive Directives** | Actionable implementation | Prescriptive statements: *"Use X instead of Y"* rather than vague advice (*"write clean code"*). |
| **4. Few-Shot Examples** | Eliminating hallucinations | Direct contrast between **❌ DON'T** (Anti-Pattern) and **✅ DO** (Approved Standard). |
| **5. Self-Verification** | Closed-loop validation | Concrete tests, linters, or checklists the agent runs before declaring the task done. |

---

## Step-by-Step Workflow

### Step 1: Identify Target & Scope
Determine the scope and location of the rule:
- **Targeted files**: What directory or glob pattern does this rule govern? (e.g. `app/api/**/*.py`).
- **Location (Vitaly)**: see "Where Rules Live in This Repo" below. File-scoped and always-on rules go in `.agents/rules/`; role definitions go in `.agents/roles/`; the multi-agent hierarchy lives in `.agents/AGENTS.md`.

### Step 2: Scaffold the Rule
Run the scaffolding helper from the repo root (preview first with `--dry-run`):
```bash
./.agents/skills/rules-creator/scripts/scaffold-rule.sh \
  --name "fastapi-endpoint-standards" \
  --description "Envelope APIResponse, gates get_current_* y aislamiento por school_id en rutas" \
  --globs "app/api/**/*.py,app/services/**/*.py" \
  --dry-run
```
Drop `--dry-run` to write `.agents/rules/<name>.md` and the `.agents/rules/<name>.mdc` relative symlink. Other flags: `--always-apply`, `--no-mdc-link`, `--output-dir <dir>`.
*(Alternatively, copy `resources/rule-template.md` by hand — then create the `.mdc` symlink yourself: `cd .agents/rules && ln -s <name>.md <name>.mdc`.)*

### Step 3: Populate Content with Concrete Directives
1. **Define Hard Constraints:** Use strong callouts (⛔ **NEVER**, 🔒 **MANDATORY**).
2. **Write Prescriptive Directives:** Detail the architectural flow (in Vitaly: `endpoint -> service singleton -> supabase-py client`; see skill `vitaly-architecture`).
3. **Craft Contrastive Code Examples (Crucial):**
   - Provide realistic, syntactically valid code snippets.
   - Show the exact mistake developers or agents commonly make (❌ DON'T).
   - Show the exact resolution conforming to the project architecture (✅ DO).
4. **Establish Self-Verification:** Provide exact shell commands or validation steps (e.g., `pytest tests/api/...`, `mypy`, `ruff`).

### Step 4: Token Optimization & Audit
Ensure the rule meets token budgeting best practices:
- **Conciseness:** Keep rules under 150–250 lines. Avoid explaining basic programming concepts the LLM already knows.
- **Single Responsibility Principle (SRP):** Split multi-concern rules into focused individual rules (e.g., separate database queries from HTTP route definitions).
- **Scope Tightening:** Restrict `globs` to the minimum necessary files. Avoid setting `alwaysApply: true` unless it is truly global.

---

## Where Rules Live in This Repo

```text
.agents/rules/<name>.md      ← canonical file (edit this one)
.agents/rules/<name>.mdc     ← relative symlink to <name>.md (Cursor discovery)
.claude/rules  → ../.agents/rules   (directory symlink)
.cursor/rules  → ../.agents/rules   (directory symlink)
.agents/AGENTS.md            ← orchestrator + role pointer table (CLAUDE.md, AGENTS.md, GROK.md,
                               .cursorrules, .github/copilot-instructions.md symlink to it)
.agents/roles/<role>.md      ← detailed role definitions
```

- ⛔ **NEVER** replace the `.cursor/rules` or `.claude/rules` directory symlinks with real directories; always create and edit rules through the canonical path `.agents/rules/`.
- ⛔ **NEVER** write rule content into the `.mdc`; it must stay a symlink to the `.md`.
- 🔒 **MANDATORY:** Frontmatter with `description` and `alwaysApply`; add `globs` (YAML list) when the rule is file-scoped. Workflow rules without globs (e.g. `branch-naming.md`) may use `description` only.
- 🔒 **MANDATORY:** Rule body follows the 5 sections with the repo's headings: `## 1. Scope & Context`, `## 2. Hard Constraints (Reglas Infranqueables)`, `## 3. Directivas Prescriptivas`, `## 4. Ejemplos Contrastados (Few-Shot)`, `## 5. Verificación & Auto-Corrección`.
- Rules are written in neutral professional Spanish (matching existing rules); code identifiers stay in English.
- No absolute local paths (`/Users/...`, `C:\...`) inside rules.

Verify after creating: `ls -la .agents/rules/<name>.*` must show the `.md` file and the `.mdc -> <name>.md` link.

---

## Decision Tree: Choosing Rule Location

```text
Where should the rule live?
│
├── Scoped to specific file paths?
│   └── .agents/rules/<name>.md with 'globs' + 'alwaysApply: false' (+ .mdc symlink)
│
├── Repository-wide workflow or policy (commits, branches, PRs)?
│   └── .agents/rules/<name>.md with 'alwaysApply: true' or description-only (+ .mdc symlink)
│
├── Defines what a specialist agent owns?
│   └── .agents/roles/<role>.md + one row in the role table of .agents/AGENTS.md
│
└── Orchestration / handoff / cross-cutting standards?
    └── .agents/AGENTS.md (edit in place; never break its symlinks)
```

---

## Bundled Resources & References

- **Rule Template:** [resources/rule-template.md](resources/rule-template.md)
- **Role / Guide Template (no frontmatter):** [resources/agents-rule-template.md](resources/agents-rule-template.md)
- **Reference Example (FastAPI):** [examples/fastapi-route-rule.md](examples/fastapi-route-rule.md)
- **Scaffold Script:** [scripts/scaffold-rule.sh](scripts/scaffold-rule.sh)
