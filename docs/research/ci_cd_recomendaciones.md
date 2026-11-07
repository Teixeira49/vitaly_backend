# Recomendaciones de CI/CD para Vitaly Backend

**Fecha:** 2026-10-17
**Objetivo:** Documentar mejoras de integración y despliegue continuos que pueden incorporarse al backend a partir de su configuración actual.
**Estado:** Propuesta de investigación; no implementa cambios en workflows ni infraestructura.

## 1. Diagnóstico actual

La revisión inicial se realizó sobre la rama `ci/GH-35` (commit `1240b29`), que contiene GitHub Actions en `.github/workflows/ci.yml`. La base `origin/development` de este documento (commit `135ef13`) todavía no contiene ese workflow. El diagnóstico siguiente describe la rama de CI; su integración en `development` es un paso previo a las ampliaciones propuestas.

El workflow revisado:

- Se ejecuta en pull requests, en pushes a `development` y `main`, y manualmente.
- Usa Python 3.10 y caché de pip.
- Instala las dependencias de desarrollo y ejecuta Ruff y pytest.
- Limita los permisos a lectura del contenido, cancela ejecuciones anteriores del mismo grupo y establece un timeout de diez minutos.

En esa rama, las pruebas bloquean conexiones externas mediante `pytest-socket` y usan credenciales ficticias, lo que permite mantener el CI independiente de Supabase e ImageKit. Ruff comprueba errores críticos; el `CONTRIBUTING.md` de esa rama documenta la ampliación de reglas como trabajo separado.

No se encontró un workflow de despliegue en el repositorio inspeccionado. Esto no confirma la ausencia de despliegues configurados directamente en un proveedor externo. Tampoco se verificaron los rulesets ni las protecciones de ramas en GitHub.

La recomendación es ampliar el GitHub Actions existente y añadir un flujo de despliegue por ambientes.

## 2. Prioridades propuestas

Los esfuerzos son estimaciones relativas, sujetas a los permisos disponibles, los resultados iniciales y el proveedor de alojamiento.

| Prioridad | Mejora | Aplicación concreta en Vitaly | Esfuerzo estimado |
| --- | --- | --- | --- |
| 1 | Exigir CI antes del merge | Verificar y configurar protección de `development` y `main` para exigir el check **Lint and tests**. La existencia del workflow no activa esta protección por sí sola. | Bajo |
| 2 | Auditoría de dependencias | Añadir un job con `pip-audit` en los PR y una ejecución semanal para detectar vulnerabilidades conocidas en las dependencias instaladas. | Bajo |
| 3 | Actualizaciones automáticas | Configurar Dependabot para Python y GitHub Actions, con PR semanales agrupados que pasen por el CI existente. | Bajo |
| 4 | Cobertura de pruebas | Incorporar `pytest-cov`, publicar el reporte como artefacto y medir la cobertura actual antes de fijar un mínimo. Usar el reporte para identificar servicios críticos sin pruebas. | Bajo |
| 5 | Instalaciones reproducibles | Generar un archivo de dependencias resueltas con versiones exactas y usarlo tanto en CI como en despliegue. Varias dependencias actuales solo tienen un límite mínimo, por lo que dos instalaciones pueden resolver versiones diferentes. | Medio |
| 6 | Validación del contrato OpenAPI | Comparar el contrato del PR con el de su rama destino para detectar campos eliminados, nuevos campos obligatorios o cambios de tipos que afecten al frontend. Coordinar los cambios de contrato con sus interfaces TypeScript. | Medio |
| 7 | Despliegue con verificación posterior | Desplegar `development` a staging y `main` a producción después de pasar CI; verificar la API al terminar y conservar la versión anterior para poder restaurarla. | Medio; depende del hosting |

### Auditoría y actualizaciones de dependencias

`pip-audit` revisa vulnerabilidades conocidas en entornos Python y archivos de dependencias. Ejecutarlo también de forma periódica permite detectar avisos publicados aunque no haya cambios recientes en el código. Véase su [documentación oficial](https://github.com/pypa/pip-audit).

Dependabot puede mantener actualizadas las dependencias Python y las acciones del workflow mediante pull requests. Las actualizaciones deben atravesar los mismos controles de CI que el resto de los cambios. Véase la [configuración oficial de actualizaciones de versiones](https://docs.github.com/en/code-security/dependabot/dependabot-version-updates/configuring-dependabot-version-updates).

### Integridad de las acciones de CI

Como mejora adicional, fijar las acciones del workflow a un **SHA completo**, acompañado de actualizaciones automatizadas. Esto permite controlar exactamente qué código ejecuta el pipeline. GitHub recomienda esta práctica en su [referencia de uso seguro de Actions](https://docs.github.com/en/actions/reference/security/secure-use).

## 3. Flujo de despliegue propuesto

```text
PR → lint + tests + auditoría + contrato
                  ↓ merge
development → CI → staging → smoke tests
                  ↓ promoción a main
main → CI → producción → smoke tests
```

Staging debe tener configuración y credenciales separadas de producción. Los secretos se pueden organizar por ambiente mediante GitHub Environments. Sus controles disponibles dependen del plan y de la visibilidad del repositorio; deben comprobarse antes de diseñar las restricciones. Véase la [documentación de despliegues y ambientes](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

El mecanismo concreto de despliegue y restauración queda pendiente de conocer el proveedor donde está alojada la API. La versión desplegada debe poder identificarse y debe conservarse una versión anterior recuperable.

### Particularidad del endpoint de salud

En [app/main.py](../../app/main.py), `/health` captura el error de conexión a Supabase y devuelve una respuesta HTTP 200 incluso si la base de datos está desconectada. El campo `status` continúa siendo `online`; el resultado de la conexión se comunica en `database`.

Por tanto, una verificación posterior al despliegue debe comprobar también que `database == "connected"`. Revisar únicamente el código HTTP produciría un resultado engañoso. Este documento registra esa condición; no modifica el endpoint.

## 4. Orden recomendado de adopción inmediata

1. Integrar o confirmar la integración del CI de `ci/GH-35` y exigir su check antes del merge en las ramas protegidas.
2. Incorporar auditoría de dependencias y actualizaciones automatizadas.
3. Publicar un primer reporte de cobertura para establecer una línea base.
4. Fijar las acciones a SHA completo y hacer reproducible la instalación de dependencias.
5. Añadir la comparación de contratos OpenAPI.
6. Conectar staging al proveedor de alojamiento y después habilitar el flujo de producción con verificación posterior y recuperación de la versión anterior.

La primera entrega recomendada comprende protección de ramas, auditoría de dependencias, Dependabot y reporte de cobertura. Son mejoras pequeñas que aprovechan el CI actual. El siguiente paso es conectar staging al proveedor donde esté alojada la API.
