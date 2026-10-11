---
name: api-hexagonal-layers
description: "Trigger: adding code to apps/api/src/modules/ that crosses domain, application, or infrastructure layers. New code only — not for components/."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activates on: "writing code in apps/api/src/modules/", "extending a module",
"adding service to modules/", "adding to application layer".

**Scope: NEW code in `modules/` ONLY. Does NOT mandate migration of `components/`.
Does NOT block the existing hybrid architecture reality.** When touching existing
`components/` code, use `api-legacy-migration` instead.

Co-inject with `api-module-pattern` when scaffolding a new module from scratch.

---

## Hard Rules

| Rule ID | Rule |
|---------|------|
| SK4-R1 | `domain/` MUST contain ONLY pure TypeScript types, interfaces, and repository contracts — zero Mongoose/GraphQL/external imports |
| SK4-R2 | `application/` MUST NOT import Mongoose models — only repository interfaces and domain types |
| SK4-R3 | Cross-module dependencies MUST flow through `domain/dependencies/{module}.domain.ts` interface files — never direct imports from another module's `application/` or `infrastructure/` |
| SK4-R4 | Repository interface MUST live in `application/{entity}/{entity}.repository.ts`; Mongo implementation MUST live in `infrastructure/{entity}/{entity}.repository.mongo.ts` and implement the interface |
| SK4-R5 | `infrastructure/` is the ONLY layer permitted to import Mongoose models, GraphQL TypeComposers, and controller utilities |

---

## Decision Gates

| IF | THEN |
|----|------|
| Need another module inside application-layer service | Create/extend `domain/dependencies/{module}.domain.ts` interface |
| New repository needed | Interface in `application/`, Mongo impl in `infrastructure/` |
| Pure business logic, no DB/GQL | `domain/` or `application/` layer |
| Data access, GQL type mapping, HTTP routes | `infrastructure/` only |

---

## Execution Steps

1. Before adding any import, ask: which layer does this file live in?
2. `domain/` file? → only TS primitives and `@estei/models` interfaces allowed. Stop if you see a Mongoose/GQL import.
3. `application/` file? → inject repos and cross-domain deps via constructor; never import a Mongoose Model.
4. Cross-module dep needed? → create `domain/dependencies/{other-module}.domain.ts` interface; wire in `setDependencies`.
5. New repository? → write interface in `application/`; write `{Entity}MongoRepository implements {Entity}Repository` in `infrastructure/`.
6. `infrastructure/` file? → freely import Mongoose models, TypeComposers, and request/response utilities.

---

## Examples

### Domain dependency interface (canonical: `apps/api/src/modules/stay/domain/dependencies/calendar.domain.ts`)

```typescript
// domain/dependencies/calendar.domain.ts
import { IStay, IStaySpace } from '@estei/models';

export interface ICalendarDomain {
  url: {
    assignCalendarUrl: (stay: IStay, space: IStaySpace) => Promise<any>;
  };
}
```

The consuming module declares `private calendarDomain: ICalendarDomain` and receives it
through `setDependencies` — never by importing `CalendarDomain` from `modules/calendar/`.

### Repository interface vs Mongo implementation (canonical: `apps/api/src/modules/stay/`)

```typescript
// application/stay/stay.repository.ts  ← interface (no Mongoose)
export interface StayRepository {
  findOne(query: StayQueryFilter, projection?: string): Promise<IStay | null>;
  save(stay: IStay): Promise<IStay | null>;
  // ... other methods
}

// infrastructure/stay/stay.repository.mongo.ts  ← Mongo impl
import { Stay } from '@/modules/core/stay/stay.model'; // ✅ Mongoose import OK here

export class StayMongoRepository implements StayRepository {
  async findOne(query: Record<string, any>, projection?: string) {
    return Stay.findOne(query, projection);
  }
  async save(stay: IStay) {
    return (stay as StayDocument).save();
  }
}
```

---

## Output Contract

Agent confirms ALL of:
- [ ] No Mongoose model imports in `domain/` or `application/` layer files
- [ ] Cross-module deps declared via `domain/dependencies/{module}.domain.ts` interface
- [ ] Repository interface lives in `application/`; Mongo impl in `infrastructure/`
- [ ] `infrastructure/` is the only layer with Mongoose/GQL/controller imports

---

## Anti-Patterns

- ❌ Mongoose model import in `domain/` or `application/` — breaks hexagonal isolation and forces DB in every test
- ❌ Direct import from another module's `application/` or `infrastructure/` — creates hidden coupling; use domain interfaces
- ❌ DB query logic in `domain/` files — domain is pure logic only
