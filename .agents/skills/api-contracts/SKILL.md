---
name: api-contracts
description: >
  Asegura contratos tipados end-to-end entre server y client via shared/.
  Usar cuando se cree o modifique un endpoint, su response type, o un hook
  useQuery/useMutation en el frontend.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# API contracts

## Cuando usar este skill

- Endpoint nuevo o modificado en `server/src/infrastructure/web/express/`
- Hook `useQuery` o `useMutation` nuevo o modificado en `client/src/`
- Cambio en tipos de respuesta o request de un endpoint existente
- Refactor de `shared/api-types.ts` o archivos de tipos compartidos

## No usar este skill para

- Lógica de dominio sin impacto HTTP
- Cambios de schema de base de datos sin cambio de API → usar `database-schema`
- Errores HTTP y formato de error → usar `error-handling-patterns`

## Fuente de verdad

`shared/api-types.ts` y archivos de tipos en `shared/` son el contrato entre server y client.

## Reglas obligatorias

### 1. Todo endpoint DEBE tener su response type en shared

Cada endpoint que retorne datos debe tener un tipo explícito en `shared/api-types.ts`
(o en un archivo `shared/api-types/*.ts` si se migra a estructura por dominio).

```ts
// shared/api-types.ts
export type UserListItem = {
  id: string;
  name: string;
  email: string;
  status: AccountStatus;
};
```

**No definir tipos de respuesta ad-hoc** en el frontend ni en el backend.
Si el tipo solo existe en uno de los dos lados, falta el contrato.

### 2. El frontend DEBE tipar sus queries con el tipo de shared

```ts
// client/src/pages/app/users/UserList.tsx
import type { UserListItem } from '@shared/api-types';

const { data } = useQuery<ApiSuccessResponse<PaginatedResponse<UserListItem>>>({
  queryKey: ['users', page],
  queryFn: () => fetchApi('/api/app/users', { params: { page } }),
});
```

Si un `useQuery` usa `any`, `unknown`, o un tipo local que duplica lo de shared,
es una violación del contrato.

### 3. El backend DEBE retornar datos que cumplan el contrato

El controller debe usar `createSuccessResponse` con datos que matcheen el tipo shared.
No retornar campos extra no documentados ni omitir campos esperados.

```ts
// server controller
import { createSuccessResponse } from '@shared/api-types';

res.json(createSuccessResponse({ items: mappedUsers, total }));
```

### 4. Response validation en el frontend (recomendado)

Cuando sea práctico, validar la respuesta en runtime con el schema Zod de shared:

```ts
import { paginatedResponseSchema, userListItemSchema } from '@shared/api-types';

const schema = apiResponseSchema(paginatedResponseSchema(userListItemSchema));
// Usar en el queryFn o como validación post-fetch
```

Esto protege contra cambios breaking del backend que TypeScript solo no detecta.
Priorizar en: endpoints financieros, booking y políticas (datos críticos).

### 5. Organización de tipos

Mientras `shared/api-types.ts` sea manejable (<1000 líneas), mantenerlo unificado.
Cuando supere ese límite, migrar a estructura por dominio:

```
shared/
  api-types/
    index.ts          # re-exports + tipos base (ApiResponse, PaginatedResponse)
    financial.ts      # InvoiceDetail, PaymentHistoryItem, etc.
    bookings.ts       # BookingListItem, BookingDetail, etc.
    users.ts          # UserListItem, UserDetail, etc.
    policies.ts       # PolicyListItem, PolicyEvaluation, etc.
```

Mantener el re-export desde `index.ts` para no romper imports existentes.

## Deteccion de violaciones

Al tocar un endpoint o hook, verificar estas condiciones:

| Condicion                                               | Accion                                        |
| ------------------------------------------------------- | --------------------------------------------- |
| El endpoint no tiene response type en shared            | Crear el tipo antes de continuar              |
| El `useQuery` usa `any` o tipo local duplicado          | Migrar a tipo de shared                       |
| El controller retorna un objeto literal sin tipo        | Tipar con el contrato de shared               |
| El frontend no valida response y es un endpoint critico | Sugerir agregar schema validation             |
| `shared/api-types.ts` supera ~1000 lineas               | Sugerir la migracion a estructura por dominio |

Estas verificaciones son **sugerencias activas**: cuando se detecten, informar al
desarrollador y proponer el fix. No bloquear la tarea, pero siempre documentar
la deuda si se decide posponer.

## Checklist

- [ ] El endpoint tiene su response type en `shared/api-types.ts`
- [ ] El frontend usa ese tipo en su `useQuery`/`useMutation` (no `any` ni tipo local)
- [ ] El backend retorna datos que cumplen el contrato via `createSuccessResponse`
- [ ] Si es un endpoint critico (financiero, booking, politicas): hay Zod schema validation en el frontend
- [ ] `shared/api-types.ts` esta dentro de limites razonables de tamano

## Referencia

- `shared/api-types.ts` — tipos base y schemas Zod compartidos
- `shared/schema.ts` — entidades de base de datos y enums
- `.cursor/rules/api-spec.yml` — documentacion parcial de endpoints (contexto AI)

## Skills que suelen acompanar este

- `api-routes` — para el patron de creacion de endpoints
- `error-handling-patterns` — para el formato de errores
- `code-quality` — reglas transversales
- `testing-convention` — tests del controller/hook
