---
name: api-search-builders
description: "Trigger: adding or modifying a MongoDB search/aggregation pipeline, filter, sort, or search model in apps/api/src/modules/search. Use the SearchPipeline builder and its typed stages."
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## Activation Contract

Activates on: "add search filter", "new search model", "modify search pipeline",
"add sort to search", "aggregation pipeline in apps/api", "geo search", "search builder".

**Scope: `apps/api/src/modules/search/application/algorithm/` ONLY** — the `SearchPipeline`
class, its `stages/` factories, and the entity cores. The denormalized search collections
(`searchcompletestays`, `searchrooms`, `searchsortedstays`) are WRITTEN by the legacy queue
sync at `components/queue/utils/search.ts`; that write path is out of scope (use
`api-legacy-migration` there). This skill is the READ/query builder side only.

Co-inject with `api-hexagonal-layers` when adding a new search model (crosses layers) and
with `api-graphql-registration` when exposing a new search query.

---

## Hard Rules

| Rule ID | Rule |
|---------|------|
| SK7-R1 | `$geoNear` MUST be the first stage. `addLocationFilter` emits `$geoNear` for web; call it FIRST in every location-aware pipeline. A `$match`/`$addFields` before it throws at runtime. |
| SK7-R2 | `SearchPipeline` MUST be constructed with an explicit `type: 'room' \| 'complete' \| 'sort' \| 'general'`. `addPriceFilter`, `addGrouping`, `addProjection` are type-dispatched and THROW on wrong/undefined type (runtime, not compile-time). |
| SK7-R3 | Every new stage factory MUST return `[]` when its input is falsy/empty (empty-safe convention). Otherwise it injects an empty/invalid `$match`. |
| SK7-R4 | Slug-based filters MUST resolve slug→ObjectId in the Core BEFORE the pipeline runs (see attribute resolution in `search-general.core.ts`), because `$match` compares ObjectId fields. |
| SK7-R5 | Pagination MUST flow through `MongoRepository.aggregate(pipeline, { pagination: { page, perPage } })` → `paginatePipeline` (`$facet`). NEVER add your own `$skip`/`$limit`/`$count`. |
| SK7-R6 | New sort fields MUST be constrained at the DTO (`TSortInput`) level. `addFieldSorting` interpolates `input.field` into `$sort` with NO whitelist — it will sort on any field given. |
| SK7-R7 | Room searches MUST `$group` back to `staySlug` (`addGrouping`/`addRoomGrouping`). Skipping grouping yields duplicate stays. |

---

## Decision Gates

| IF | THEN |
|----|------|
| Adding a filter to an existing search | Add an empty-safe `add*Filter` method on `SearchPipeline` + a stage factory in `pipeline/stages/`; call it in the relevant Core |
| Filter value is a slug | Resolve slug→ObjectId in the Core first (SK7-R4); the stage matches ObjectId |
| Adding a new sortable field | Extend `TSortInput` DTO (SK7-R6); reuse `addFieldSorting` |
| Stage applies only to one type (price, grouping, projection) | Branch on `this.type` inside the method; `throw` for unsupported types (SK7-R2) |
| Adding a whole new search entity/model | New schema+model + `MongoRepository` subclass (`infrastructure/`), Core (`application/algorithm/core/`), DI wiring in `modules/search/index.ts`; co-load `api-hexagonal-layers` |
| Exposing search via GraphQL | Resolver in `infrastructure/algorithm/controllers/`; co-load `api-graphql-registration` |

---

## Execution Steps

1. Identify the pipeline `type` you target (`complete`, `room`, `sort`, `general`) and the
   Core that builds it (`application/algorithm/core/{complete,room,sort}/index.ts`).
2. New filter? Add an empty-safe stage factory in `pipeline/stages/{general,location,...}.ts`
   (return `[]` when arg is empty), then an `add*Filter` method on `SearchPipeline`
   (`pipeline/model.ts`) that calls `addNewState(() => factory(...))`.
3. If the filter input is a slug, resolve it to an ObjectId in the Core before building.
4. Wire the new `add*Filter` call into the Core's pipeline build, respecting stage order
   (location/`$geoNear` first, then `$match` filters, then `$addFields`/`$sort`/`$group`,
   then `addProjection` last).
5. Do NOT touch pagination — leave execution to `repo.aggregate(pipeline, { pagination })`.
6. New model? Add schema+model, a `MongoRepository<Model, Interface>` subclass, a Core, and
   DI wiring in `modules/search/index.ts` `init()`.

---

## Examples

### Builder usage (canonical: `application/algorithm/core/complete/index.ts:31–57`)

```typescript
const searchPipeline = new SearchPipeline({ type: 'complete' }); // explicit type (SK7-R2)
searchPipeline.addLocationFilter(filter.location);               // $geoNear FIRST (SK7-R1)
searchPipeline.addSpacesFilter(filter?.spaces);                  // empty-safe (SK7-R3)
searchPipeline.addGeneralFilter();
searchPipeline.addPriceFilter({ minPrice, maxPrice, checkIn, checkOut }); // type-dispatched
searchPipeline.addAttributesFilter(filter.attributes);           // attributes already slug→ObjectId
searchPipeline.addRandomSeed(record.seed);
searchPipeline.addSeedSorting();
searchPipeline.addProjection();                                  // type-dispatched, last
return searchPipeline.compile();                                 // returns PipelineStage[]
```

Execution (canonical: `complete/index.ts:67`):

```typescript
const res = await this.repo.aggregate<CompleteStayReturn>(pipeline, {
  pagination: { page: record.pagination.page, perPage },        // SK7-R5 — never hand-roll $skip/$limit
});
```

### Empty-safe stage factory (canonical: `pipeline/stages/general.ts`)

```typescript
// returns [] when the arg is empty → no $match injected (SK7-R3)
export const spaceFilter = (spaces?: string[]): PipelineStage[] =>
  spaces?.length ? [{ $match: { spaceSlug: { $in: spaces } } }] : [];
```

---

## Output Contract

Agent confirms ALL of:
- [ ] `SearchPipeline` constructed with explicit `type`
- [ ] Location/`$geoNear` filter added first when used
- [ ] New stage factory returns `[]` on empty input
- [ ] Slug inputs resolved to ObjectId in the Core, not the stage
- [ ] Pagination left to `repo.aggregate(..., { pagination })` — no manual `$skip`/`$limit`/`$count`
- [ ] New sort fields constrained in `TSortInput`
- [ ] New model wired in `modules/search/index.ts`

---

## Anti-Patterns

- ❌ `$match`/`$addFields` before `addLocationFilter` — breaks the `$geoNear`-must-be-first rule
- ❌ Constructing `SearchPipeline` without a `type` — type-dispatched methods throw at runtime
- ❌ Hand-rolling `$skip`/`$limit`/`$count` — bypasses `paginatePipeline`'s `$facet` and double-paginates
- ❌ Matching a raw slug against an ObjectId field — silent empty results; resolve in the Core
- ❌ Exposing a new sort field without a DTO guard — lets callers sort on arbitrary fields
- ❌ Returning room results without `$group` to `staySlug` — duplicate stays in the response
