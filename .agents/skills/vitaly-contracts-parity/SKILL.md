---
name: vitaly-contracts-parity
description: "Keep Vitaly's Pydantic schemas (backend) and the TypeScript interfaces in ../vitaly_frontend/vitaly-care-for-families/src/services in sync: type equivalence table, APIResponse.data unwrapping, OpenAPI diff check. Trigger: creating or modifying an endpoint's response_model or payload, a schema in app/schemas/, a frontend service DTO, or when the frontend and API disagree on a field, type or nullability."
---

# Vitaly contracts parity — Pydantic ↔ TypeScript

**Source of truth:** `.agents/rules/cross-repo-e2e.md` and `.agents/rules/standard-response.md`
(the law). The backend owns the contract; the frontend mirrors it. This skill is the procedure.

No compiler crosses the Python/TypeScript boundary. `tsc` checks one side, Pydantic the other,
and a drift fails silently until a user hits it.

## The rule in one line

**A contract change touches both repos in the same task, in separate commits.** Editing a schema
in `app/schemas/` or a handler's return shape means opening the matching service in
`../vitaly_frontend/vitaly-care-for-families/src/services/<feature>/<feature>Service.ts` before calling it done.
Resolve the frontend path relatively (`$(git rev-parse --show-toplevel)/../vitaly_frontend/vitaly-care-for-families`).

Fields travel in **snake_case** on both sides. No camelCase conversion at the boundary.

## How the frontend writes contracts today

- Plain TypeScript `interface`s in the service file (no Zod there), e.g. `StudentsResumeData`.
- Each endpoint declares its own envelope interface (`success`, `message`, `data`, `errors`,
  `meta`) and calls `apiClient.get<XResponse>("/api/v1/...")` (axios instance in
  `src/lib/api-client.ts`), then returns `response.data.data`. One partial generic exists:
  `CommonListResponse<T>` (`src/services/schoolAdmin/schoolAdminService.ts:90`, `data: { items: T[] }`).
- Legacy paginated endpoints nest `{data, total, page, size}` **inside** `data`, so the frontend
  unwraps three times (`response.data.data.data`, see `schoolAdminService.ts:413-415`). New
  paginated endpoints put the list in `data` and pagination in `meta` (`PaginationMeta`); moving
  an existing endpoint to `meta` is a coordinated backend + frontend change, never backend-only.
- Legacy `*Response` schema names are tolerated per `schema-naming-convention.md`; do not rename
  them without coordinating the frontend.
- Zod exists in the frontend only for **form validation** in pages (`RegisterDoctor.tsx`, etc.).
  Form schemas must produce the payload the `*Create`/`Register` Pydantic model expects.

## Equivalence table

| Pydantic                                | TypeScript                | Note                                           |
| --------------------------------------- | ------------------------- | ---------------------------------------------- |
| `str`                                   | `string`                  |                                                |
| `int`, `float`                          | `number`                  | Mirror `Field(ge=, le=)` in form validation    |
| `bool`                                  | `boolean`                 |                                                |
| `date`, `datetime`                      | `string`                  | ISO-8601 on the wire; parse explicitly         |
| `str` `Enum` / `Literal[...]`           | union of string literals  | Values must match exactly (`"OPTIMO" \| ...`)  |
| `list[X]`                               | `X[]`                     |                                                |
| `X \| None` (no default, required)      | `x: X \| null`            | Key always present, may be `null`              |
| `X \| None = None`                      | `x?: X \| null`           | Key may be omitted **or** `null`               |
| `dict[str, Any]`                        | `Record<string, unknown>` | Avoid in new contracts                         |

Optional (`?`) and nullable (`| null`) are not interchangeable, and the direction matters:

- **Request** (`*Create`/`*Update`): a field with a default (`X | None = None`) may be omitted by
  the client, so the TS payload type uses `x?: X | null`.
- **Response** (`*Read`): FastAPI serializes the whole `response_model` (no
  `response_model_exclude_none` in `app/`), so every declared key is present, `None` as `null`.
  Type it `x: X | null`, not `x?:`.

## APIResponse envelope

`app/schemas/responses.py`: `success: bool`, `message: str | None`, `data: T | None`,
`errors: list[ErrorDetail] | None`, `meta: PaginationMeta | None`. In TS:

- Prefer one generic `ApiResponse<T>` over per-endpoint copies when touching a service.
- `errors` is `{ loc?: (string|number)[] | null; msg: string; type: string }[] | null`, and `meta`
  is `{ page; size; total; total_pages } | null`. Existing frontend copies type them as
  `null | string[]` and `Record<string, unknown>` — that is drift, fix it when you touch the file.
- `meta` is the target only for **new** paginated endpoints; legacy ones still carry
  `total/page/size` inside `data` (see above).
- Components consume the unwrapped `data`; guard `null` before use.

## Typed contracts first

Many endpoints declare `response_model=APIResponse[dict]`. That makes OpenAPI useless for parity
and lets the service return anything. When adding or changing an endpoint, define a `*Read`
schema (with `Field(description=...)`) and use `APIResponse[XRead]`; then mirror it in TS.

## Verify against OpenAPI

FastAPI publishes the real schemas at `/openapi.json` (the app sets no custom `openapi_url`):

```bash
curl -s http://localhost:8000/openapi.json | jq '.components.schemas.SchoolRead'
```

Compare against the TS interface on four points: identical field names, equivalent types per the
table, same required set (and nullability), same enum values. These catch nearly all real drift.
This is also the natural base for a CI check (e.g. generate TS types from the OpenAPI spec and
diff them against the hand-written interfaces) without writing a third contract.

## Adding or changing an endpoint

1. Pydantic `*Create`/`*Update`/`*Read` in `app/schemas/`, `response_model=APIResponse[XRead]`.
2. Mirror the `*Read` (and request payload) as TS interfaces in the feature service.
3. Check both against the table and the OpenAPI output.
4. Fix asymmetry **from the lax side toward the strict side**: the API is the last line, the
   frontend is just one client. If TS allows only `"monthly" | "weekly"`, Pydantic must be a
   `Literal`, not `str`.
5. Commit backend and frontend separately.

## Red flags

- A Pydantic `str` whose TS counterpart is a literal union (or the reverse).
- `min`/`max` limits on one side only.
- A new endpoint returning `APIResponse[dict]`.
- `apiClient.get<any>(...)` (e.g. `schoolAdminService.ts:404`): the contract is untyped.
- A TS interface with camelCase fields or a field the backend never sends.
- A frontend form whose Zod field names do not match the backend payload model.
