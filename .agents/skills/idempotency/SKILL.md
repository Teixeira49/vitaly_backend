---
name: idempotency
description: >
  Garantiza idempotencia y deduplicación en webhooks, operaciones financieras
  y endpoints sensibles a reintentos. Usar cuando se reciban webhooks externos,
  se creen recursos financieros o se exponga un POST/PATCH donde un doble
  submit cause daño.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Idempotency — Operaciones Idempotentes

## Cuándo es obligatorio

Agregar idempotencia en **toda operación que**:

- Recibe webhooks externos (Estei Web, Zoho Desk, pasarelas de pago)
- Crea o modifica recursos financieros: facturas, pagos, liquidaciones
- Crea usuarios, roles o políticas (riesgo de duplicados por retry de red)
- Procesa callbacks de APIs externas susceptibles a reintentos
- Expone endpoints `POST`/`PATCH` donde un doble submit del cliente causa daño real

## Cuándo NO es necesario

- Operaciones de lectura (`GET`)
- Operaciones ya intrínsecamente idempotentes (upserts con `ON CONFLICT DO UPDATE`)
- Actualizaciones de estado simples donde el estado final es el mismo (ej. marcar como leído)
- Operaciones internas de background jobs donde el sistema controla los reintentos

## Servicio principal

```ts
import { IdempotencyService } from '@/infrastructure/security/IdempotencyService';
```

- Ubicación: `server/src/infrastructure/security/IdempotencyService.ts`
- Singleton: usar `IdempotencyService.getInstance()`
- Storage: PostgreSQL, tabla `idempotency_records`
- TTL: **24 horas** desde la primera ejecución
- Limpieza: job interno cada 10 minutos elimina registros expirados

## Cómo usar

### Patrón con middleware (recomendado para endpoints HTTP)

```ts
// En el router, DESPUÉS de permisos y ANTES del controller
router.post(
  '/recurso',
  PermissionMiddleware.requireAnyPermission([Permission.X]),
  idempotencyService.createMiddleware('nombre-operacion'),
  (req, res) => controller.crearRecurso(req, res)
);
```

El middleware:

1. Genera la key: `SHA256(userId + operation + body)`
2. Si existe en DB → devuelve `res.json(existing.response)` sin ejecutar el controller
3. Si no existe → adjunta `req.idempotencyKey` y llama `next()`

El controller **debe** persistir la respuesta al finalizar:

```ts
const result = await this.command.execute(input);
const response = { success: true, data: result };

if (req.idempotencyKey) {
  await idempotencyService.storeResult(req.idempotencyKey, req.user.id, req.body, response);
}

return res.json(response);
```

### Patrón para webhooks (middleware WebhookHmacMiddleware)

Para webhooks, usar `WebhookHmacMiddleware.checkIdempotency()`:

```ts
router.post(
  '/webhook',
  WebhookHmacMiddleware.validateSignature(),
  WebhookHmacMiddleware.checkIdempotency({ source: 'estei-web' }),
  (req, res) => controller.handleWebhook(req, res)
);
```

El middleware de webhook usa `integration_events` (no `idempotency_records`) para deduplicar por `externalEventId` + `eventType` + `source`.

## Generación de keys

El `IdempotencyService` genera la key automáticamente vía el middleware:

```
key = "{operation}_{userId}_{SHA256(body)[0:16]}"
```

No generar keys manualmente salvo en casos de integración directa (llamar `generateKey(userId, operation, data)`).

## TTL y expiración

- Keys estándar: **24 horas** (hardcoded en `storeResult`)
- Eventos de webhook: según esquema de `integration_events` (sin expiración automática)
- Los registros expirados se limpian cada 10 minutos por el job interno

## Anti-patrones

| Anti-patrón                                                      | Por qué es un problema                             |
| ---------------------------------------------------------------- | -------------------------------------------------- |
| Procesar antes de verificar la key                               | La operación ya ocurrió, el check llega tarde      |
| No llamar `storeResult` tras procesar                            | El segundo request ejecuta la operación de nuevo   |
| Usar el mismo `operation` para endpoints distintos               | Colisión de keys entre operaciones no relacionadas |
| Generar keys con datos variables (timestamps, UUIDs del cliente) | La key nunca matchea en reintentos                 |
| No aplicar idempotencia a webhooks con retry automático          | Procesamiento duplicado de facturas o pagos        |

## Referencia canónica

Endpoint con middleware en producción:

```ts
// adminRoutes.ts
router.post(
  '/payment-methods',
  GranularPermissionMiddleware.requireAnyPermission([Permission.MANAGE_PLATFORM_SETTINGS]),
  idempotencyService.createMiddleware('create-payment-method'),
  (req, res) => paymentMethodsController.createPaymentMethod(req, res)
);
```

Webhook con idempotencia:

```
WebhookHmacMiddleware.checkIdempotency() en EsteiWebWebhookController / ZohoDeskWebhookController
```

## Checklist antes de deployar un webhook o endpoint de mutación crítica

- [ ] ¿El endpoint tiene `idempotencyService.createMiddleware('nombre-único')` en la cadena?
- [ ] ¿El controller llama `storeResult` con la respuesta exitosa?
- [ ] ¿El nombre de operación es único para este endpoint (no reutilizado)?
- [ ] Para webhooks: ¿usa `WebhookHmacMiddleware.checkIdempotency()`?
- [ ] ¿Se probó qué pasa al enviar el mismo request dos veces?
