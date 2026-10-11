---
description: Nomenclatura y base de las ramas de git, derivadas de la tarea de Jira. Aplica cada vez que se vaya a crear una rama nueva en este repositorio.
---

# Nomenclatura de Ramas

Esta regla define cómo nombrar y desde dónde crear cada rama. La base de la rama y el nombre derivan de la tarea de Jira, salvo en hotfixes y en requerimientos sin ticket.

## Paso 0 — Leer la configuración

Antes de crear una rama, lee `.claude/pr-config.json` si existe. Usa:

- `baseBranch`: rama base por defecto para todo lo que no sea hotfix. Por defecto `development`.
- `productionBranch`: rama de producción de la que salen los hotfixes. Por defecto `main`.

Si el archivo no existe, asume `baseBranch: "development"` y `productionBranch: "main"`.

## Base de la rama

- **Hotfix**: se saca **directamente de producción** (`productionBranch`).
- **Todo lo demás** (`fix`, `feat`, etc.): se saca de `baseBranch` (`development`).

Antes de crear la rama, asegúrate de partir de la base correcta y actualizada:

```bash
git checkout <base>
git pull
git checkout -b <nombre-de-rama>
```

Donde `<base>` es `productionBranch` para hotfix, o `baseBranch` en cualquier otro caso.

## Nomenclatura

### Caso 1 — Hay ticket de Jira

```
[tipo]/[codigo-tarea][-intento]
```

- **tipo**: `fix`, `feat`, `hotfix`, etc. (en minúsculas), según la naturaleza del trabajo.
- **codigo-tarea**: el código del ticket de Jira tal cual, ej. `EWEB-874`, `EMPW-347`, `EPLT-19`.
- **intento**: ver "Regla del intento". Se omite si es la primera vez.

Ejemplos:
```
fix/EWEB-870
feat/EMPW-456
feat/EMPW-456-1
```

### Caso 2 — No hay ticket para el requerimiento

Si no existe un ticket de Jira para el trabajo, **pregunta al usuario qué desea realizar** para determinar el `tipo` de rama. Luego usa:

```
[tipo]/[nombre-git-desarrollador][fecha-de-hoy][-intento]
```

- **tipo**: igual que arriba (`fix`, `feat`, etc.), definido a partir de lo que el usuario indique.
- **nombre-git-desarrollador**: obtenido con `git config user.name`. Normalízalo a un slug sin espacios ni mayúsculas (ej. "Javier Teixeira" → `javier-teixeira`).
- **fecha-de-hoy**: en formato `YYYY-MM-DD`, obtenida con `date +%F`.
- **intento**: ver "Regla del intento".

Ejemplo:
```
feat/javier-teixeira-2026-06-16
fix/javier-teixeira-2026-06-16-1
```

## Regla del intento

El sufijo `-intento` se agrega **solo si ya existe una rama con exactamente el mismo nombre base**. La numeración empieza en `1` y crece de uno en uno hasta encontrar un nombre libre. Aplica igual en ambos casos (con ticket y sin ticket).

Para verificar existencia, comprueba ramas locales y remotas:

```bash
git branch --list "<nombre-base>"
git ls-remote --heads origin "<nombre-base>"
```

Procedimiento:
1. Construye el nombre base (sin sufijo).
2. Si no existe ninguna rama con ese nombre exacto → úsalo tal cual.
3. Si ya existe → prueba `<nombre-base>-1`, luego `<nombre-base>-2`, etc., hasta encontrar uno que no exista. Usa el primero libre.

Ejemplo: si `feat/EMPW-456` ya existe, la nueva rama será `feat/EMPW-456-1`; si esa también existe, `feat/EMPW-456-2`.

## Notas

- El `tipo` de rama debe ser coherente con el `type` que luego usarás en commits y en el título de la PR (ver reglas de commits y de pull requests).
- No incluyas el título descriptivo del ticket en el nombre de la rama: solo el código de tarea. El contexto descriptivo va en la PR, no en la rama.