---
name: audit-logging
description: Estandariza cuándo y cómo registrar audit logs para acciones críticas
  de la plataforma. Usar cuando una operación sensible requiera trazabilidad, especialmente
  en dominios financieros, usuarios, reservas, políticas, configuración o exportaciones.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Audit logging

## Cuándo usar este skill

- Acciones financieras
- Cambios de usuarios, roles o autenticación
- Cambios sobre reservas, aprobaciones o políticas
- Exportaciones, configuración sensible o acciones administrativas
- Cualquier operación crítica que deba quedar trazable

## No usar este skill para

- Logging técnico de depuración → usar `code-quality`
- Eventos informativos que no requieren auditoría formal
- Métricas de observabilidad no ligadas a una acción de negocio

## Reglas obligatorias

- Ante duda, preferir auditar una acción crítica antes que omitirla.
- Registrar éxito y, cuando aplique, también fallas relevantes.
- Mantener error isolation: el fallo del audit log no debe romper la operación principal salvo requisito explícito.
- Incluir contexto útil: actor, recurso, id del recurso y metadata relevante sin filtrar secretos.

## Patrón recomendado

1. Identificar la acción crítica.
2. Elegir el método de audit log más específico disponible.
3. Envolver el registro de auditoría con manejo de errores seguro.
4. Añadir metadata útil para investigación posterior.
5. Verificar que el flujo principal no dependa indebidamente del log.

## Casos donde suele ser obligatorio

- Facturas, pagos, conciliaciones, settlements
- Creación o suspensión de usuarios
- Aprobación o rechazo de reservas
- Cambios de políticas corporativas
- Exportaciones de datos
- Acciones de configuración sensible

## Checklist

- ¿La acción es materialmente sensible o regulatoria?
- ¿Se registró actor, recurso y resourceId?
- ¿La metadata ayuda a investigar el evento?
- ¿Se protegieron secretos o datos innecesarios?
- ¿El audit log no rompe el flujo principal si falla?

## Skills que suelen acompañar este

- `code-quality`
- `financial-architecture`
- `corporate-policies`
- `notification-system`

---

## Archivos clave

| Archivo                                                                                     | Rol                                                                                                                                                         |
| ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `server/src/infrastructure/logging/AuditLogService.ts`                                      | Implementación singleton. Expone `log`, `logFromRequest`, `logSuccess`, `logFailure` y helpers por dominio. También exporta el singleton `auditLogService`. |
| `server/src/application/contracts/IAuditLogService.ts`                                      | Contrato (interfaz) para inyección en capa de aplicación. Solo define `log(context, params)`.                                                               |
| `server/src/infrastructure/persistence/postgres/repositories/PostgresAuditLogRepository.ts` | Repositorio Postgres. Escribe en tabla `audit_logs`. No usar directamente; usar el servicio.                                                                |
| `shared/schema.ts`                                                                          | Define los enums `AuditAction`, `AuditResource`, `AuditResult` y el tipo `InsertAuditLog`. Siempre importar acciones/recursos desde aquí.                   |

---

## Patrón de importación

Hay dos formas según el contexto:

**En controllers e infrastructure** — usar el singleton exportado:

```ts
import { auditLogService } from '../../../logging/AuditLogService';
import { AuditAction, AuditResource } from '@shared/schema';
```

**En application layer** — inyectar la interfaz:

```ts
import type { IAuditLogService } from '../contracts/IAuditLogService';
// Se recibe en el constructor del command/service
```

> No instanciar `new AuditLogService()` manualmente. Usar el singleton o la inyección.

---

## Ejemplo de uso

### En un controller (con request disponible)

```ts
// Forma preferida en controllers: extrae userId, IP y userAgent automáticamente del request
auditLogService
  .logFromRequest(req, {
    action: AuditAction.BOOKING_APPROVED,
    resource: AuditResource.BOOKING,
    resourceId: bookingId,
    previousValue: { status: previousState.status },
    newValue: { status: 'APPROVED', approverComments: comments },
    metadata: {
      approvalId,
      approverRole: req.user?.role,
    },
  })
  .catch((err) => {
    loggingService.error('Failed to log booking approval audit', err as Error, {
      operation: 'audit_log_error',
      approvalId,
    });
  });
```

### En un command (sin request)

```ts
// Usar .log() con context manual cuando no hay req disponible
auditLogService
  .log(
    { userId: processedBy },
    {
      action: AuditAction.PAYMENT_PROCESSED,
      resource: AuditResource.PAYMENT,
      resourceId: payment.id,
      previousValue: { invoiceStatus: invoice.status },
      newValue: { invoiceStatus: 'PAID', paymentId: payment.id },
      metadata: {
        operation: 'bcv_settlement',
        invoiceId,
        bcvRate,
      },
    }
  )
  .catch((err) => {
    loggingService.error('Failed to log settlement audit', err as Error, {
      operation: 'audit_log_bcv_settlement',
    });
  });
```

