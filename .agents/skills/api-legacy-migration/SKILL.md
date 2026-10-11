---
name: api-legacy-migration
description: "Trigger: editing files under apps/api/src/components/ for maintenance or bug-fix. Apply Boy Scout rule only when <50 lines and isolated."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activates on: "editing apps/api/src/components/", "extending legacy component",
"fixing bug in components/", "updating {name} in components/".

**Scope: applies ONLY when touching existing `components/` code.** For new features → `api-module-pattern` instead.

---

## Hard Rules

| Rule ID | Rule |
|---------|------|
| SK5-R1 | When touching any `components/` file, MUST evaluate migration eligibility BEFORE writing code |
| SK5-R2 | Migration permitted ONLY IF: function/class is <50 lines AND no cross-deps on other `components/` files (BOTH conditions required) |
| SK5-R3 | If ineligible: MUST add `// TODO: [TECH-DEBT] migrate to modules/<name> - blocked by: <dep1>, <dep2>` comment |
| SK5-R4 | If migration is done: it MUST be in a SEPARATE commit from the original fix |
| SK5-R5 | If migration would push the PR over 400 changed lines: defer migration entirely |
| SK5-R6 | **The original fix MUST always ship even when migration is deferred — migration MUST NEVER block a fix** |

---

## Decision Gates

| Condition | Action |
|-----------|--------|
| Function <50 lines AND no cross-deps on other `components/` files | Migrate to `modules/` in a separate commit |
| Function ≥50 lines OR has cross-component deps | Leave TODO comment; ship original fix only |
| Migration would push PR >400 changed lines | Defer migration; original fix ships alone |
| Hotfix with time constraint | Skip migration evaluation; TODO comment only |

---

## Execution Steps

1. Before writing any code, check two conditions:
   - Is it **<50 lines**?
   - Does it import from other `components/` files?

2. If NOT eligible (fails either condition): add a `[TECH-DEBT]` comment, then ship the fix only:

```typescript
// TODO: [TECH-DEBT] migrate to modules/payment - blocked by: reservationCore, notificationCore
function calculateFee(amount: number): number {
  // original fix goes here
}
```

3. If ELIGIBLE (<50 lines, no cross-deps): write the fix first, commit it, then migrate in a second commit:

```bash
# Commit #1 — original fix (SK5-R6: fix ships first, independent of migration)
git commit -m "fix(api): correct fee calculation rounding"

# Commit #2 — migration in a separate commit
git commit -m "refactor(api): migrate calculateFee to modules/payment"
```

4. **SK5-R6 safety check**: Confirm the fix is in commit #1 and ships independently.
   If migration is reverted or deferred, the fix MUST still land.

---

## Output Contract

Agent confirms ALL of:
- [ ] Migration eligibility evaluated before writing any code
- [ ] If migrated: fix and migration are separate commits; fix commit is always first
- [ ] If not migrated: `// TODO: [TECH-DEBT]` comment added with blocking deps listed
- [ ] **SK5-R6**: Original fix is in its own commit and does NOT depend on migration being merged

---

## Anti-Patterns

- ❌ Blocking the fix while awaiting migration decision — SK5-R6 forbids this
- ❌ Migrating a function that has cross-component deps — creates new circular dependencies
- ❌ Mixing fix + migration in a single commit — defeats work-unit-commits and makes revert messy
