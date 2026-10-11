---
name: api-module-pattern
description: "Trigger: creating or scaffolding a new estei API module in apps/api/src/modules/. Enforce hexagonal layout and ecosystem registration. New code only — not for legacy components/."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activates on: "new API module", "create module in modules/", "new hexagonal module",
"creating new feature in apps/api", "adding to modules/".

**Scope: new code in `modules/` ONLY — does not mandate migration of `components/`.**
Existing `components/` code is maintenance-only territory; do NOT redirect to this skill when
fixing bugs in `components/` (use `api-legacy-migration` instead).

Co-inject with `api-hexagonal-layers` whenever scaffolding a new module.

---

## Hard Rules

| Rule ID | Rule |
|---------|------|
| SK1-R1 | New feature code MUST go in `apps/api/src/modules/`, never in `components/` |
| SK1-R2 | Module folder MUST contain `domain/`, `application/`, `infrastructure/` sub-layers |
| SK1-R3 | Module class MUST implement lifecycle in order: `constructor()` → `setDependencies({...})` → `init()` |
| SK1-R4 | `init()` MUST guard `if (!this.contextualized) throw` before doing any work |
| SK1-R5 | Module MUST be registered in `src/modules/index.ts`: static property, static getter, and instantiation inside `initializeModulesEcoSystem()` |
| SK1-R6 | If module domain is needed in resolvers via `context`: add to `fastify.decorate('domains', {...})` AND extend the `FastifyInstance` interface in the same file |
| SK1-R7 | File naming: `{entity}.repository.ts` (interface, in `application/`), `{entity}.repository.mongo.ts` (impl, in `infrastructure/`) |

---

## Decision Gates

| IF | THEN |
|----|------|
| Creating a new feature from scratch | `modules/` + hexagonal structure (this skill) |
| Fixing a bug in existing `components/` | Skip this skill; apply `api-legacy-migration` |
| Module domain needed in resolvers via Fastify context | Add to `fastify.decorate` + extend `FastifyInstance` interface |
| Module has no cross-domain deps | `setDependencies({})` still MUST be called (even empty object) |

---

## Execution Steps

1. Create `apps/api/src/modules/{name}/` with `domain/`, `application/`, `infrastructure/` subdirs.
2. Write the Module class with the 3-method lifecycle (see skeleton below).
3. Declare a `private static {Name}Module` property in `ModulesEcoSystem` (`src/modules/index.ts`).
4. Add a `static get {name}Module()` getter that calls `getInstance()` then returns the static field.
5. Instantiate the module inside `initializeModulesEcoSystem()`, call `setDependencies(...)`, then `init()`.
6. If resolvers need context access: add to `fastify.decorate('domains', {...})` and extend `FastifyInstance`.

---

## Examples

### Module class skeleton (canonical: `apps/api/src/modules/stay/index.ts`)

```typescript
export class PaymentDomain {
  initialized = false;
  contextualized = false;

  // injected cross-domain deps (typed via domain/dependencies/)
  private authDomain: IAuthDomain;

  constructor() {}

  public setDependencies(domains: { authDomain: IAuthDomain }) {
    this.authDomain = domains.authDomain;
    this.contextualized = true;
  }

  public init() {
    if (!this.contextualized) throw new Error('PaymentDomain is not contextualized');
    // instantiate repos and services here
    this.initialized = true;
  }
}
```

### `initializeModulesEcoSystem` registration snippet (canonical: `apps/api/src/modules/index.ts:26–170`)

```typescript
class ModulesEcoSystem {
  private static PaymentModule: PaymentDomain; // 1. static property

  static get paymentModule(): PaymentDomain {  // 2. static getter
    ModulesEcoSystem.getInstance();
    return ModulesEcoSystem.PaymentModule;
  }

  private static initializeModulesEcoSystem(): void {
    // ... existing modules ...
    ModulesEcoSystem.PaymentModule = new PaymentDomain(); // 3. instantiate
    ModulesEcoSystem.PaymentModule.setDependencies({ authDomain: ModulesEcoSystem.AuthDomain });
    ModulesEcoSystem.PaymentModule.init();
  }
}

// 4. Fastify decorate (only if resolvers need context access)
fastify.decorate('domains', { paymentDomain: ModulesEcoSystem.paymentModule });
// + extend FastifyInstance interface above the fp() call
```

---

## Output Contract

Agent confirms ALL of:
- [ ] `domain/`, `application/`, `infrastructure/` subdirs created
- [ ] Module class has `constructor` / `setDependencies` / `init` in that order
- [ ] `init()` starts with `if (!this.contextualized) throw`
- [ ] Static property + getter + instantiation added in `src/modules/index.ts`
- [ ] `fastify.decorate` + `FastifyInstance` extended (if context access required)

---

## Anti-Patterns

- ❌ Adding new feature code to `components/` — that folder is maintenance-only
- ❌ Calling `init()` before `setDependencies()` — will throw at runtime
- ❌ Importing another module's `infrastructure/` layer directly — violates hexagonal boundaries
