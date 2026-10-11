---
name: api-feature-flags
description: "Trigger: adding, renaming, or removing a feature flag in estei (apps/api). A flag is a 3-place change across api schema, shared models type, and admin UI."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activates when adding, renaming, removing, reading, or toggling an estei feature flag.
Trigger phrases: "add a feature flag", "new flag", "feature flag", "toggle from admin",
"flag no aparece en admin", "gate X behind a flag".

The flag system is split across FOUR places that must stay in sync. A backend-only
change silently breaks the admin UI and the frontend typecheck, and a missing GraphQL
field makes the admin toggle appear to do nothing (it saves but the UI re-renders OFF).

---

## Hard Rules

| Rule ID | Rule |
|---------|------|
| SKFF-R1 | Adding a flag is a **4-place change**: (1) Mongoose schema in `apps/api/src/modules/feature-flags/infrastructure/feature-flags.model.ts`, (2) the shared `FeatureFlags` interface in `packages/models/src/models.ts`, (3) the hardcoded UI list in `apps/admin/components/feature-flags/utils.ts`, (4) the GraphQL `FeatureFlagsFragment` in `apps/admin/graphql/fragments.ts`. Skipping (2) breaks `apps/admin` `tsc --noEmit` (CI gate). Skipping (3) makes the flag invisible/untoggleable in admin. Skipping (4) makes the toggle SAVE on the backend but the admin re-render show OFF (the activate/deactivate mutation AND the GET_FEATURE_FLAGS query both select this fragment, so a missing field never reaches the UI). |
| SKFF-R2 | The admin dashboard does NOT render flags dynamically from the schema. `processFeatureFlags()` returns a hand-written array. A new flag MUST get its own `{ title, description, key, status }` entry there. |
| SKFF-R3 | `key` uses dotted notation ONLY for nested flags (e.g. `user.bill`, `payment.ubii`). Top-level flags have no dot (e.g. `sms`, `internationalOtp`). The dot determines how `getFeatureFlag` looks it up. |
| SKFF-R4 | Do NOT nest a flag under an existing single-word flag key (e.g. avoid `sms.international`): `getFeatureFlag` splits on `.`, so a nested key would collide with the parent category lookup. Use a dedicated top-level flag instead. |
| SKFF-R5 | Backend reads via `featureFlagsDomain.core.getFeatureFlag('key')` (or the module service). It throws if the key is absent from the loaded document — callers must handle a default. Existing env documents do NOT auto-gain new fields (Mongoose `default` applies on create only), so an unset flag reads as not-`on` → treat as OFF (default-deny). |
| SKFF-R6 | Activate/deactivate (`feature-flags.core.ts`) does NOT validate against a closed key list — `repo.update(flags, key, status)` accepts any schema key. So enabling a new top-level flag needs NO backend endpoint change. |
| SKFF-R7 | The admin `FeatureFlagsFragment` (`apps/admin/graphql/fragments.ts`) is a hand-written field selection used by BOTH the `GET_FEATURE_FLAGS` query and the activate/deactivate mutations. A new flag MUST be added to this fragment, mirroring the schema nesting. If skipped, the backend saves the toggle but the mutation/query response omits the field, so the dashboard re-renders the flag as OFF — the classic "toggle does nothing" symptom. |

---

## Decision Gates

| IF | THEN |
|----|------|
| Adding a brand-new flag | Do all 4 places (SKFF-R1). Default-deny semantics in the consumer. |
| Flag is conceptually nested under a multi-key category (e.g. `user.*`, `stay.*`) | Add it inside that category object in all 4 places; key is `category.subKey`. |
| Flag would nest under a single-word flag | STOP — use a top-level flag (SKFF-R4). |
| Flag added in a backend-only ticket/scope | Flag still must reach `packages/models` + both `apps/admin` files (UI list + GraphQL fragment), or QA cannot toggle it and CI typecheck fails. Flag it as cross-package work. |
| Admin toggle "saves but shows OFF" | The flag is missing from `FeatureFlagsFragment` (SKFF-R7). Add it there. |
| Just reading a flag in backend code | `featureFlagsDomain.core.getFeatureFlag(key)`; handle absence as OFF. |

---

## Execution Steps

1. **API schema** — add the field in `apps/api/src/modules/feature-flags/infrastructure/feature-flags.model.ts`:

```typescript
// top-level flag (no dot in key)
internationalOtp: { type: featureFlagSchema, default: {} },
// or nested under a category object (e.g. inside user: { ... })
```

2. **Shared type** — add the field to the `FeatureFlags` interface in `packages/models/src/models.ts` (mirror the schema nesting):

```typescript
internationalOtp?: FeatureFlag;
```

3. **Admin UI** — add an entry to the array returned by `processFeatureFlags()` in `apps/admin/components/feature-flags/utils.ts`:

```typescript
{
  title: 'OTP internacional',
  description: 'Texto de producto en español neutro explicando qué habilita el flag.',
  key: 'internationalOtp',          // dotted only if nested
  status: _flags?.internationalOtp?.status,
},
```

4. **Admin GraphQL fragment** — add the field to `FeatureFlagsFragment` in `apps/admin/graphql/fragments.ts`, mirroring the schema nesting (top-level or inside its category object):

```graphql
internationalOtp {
  ...FeatureFlagFragment
}
```

This fragment feeds BOTH `GET_FEATURE_FLAGS` (dashboard load) and the activate/deactivate mutations. Without it the toggle saves but the UI shows OFF.

5. **Verify locally** (CI-gate-relevant checks for a flag change):
   - `npx turbo run build --filter="@estei/models"` — shared type compiles.
   - `cd apps/admin && npx tsc --noEmit` — admin typechecks against the new field.

6. **Consumer** — read with `featureFlagsDomain.core.getFeatureFlag('internationalOtp')`; treat absent/`off` as disabled (default-deny).

---

## Output Contract

Agent confirms ALL of:
- [ ] Flag added in `feature-flags.model.ts` (api schema)
- [ ] Flag added in `packages/models/src/models.ts` (shared `FeatureFlags` type)
- [ ] Flag entry added in `apps/admin/components/feature-flags/utils.ts` (UI list)
- [ ] Flag added to `FeatureFlagsFragment` in `apps/admin/graphql/fragments.ts` (GraphQL selection)
- [ ] `@estei/models` build + `apps/admin` `tsc --noEmit` pass locally
- [ ] Consumer treats an unset flag as OFF (default-deny)

---

## Anti-Patterns

- ❌ Adding a flag only in the API schema (backend-only scope) — invisible in admin and breaks frontend typecheck.
- ❌ Nesting a flag under a single-word key like `sms.international` — collides with `getFeatureFlag`'s dotted lookup (SKFF-R4).
- ❌ Assuming an existing env document already has the new field — it does not until a `save()` materializes it; rely on default-deny.
- ❌ Adding backend key-validation for a new flag — the toggle accepts any schema key; no endpoint change needed.
- ❌ Adding a flag to the UI list but NOT to `FeatureFlagsFragment` — the toggle will save on the backend but the dashboard re-renders it OFF, looking like "the toggle does nothing" (SKFF-R7).