**Importante:** siempre encadenar `.catch()` — el audit log nunca debe romper el flujo principal.

---

## Estructura de un audit entry

### Contexto (`AuditLogContext`)

| Campo       | Tipo      | Descripción                          |
| ----------- | --------- | ------------------------------------ |
| `userId`    | `string?` | ID del usuario que realiza la acción |
| `userEmail` | `string?` | Email del actor                      |
| `userRole`  | `string?` | Rol del actor                        |
| `clientId`  | `string?` | Organización del actor               |
| `companyId` | `string?` | Empresa del actor                    |
| `ipAddress` | `string?` | IP de origen                         |
| `userAgent` | `string?` | User-Agent del browser               |

> `logFromRequest(req, params)` extrae todo el contexto automáticamente desde el request. Preferir este método en controllers.

### Parámetros (`AuditLogParams`)

| Campo           | Tipo                   | Requerido      | Descripción                                                              |
| --------------- | ---------------------- | -------------- | ------------------------------------------------------------------------ |
| `action`        | `AuditActionType`      | ✅             | Acción realizada. Usar constantes de `AuditAction`.                      |
| `resource`      | `AuditResourceType`    | ✅             | Recurso afectado. Usar constantes de `AuditResource`.                    |
| `resourceId`    | `string?`              | Recomendado    | ID del recurso (ej: bookingId, invoiceId).                               |
| `previousValue` | `Record<string, any>?` | Opcional       | Estado anterior del recurso.                                             |
| `newValue`      | `Record<string, any>?` | Opcional       | Estado nuevo del recurso.                                                |
| `result`        | `AuditResultType`      | Opcional       | `SUCCESS` o `FAILURE`. Por defecto: `SUCCESS`.                           |
| `errorMessage`  | `string?`              | Solo en fallos | Mensaje de error si `result = FAILURE`.                                  |
| `metadata`      | `Record<string, any>?` | Opcional       | Contexto adicional para investigación (ej: operación, IDs relacionados). |

### Enums disponibles

```ts
// Acciones — importar desde '@shared/schema'
AuditAction.BOOKING_APPROVED | BOOKING_REJECTED | BOOKING_CANCELLED;
AuditAction.INVOICE_CREATED | INVOICE_CANCELLED | PAYMENT_PROCESSED | PAYMENT_RECONCILED;
AuditAction.USER_CREATED | USER_UPDATED | USER_ROLE_CHANGED | LOGIN_FAILED;
AuditAction.POLICY_CREATED | POLICY_UPDATED | POLICY_DELETED;
AuditAction.ORGANIZATION_APPROVED | ORGANIZATION_SUSPENDED;
AuditAction.DATA_EXPORTED | PLATFORM_SETTINGS_UPDATED;
// ... ver shared/schema.ts para lista completa

// Recursos
AuditResource.BOOKING | INVOICE | PAYMENT | USER | POLICY | ORGANIZATION | REPORT;
// ... ver shared/schema.ts para lista completa

// Resultados
AuditResult.SUCCESS | AuditResult.FAILURE;
```

---

## Helpers especializados

El servicio ofrece métodos de conveniencia para dominios específicos:

| Método                                             | Cuándo usar                                                     |
| -------------------------------------------------- | --------------------------------------------------------------- |
| `logFromRequest(req, params)`                      | Controllers — extrae contexto del request automáticamente       |
| `logSuccess(ctx, action, resource, ...)`           | Cuando solo importa registrar éxito                             |
| `logFailure(ctx, action, resource, errorMsg, ...)` | Para registrar errores de negocio                               |
| `logFinancialAction(ctx, action, resourceId, ...)` | Acciones financieras — agrega `category: FINANCIAL` en metadata |
| `logUserAction(ctx, action, targetUserId, ...)`    | Gestión de usuarios                                             |
| `logBookingAction(ctx, action, bookingId, ...)`    | Acciones sobre reservas                                         |
| `logLoginAttempt(ip, ua, email, success, ...)`     | Intentos de login                                               |
| `logDataExport(ctx, exportType, recordCount, ...)` | Exportaciones de datos                                          |

---

## Cómo mockear en tests

```ts
vi.mock('../../infrastructure/logging/AuditLogService', () => ({
  auditLogService: {
    logFromRequest: vi.fn().mockResolvedValue(undefined),
    log: vi.fn().mockResolvedValue(null),
  },
  AuditLogService: {
    getInstance: vi.fn().mockReturnValue({ logAction: vi.fn() }),
  },
}));
```
