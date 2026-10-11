---
name: access-control
description: Administra el sistema centralizado de roles, permisos, rutas frontend
  y endpoints backend en `shared/access-control/`. Usar cuando se agreguen o modifiquen
  rutas, endpoints, permisos, roles o validaciones de acceso.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Access control

## Cuándo usar este skill

- Ruta frontend nueva o cambio de acceso en una ruta existente
- Endpoint backend nuevo o cambio de permisos
- Alta o ajuste de permisos/roles
- Dudas sobre cómo registrar acceso en `shared/access-control/`

## No usar este skill para

- Implementar la lógica HTTP completa del endpoint → usar también `api-routes`
- Cambios visuales de UI sin impacto de permisos
- Migraciones o cambios de schema sin relación con permisos

## Rutas relevantes

- `shared/access-control/index.ts`
- `shared/access-control/types.ts`
- `shared/access-control/enums.ts`
- `shared/access-control/role-permissions.ts`
- `shared/access-control/routes/*.routes.ts`
- `shared/access-control/endpoints/*.endpoints.ts`
- `shared/access-control/mappings.ts`
- `shared/access-control/helpers.ts` — utilitarios de consulta sobre el sistema de permisos
- `shared/access-control/validation.ts` — validación cruzada entre rutas y endpoints
- `shared/access-control/intentional-mismatches.ts` — allowlist de diferencias arquitectónicas rutas↔endpoints que NO son bugs de seguridad. **Antes de "arreglar" una discrepancia entre rutas y endpoints, verificar si está listada aquí como intencional.**

## Reglas obligatorias

- No crear rutas ni endpoints fuera del sistema centralizado.
- Mantener principio default-deny: si algo no está registrado, no debe quedar expuesto por accidente.
- Registrar rutas frontend y endpoints backend en los archivos correctos por contexto.
- Verificar si la protección es por permisos, por rol o por usuario autenticado.
- Cuando una ruta frontend dependa de endpoints concretos, actualizar el mapping ruta → endpoint.
- Aplicar doble validación cuando corresponda: visibilidad en frontend y enforcement real en backend.

## Flujo mínimo

### Ruta frontend nueva

1. Elegir el archivo `*.routes.ts` correcto.
2. Registrar la ruta con roles/permisos permitidos.
3. Actualizar el mapeo ruta → endpoints si la pantalla consume endpoints protegidos.
4. Validar con un usuario autorizado y otro no autorizado.

### Endpoint backend nuevo

1. Elegir el archivo `*.endpoints.ts` correcto.
2. Registrar método + patrón + permisos requeridos.
3. Verificar exports desde `endpoints/index.ts`.
4. Confirmar que el middleware correcto hace enforcement en runtime.

### Permiso nuevo

1. Agregarlo al enum o fuente central correspondiente.
2. Asignarlo a los roles necesarios.
3. Usarlo en rutas/endpoints y tests afectados.

## Checklist

- ¿La ruta o endpoint quedó registrado en `shared/access-control/`?
- ¿El permiso existe y está asignado al rol correcto?
- ¿Se actualizó el mapping ruta → endpoint si aplica?
- ¿Se probó acceso permitido y denegado?
- ¿El backend sigue protegido aunque alguien salte el frontend?

## Skills que suelen acompañar este

- `api-routes`
- `testing-convention`
- `code-quality`
