---
name: notification-system
description: Estandariza la creación de eventos de notificación por email, in-app
  y SMS, incluyendo templates y retries. Usar cuando se agreguen o modifiquen notificaciones,
  mensajes a usuario o flujos de reintento.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Notification system

## Cuándo usar este skill

- Nuevo evento de notificación
- Cambios en emails transaccionales
- Notificaciones in-app
- SMS o flujos multicanal
- Reintentos o error isolation de notificaciones

## No usar este skill para

- Audit logs → `audit-logging`
- Logging técnico
- Mensajes puramente locales de UI que no pasan por el sistema de notificaciones

## Reglas obligatorias

- Mantener error isolation: un fallo de notificación no debe romper la operación principal salvo requisito explícito.
- Reutilizar singletons y helpers de templates existentes.
- Mantener consistencia de copy y tono.
- Si un evento requiere más de un canal, coordinarlo en la capa de aplicación, no con duplicación desordenada.

## Flujo recomendado

1. Definir o extender el tipo de notificación.
2. Crear o ajustar la interfaz de datos necesaria.
3. Implementar el método del canal correspondiente.
4. Reutilizar helpers de template.
5. Disparar la notificación desde el punto de aplicación correcto.
6. Cubrir éxito, fallo y reintentos si aplican.

## Checklist

- ¿Se eligió el canal correcto?
- ¿Se mantuvo error isolation?
- ¿Se reutilizaron helpers y servicios existentes?
- ¿El copy es consistente y claro?
- ¿Hay tests o validaciones del flujo?

## Skills que suelen acompañar este

- `audit-logging`
- `testing-convention`
- skill del dominio afectado

---

## Archivos clave

| Archivo                                                          | Rol                                                                                                                                                                                                                                              |
| ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `server/src/infrastructure/notifications/NotificationService.ts` | Singleton central. Maneja email (Postmark) y SMS (Twilio/Roraima) directamente, sin cola. Métodos: `sendEmailOTP`, `sendSMSOTP`, `sendDualOTP`, `sendInvitationEmail`, `sendApprovalRequiredNotification`, `sendPolicyCreatedNotification`, etc. |
| `server/src/application/services/InAppNotificationService.ts`    | Servicio de aplicación para notificaciones in-app. Escribe en `user_notifications` vía `storage`, encola reintentos automáticamente, y dispara email/SMS externos según preferencias del usuario.                                                |
| `server/src/application/services/NotificationRetryService.ts`    | Cola de reintentos con backoff exponencial. Delays: 1 min → 5 min → 30 min. Máx 3 intentos. Persiste jobs en `queue_jobs` (`QUEUE_NAME = 'notifications'`).                                                                                      |
| `server/src/application/services/NotificationTypes.ts`           | Enum `NotificationType` con todos los tipos válidos: `BOOKING_*`, `INVOICE_CREATED`, `PAYMENT_RECEIVED`, `CREDIT_ALERT`, `POLICY_CHANGE`, `SYSTEM`.                                                                                              |
| `server/src/application/services/ApprovalNotificationService.ts` | Orquesta notificaciones de aprobación: busca aprobadores por rol, crea in-app y llama a `NotificationService` para email/SMS. Respeta preferencias del usuario.                                                                                  |
| `server/src/services/AdminNotificationService.ts`                | Crea notificaciones para admins de plataforma en `platform_admin_notifications`. Singleton exportado como `adminNotificationService`.                                                                                                            |
| `server/src/services/UserNotificationPreferencesService.ts`      | Singleton. Consulta preferencias de canal por usuario y tipo. Default: email=true, sms=false. Métodos: `shouldNotifyByEmail(userId, type)`, `shouldNotifyBySms(userId, type)`.                                                                   |
| `server/src/infrastructure/email/PostmarkEmailService.ts`        | Implementación concreta de envío de email vía Postmark. Usada por `NotificationService` e `InAppNotificationService`.                                                                                                                            |
| `server/src/infrastructure/email/emailTemplateBuilder.ts`        | Helpers de HTML para emails: `buildEmailHtml`, `buildEmailButton`, `buildHighlightBox`, `buildDetailRow`, `buildMonoDisplay`, `buildMutedText`, `buildContactSection`.                                                                           |
| `server/src/infrastructure/sms/SmsProviderFactory.ts`            | Singleton. Selecciona automáticamente proveedor SMS: Roraima para números venezolanos (`584XXXXXXXX`), Twilio para internacionales.                                                                                                              |
| `server/src/infrastructure/sms/RoraimaSmsService.ts`             | Integración con API Roraima para SMS en Venezuela.                                                                                                                                                                                               |
| `server/src/composition-root.ts`                                 | Donde se instancian y cablean todos los servicios. Aquí se registra `inAppNotificationService` y se importa `notificationService` (singleton).                                                                                                   |

