---
description: Nomenclatura y base de las ramas de git, derivadas del issue de GitHub. Aplica cada vez que se vaya a crear una rama nueva en este repositorio.
---

# Nomenclatura de Ramas

Esta regla define cómo nombrar y desde dónde crear cada rama. El nombre de la rama deriva del issue de GitHub (Vitaly usa **GitHub Issues** como gestor de tareas), salvo en requerimientos sin issue.

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

### Caso 1 — Hay issue de GitHub

```
[tipo]/GH-<n>[-intento]
```

- **tipo**: `fix`, `feat`, `hotfix`, etc. (en minúsculas), según la naturaleza del trabajo.
- **GH-<n>**: prefijo fijo `GH-` seguido del número del issue de GitHub (sin `#`), ej. `GH-12` para el issue `#12`. Verifica que el issue existe con `gh issue view <n> --json number,title,state`.
- **intento**: ver "Regla del intento". Se omite si es la primera vez.

Ejemplos:
```
fix/GH-7
feat/GH-12
feat/GH-12-1
```

### Caso 2 — No hay issue para el requerimiento

Si no existe un issue de GitHub para el trabajo (y el usuario no quiere crearlo primero con el skill `vitaly-issue`), **pregunta al usuario qué desea realizar** para determinar el `tipo` de rama. Luego usa:

```
[tipo]/[nombre-git-desarrollador]-[fecha-de-hoy][-intento]
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

El sufijo `-intento` se agrega **solo si ya existe una rama con exactamente el mismo nombre base**. La numeración empieza en `1` y crece de uno en uno hasta encontrar un nombre libre. Aplica igual en ambos casos (con issue y sin issue).

Para verificar existencia, comprueba ramas locales y remotas:

```bash
git branch --list "<nombre-base>"
git ls-remote --heads origin "<nombre-base>"
```

Procedimiento:
1. Construye el nombre base (sin sufijo).
2. Si no existe ninguna rama con ese nombre exacto → úsalo tal cual.
3. Si ya existe → prueba `<nombre-base>-1`, luego `<nombre-base>-2`, etc., hasta encontrar uno que no exista. Usa el primero libre.

Ejemplo: si `feat/GH-12` ya existe, la nueva rama será `feat/GH-12-1`; si esa también existe, `feat/GH-12-2`.

## Notas

- El `tipo` de rama debe ser coherente con el `type` que luego usarás en commits y en el título de la PR (ver reglas de commits y de pull requests).
- No incluyas el título descriptivo del issue en el nombre de la rama: solo `GH-<n>`. El contexto descriptivo va en la PR, no en la rama.