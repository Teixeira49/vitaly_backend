---
name: rules-creator
description: Design, write, structure, and standardize operational rules for AI agents following modern industry standards (.mdc, AGENTS.md, role constraints, and few-shot examples). Use when creating or refining rules for AI agents.
---

# Rules Creator

This skill guides the creation, structuring, and refinement of deterministic operational rules for AI coding agents. It enforces the 5-part anatomical standard (Scope, Hard Constraints, Prescriptive Directives, Few-Shot DO/DON'T Examples, and Self-Verification), ensuring high agent compliance while optimizing token consumption.

---

## When to use this skill

- Use when asked to **create a new rule** for AI agents (e.g., Cursor `.mdc` rules, hierarchical `AGENTS.md`, or Antigravity rules).
- Use when **formalizing project guidelines**, architectural patterns, or PR review feedback into automated agent instructions.
- Use when **auditing or improving existing rules** that are vague, overly broad, or frequently ignored by the agent.
- Use when configuring role-based boundaries or domain-specific constraints (security, multi-tenancy, API standards).

---

## The 5-Part Standard Anatomy of an AI Rule

Every high-performance rule must follow this deterministic anatomy:

| Component | Purpose | Best Practice |
| :--- | :--- | :--- |
| **0. Frontmatter (YAML)** | Triggering & Scoping | Include `description`, precise `globs`, and `alwaysApply: false` unless universally required. |
| **1. Scope & Context** | Domain definition | Specify targeted files, layers, and active roles. |
| **2. Hard Constraints** | Non-negotiable boundaries | Explicit "walls": what the agent must **NEVER** do (security, tenant leakage, forbidden imports). |
| **3. Prescriptive Directives** | Actionable implementation | Prescriptive statements: *"Use X instead of Y"* rather than vague advice (*"write clean code"*). |
| **4. Few-Shot Examples** | Eliminating hallucinations | Direct contrast between **❌ DON'T** (Anti-Pattern) and **✅ DO** (Approved Standard). |
| **5. Self-Verification** | Closed-loop validation | Concrete tests, linters, or checklists the agent runs before declaring the task done. |

---

## Step-by-Step Workflow

### Step 1: Identify Target & Scope
Determine the scope and format of the rule:
- **Targeted files**: What directory or glob pattern does this rule govern? (e.g. `app/api/**/*.py`).
- **Format**:
  - Use `.mdc` for file-scoped, event-triggered rules (e.g., `.cursor/rules/name.mdc` or `.agents/rules/name.mdc`).
  - Use Markdown for directory-wide or ecosystem guidelines (e.g., `AGENTS.md` or `.agents/AGENTS.md`).

### Step 2: Scaffold the Rule
Run the scaffolding helper script with `--help` or execute directly:
```bash
./.agents/skills/rules-creator/scripts/scaffold-rule.sh \
  --name "fastapi-endpoint-standards" \
  --description "Enforces response envelopes, multi-tenant isolation, and RBAC on API routes" \
  --globs "app/api/**/*.py" \
  --type "mdc" \
  --output-dir ".cursor/rules"
```
*(Alternatively, reference the templates in `resources/rule-template.mdc` or `resources/agents-rule-template.md`).*

### Step 3: Populate Content with Concrete Directives
1. **Define Hard Constraints:** Use strong callouts (⛔ **NEVER**, 🔒 **MANDATORY**).
2. **Write Prescriptive Directives:** Detail the architectural flow (e.g., `Route -> Service -> Repository`).
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

## Decision Tree: Choosing Rule Format & Location

```text
Where should the rule live?
│
├── Is it scoped to specific file paths or extensions?
│   └── YES: Use .mdc with 'globs' in .cursor/rules/ or .agents/rules/
│            Set 'alwaysApply: false' and provide a descriptive 'description'.
│
└── Is it a global repository policy, multi-agent hierarchy, or workflow guide?
    ├── YES (Multi-agent architecture / ecosystem):
    │   └── Place in AGENTS.md or .agents/AGENTS.md
    └── YES (Universal coding style / project-wide security):
        └── Use .mdc with 'alwaysApply: true' OR root AGENTS.md
```

---

## Bundled Resources & References

- **Rule Template (.mdc):** [rule-template.mdc](file://resources/rule-template.mdc)
- **Agent Guidelines Template (.md):** [agents-rule-template.md](file://resources/agents-rule-template.md)
- **Reference Example (FastAPI):** [fastapi-route-rule.mdc](file://examples/fastapi-route-rule.mdc)
- **Scaffold Script:** [scaffold-rule.sh](file://scripts/scaffold-rule.sh)