---

## Canales disponibles

| Canal                      | Cómo se usa                                                                                                                             | Proveedor                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| **Email**                  | `NotificationService.getInstance()` → métodos `send*` o `PostmarkEmailService` directamente                                             | Postmark (`POSTMARK_API_KEY`) |
| **SMS**                    | `NotificationService.getInstance().sendSMSOTP(...)` con `message` custom                                                                | Roraima (VE) / Twilio (intl)  |
| **In-app**                 | `inAppNotificationService.notify*(data)` → persiste en `user_notifications`                                                             | PostgreSQL + retry queue      |
| **Admin in-app**           | `adminNotificationService.notifyAdmins(...)` → persiste en `platform_admin_notifications`                                               | PostgreSQL                    |
| **Email + SMS coordinado** | `NotificationService.sendApprovalRequiredNotification(...)` — respeta preferencias del usuario vía `UserNotificationPreferencesService` | Postmark + Roraima/Twilio     |

### Agregar un nuevo canal

1. Crear la implementación en `server/src/infrastructure/<canal>/`.
2. Agregar la interfaz mínima (ej. `InAppXxxService`) en el servicio de aplicación que lo consume.
3. Inyectar en `composition-root.ts` al instanciar `InAppNotificationServiceImpl`.
4. Respetar `UserNotificationPreferencesService.shouldNotifyBy*()` antes de disparar.

---

## Ejemplo de uso

### 1. In-app desde un command (patrón estándar)

```ts
// server/src/application/commands/RejectBookingCommand.ts
const notificationResult = await this.deps.inAppNotificationService.notifyBookingRejected({
  userId: booking.userId,
  bookingId: booking.id,
  listingTitle: booking.listingTitle,
  reason: params.comments,
  userEmail: bookingUser?.email?.getValue(),   // dispara email si el usuario lo tiene habilitado
  userPhone: bookingUser?.toPrimitives().phoneNumber, // dispara SMS si está habilitado
});

if (!notificationResult.success) {
  // error isolation: loguear, no lanzar
  loggingService.warn('Failed to send rejection notification', { ... });
}
```

> El servicio encola el reintento automáticamente si falla. No hay que gestionar la cola manualmente.

### 2. Email directo desde un controller/service

```ts
// Importar el singleton (no instanciar)
import { notificationService } from '../../infrastructure/notifications/NotificationService';

const result = await notificationService.sendInvitationEmail({
  recipientEmail: user.email,
  recipientName: user.name,
  companyName: company.name,
  inviterName: inviter.name,
  activationLink: `${baseUrl}/activate?token=${token}`,
  expiryDays: 7,
});

if (!result.success) {
  loggingService.warn('Invitation email failed', {
    error: result.error,
    errorCode: result.errorCode,
  });
}
```

### 3. Notificación a admins de plataforma

```ts
// server/src/infrastructure/external/EsteiSyncService.ts
import { adminNotificationService } from '../../services/AdminNotificationService';

await adminNotificationService.notifySyncFailure({
  bookingId,
  error: errorMessage,
  // ...
});
```

### 4. Template de email personalizado

```ts
import {
  buildEmailHtml,
  buildHighlightBox,
  buildEmailButton,
  buildMutedText,
} from '../../infrastructure/email/emailTemplateBuilder';

const html = buildEmailHtml({
  title: 'Título del email',
  content: `
    <p>Hola ${userName},</p>
    ${buildHighlightBox(`<p>Referencia: ${refId}</p>`)}
    ${buildEmailButton({ text: 'Ver detalle', href: actionUrl })}
    ${buildMutedText('Este email fue generado automáticamente.')}
  `,
});
```

---

## Registro de reintentos

`NotificationRetryService` se llama automáticamente desde `InAppNotificationServiceImpl` al atrapar excepciones. No se invoca manualmente. El procesamiento de la cola se ejecuta por un job periódico. Para revisar estado:

```ts
const stats = await notificationRetryService.getQueueStats();
// { pending, processing, failed, completed }
```
