---
title: "[🔒 Seguridad] Registro y login revelan si un email existe, su rol y el estado de la cuenta"
labels: [security, bug, P1, services]
issue: 20
url: https://github.com/Teixeira49/vitaly_backend/issues/20
---

## Descripción

Los flujos públicos de registro y login devuelven mensajes distintos según el estado de la cuenta asociada a un email. Esto permite enumerar usuarios sin credenciales: saber qué correos están registrados, con qué rol (administrador de sistema, administrador de escuela, doctor, representante) y si la cuenta está eliminada o pendiente de verificación. En una plataforma con datos de salud de menores, esa información facilita ataques dirigidos (phishing a doctores o administradores, credential stuffing sobre cuentas confirmadas).

## Evidencia

- `app/services/auth_service.py:12-21` — `_create_base_user`: si el email ya existe, consulta `user_roles` y responde `400` con `detail=f"El usuario ya existe bajo el rol: {role}"`. Lo usan los cuatro endpoints públicos de registro (`app/api/v1/endpoints/auth.py:10`, `:18`, `:27`, `:36`).
- `app/services/auth_service.py:127-137` — `authenticate_user`: las respuestas `403 "El usuario ha sido eliminado"` y `403 "El usuario está inactivo, debe esperar verificación"` se evalúan **antes** de verificar la contraseña (`:139`), por lo que se obtienen con cualquier contraseña.
- `app/core/exceptions.py` — el handler global copia `exc.detail` al campo `message` del envelope, así que el texto llega íntegro al cliente.

## Comportamiento actual vs esperado

| Caso | Actual | Esperado |
|---|---|---|
| Registro con email existente | `400` + rol del usuario existente | Respuesta genérica que no revele existencia ni rol |
| Login de cuenta eliminada, contraseña incorrecta | `403 "El usuario ha sido eliminado"` | `401 "Credenciales incorrectas"` |
| Login de cuenta inactiva, contraseña incorrecta | `403 "...debe esperar verificación"` | `401 "Credenciales incorrectas"` |
| Login de email inexistente | `401 "Credenciales incorrectas"` | Sin cambios |

## Impacto

- Afecta endpoints públicos (sin token): cualquiera puede consultar emails de forma masiva.
- Expone el rol de cuentas privilegiadas (`admin_sistema`, `admin_escuela`, `doctor`).
- No expone datos médicos directamente, pero reduce el costo de ataques contra cuentas con acceso a ellos.
- No hay rate limiting visible en `auth.py`, lo que agrava la enumeración.

## Propuesta de solución

1. **Registro:** eliminar el rol del mensaje. Opciones a decidir:
   - Mensaje genérico ("No fue posible completar el registro con los datos proporcionados").
   - O respuesta idéntica a un registro exitoso con notificación por correo al titular (requiere servicio de email, hoy inexistente).
2. **Login:** verificar la contraseña **antes** de evaluar `is_deleted` / `is_active`. Solo con credenciales válidas se informa el estado de la cuenta.
3. Evaluar rate limiting por IP/email en `/auth/login` y `/auth/register-*` (issue aparte si se aprueba).
4. Coordinar con el frontend (`../vitaly-care-for-families`) si algún flujo depende del texto actual del mensaje.

## Criterios de aceptación

- [ ] Registrar un email existente no revela el rol ni distingue el caso en el mensaje.
- [ ] Login con contraseña incorrecta responde `401 "Credenciales incorrectas"` para cuentas inexistentes, eliminadas e inactivas.
- [ ] Login con contraseña correcta sigue informando cuenta eliminada/inactiva.
- [ ] Tests cubren los cuatro casos de la tabla (ver skill `vitaly-feature-testing`).
- [ ] El frontend sigue mostrando mensajes coherentes.

## Referencias

- Skill `vitaly-rbac` (claims y gates de autenticación).
- Skill `vitaly-feature-testing` (casos 401/403).
- Rule `.agents/rules/standard-response.md` (envelope de errores).
- Relacionado: #19 (registro deja filas huérfanas en `user`, mismo flujo `_create_base_user`).
