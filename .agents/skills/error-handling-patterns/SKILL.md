---
name: error-handling-patterns
description: >
  Estandariza el manejo de errores HTTP, formato de respuestas de error y
  mapeo de errores de dominio a status codes. Usar cuando se cree o modifique
  un controller, se manejen errores en handlers Express, o se devuelvan
  respuestas de error desde el servidor.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Error Handling — Manejo de Errores y Respuestas HTTP

## Formato canónico de respuesta

**Siempre** usar `createErrorResponse` de `@shared/api-types`. Nunca inventar formatos.

```ts
import { createErrorResponse } from '@shared/api-types';

res.status(404).json(createErrorResponse('User not found', 'USER_NOT_FOUND'));
res.status(400).json(createErrorResponse('Validation failed', 'VALIDATION_ERROR', zodIssues));
res.status(500).json(createErrorResponse('Internal server error', 'INTERNAL_ERROR'));
```

Retorna `{ success: false, error: string, code?: string, details?: any }`.

---

## Mapa de errores → HTTP status

| Tipo de error de dominio                     | HTTP | Cuándo usarlo                         |
| -------------------------------------------- | ---- | ------------------------------------- |
| `*NotFoundError`                             | 404  | Recurso no existe                     |
| `*AlreadyExistsError` / `DUPLICATE_*`        | 409  | Conflicto de unicidad                 |
| `*HasDependenciesError` / `*HasCriticalData` | 409  | No se puede eliminar por dependencias |
| Validación Zod fallida                       | 400  | Body o params inválidos               |
| `FORBIDDEN` / sin permisos                   | 403  | Acceso denegado por regla de negocio  |
| `UNAUTHORIZED` / sin sesión                  | 401  | Sin autenticación                     |
| Error genérico `instanceof Error`            | 400  | Error de negocio no tipado (no 500)   |
| Error desconocido (`else`)                   | 500  | Falla inesperada del sistema          |

**Regla**: 422 no se usa en este proyecto. Validación de input → 400. Conflicto de estado → 409.

---

## Dónde manejar errores

- Los **controllers** atrapan errores de dominio y los mapean a HTTP. Son los únicos que conocen `Request/Response`.
- El **dominio y application layer** lanzan errores tipados (`extends Error`) sin saber nada de HTTP.
- **Nunca** retornar códigos HTTP desde domain o application layer.
- **Nunca** relanzar errores desde el controller — atrapar, mapear y responder.

---

## Patrón en controllers

```ts
async deleteUser(req: Request, res: Response): Promise<void> {
  try {
    // 1. Validación de entrada (Zod o manual)
    if (!req.user?.clientId) {
      res.status(403).json(createErrorResponse('Forbidden', 'FORBIDDEN'));
      return;
    }

    // 2. Ejecutar caso de uso
    const result = await this.deleteUserCommand.execute(req.params.id);

    // 3. Respuesta exitosa
    res.status(200).json(createSuccessResponse(result));
  } catch (error) {
    // 4. Mapear errores de dominio → HTTP
    if (error instanceof UserNotFoundError) {
      res.status(404).json(createErrorResponse(error.message, 'USER_NOT_FOUND'));
    } else if (error instanceof UserHasCriticalDataError) {
      res.status(409).json(createErrorResponse(error.message, 'USER_HAS_CRITICAL_DATA'));
    } else {
      res.status(500).json(createErrorResponse('Internal server error', 'INTERNAL_ERROR'));
    }
  }
}
```

---

## Errores de validación (Zod)

```ts
const validation = schema.safeParse(req.body);
if (!validation.success) {
  res
    .status(400)
    .json(createErrorResponse('Validation failed', 'VALIDATION_ERROR', validation.error.issues));
  return;
}
```

Pasar `validation.error.issues` en `details` para que el cliente sepa qué campo falló.

---

## Anti-patrones

```ts
// ❌ Objeto literal — rompe el contrato ApiErrorResponse
res.status(403).json({ success: false, error: 'FORBIDDEN', message: 'algo' });

// ❌ Usar 422 — no se usa en este proyecto, usar 400
res.status(422).json(createErrorResponse('Validation failed', 'VALIDATION_ERROR'));

// ❌ Catch genérico sin mapeo de errores tipados
catch (error) { res.status(500).json(createErrorResponse('...', 'INTERNAL_ERROR')); }
// Primero chequeá instanceof para los errores esperados, el 500 es el fallback.

// ❌ Errores de negocio como 500
catch (error) {
  if (error instanceof SomeBusinessError) {
    res.status(500).json(...); // 500 es solo para errores inesperados del sistema
  }
}

// ❌ createErrorResponse en el application/domain layer
// Solo los controllers conocen HttpResponse. Domain lanza errores, no los formatea.
```

---

## Referencia canónica

`server/src/infrastructure/web/express/controllers/CompanyController.ts` — usa `createErrorResponse`, mapea errores tipados del application layer, 409 para duplicados, 404 para not found, 400 para validación Zod, 500 solo como fallback.

---

## Checklist

Antes de agregar manejo de errores a un endpoint nuevo:

- [ ] Importar `createErrorResponse` de `@shared/api-types`
- [ ] Errores tipados del dominio se mapean con `instanceof` a sus HTTP correspondientes
- [ ] Validación Zod → 400 con `details: validation.error.issues`
- [ ] Último `catch` es fallback 500, no el primero
- [ ] No hay objetos literales de error — todo pasa por `createErrorResponse`
- [ ] El domain/application layer NO importa `createErrorResponse`
