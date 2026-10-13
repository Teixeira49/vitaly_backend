---
name: git-safety
description: Define las reglas de seguridad para operaciones git que pueden destruir trabajo
  (reset, checkout, rebase, force push) y los procedimientos de recuperación cuando
  algo se rompe. Usar antes de cualquier operación git destructiva o cuando haya
  archivos staged/untracked en juego.
metadata:
  owner: vitaly-backend
  format: agent-skills-v1
---

# Git safety

> **Motivación**: un `git reset --hard` ejecutado con archivos staged que nunca
> llegaron a un commit los borra del working tree y del index. La recuperación,
> si es posible, solo es parcial (blobs sueltos en `.git/objects`). Este skill
> existe para que eso **no ocurra**.

## Ramas del repositorio

Fuente de verdad: `.agents/rules/branch-naming.md` y `.agents/rules/pull-request.md`.

| Rama | Rol |
|------|-----|
| `development` | Rama base de integración. De aquí salen `feat/`, `fix/`, etc. |
| `main` | Producción. Solo de aquí salen (y aquí vuelven) los `hotfix/`. |
| `staging` | Existe en el remoto, pero ninguna regla define su flujo. Trátala como protegida. |

Las tres son **ramas compartidas protegidas**: nunca se reescribe su historia.

## Cuándo usar este skill

- Antes de ejecutar `git reset --hard`, `git checkout` con cambios sin commitear, `git rebase` o `git push --force`
- Cuando hay archivos **staged pero no commiteados** y se va a cambiar de rama o resetear
- Cuando se pierde trabajo y hay que recuperarlo
- Al diseñar un flujo de "mover commits entre ramas"
- Cuando un pre-commit hook aborta y deja el index en estado mixto

## Regla de oro

> **Si hay algo en staging o en el working tree que no está commiteado, detente
> antes de cualquier operación destructiva. Primero `stash`, después operas.**

`git status` debe mostrar **working tree clean** antes de:

- `git reset --hard <ref>`
- `git checkout <ref>` cuando el ref es lejano
- `git rebase` (interactivo o no)
- `git pull` con merge sobre una rama divergente
- Cualquier `git clean -fd`

---

## Operaciones destructivas — reglas

### `git reset --hard`

**Riesgo**: borra del working tree y del index TODO lo que no esté en el commit
destino. Los archivos staged que nunca llegaron a un commit **se pierden**.

**Reglas**:

1. Antes de ejecutarlo, corre `git status` y verifica que el working tree esté limpio.
2. Si hay cambios sin commitear, **haz stash primero**:
   ```bash
   git stash push -u -m "descripción del stash"
   git reset --hard <ref>
   git stash pop  # si quieres recuperarlos después
   ```
3. NUNCA lo uses para "limpiar" cuando hay archivos untracked importantes.
4. Para volver a `origin/<branch>` cuando hay trabajo pendiente:
   - **MAL**: `git reset --hard origin/development` (con archivos staged)
   - **BIEN**: stash, reset, y luego decidir si hacer pop o descartar

### `git checkout <ref>`

**Riesgo**: si hay archivos modificados que existen en `<ref>` con contenido
distinto, git puede negarse o (peor, con `--force`) sobrescribirlos.

**Reglas**:

1. Working tree limpio antes de hacer checkout a una rama lejana.
2. Para mover trabajo a otra rama: usa `git stash` o `git switch -c <nueva-rama>`.
3. NUNCA hagas checkout de un commit antiguo con `--force`.

### `git rebase`

**Riesgo**: reescribe la historia. Si los conflictos se resuelven mal, se pierden cambios.

**Reglas**:

1. Trabaja siempre sobre una rama de trabajo (`feat/`, `fix/`, `hotfix/`...). NUNCA hagas rebase de `development`, `staging` o `main`.
2. Haz un backup antes: `git branch backup/<nombre-de-rama>`.
3. Si el rebase falla, `git rebase --abort` antes de seguir.
4. NUNCA hagas rebase de commits ya publicados en una rama compartida.

### `git push --force`

**Riesgo**: pisa el trabajo de otras personas sin aviso.

**Reglas**:

1. Usa SIEMPRE `git push --force-with-lease` en lugar de `--force`.
2. NUNCA hagas force push a `development`, `staging` o `main` (la protección de ramas debería bloquearlo, pero verifícalo).
3. Solo haz force push a tu propia rama de trabajo.

---

## Movimiento de commits entre ramas

**Caso típico**: hiciste commits en `development` por error y quieres moverlos a una rama de trabajo.

**Procedimiento seguro** (el nombre de la rama sigue `.agents/rules/branch-naming.md`):

```bash
# 1. ESTANDO en development con los commits a mover, crea la rama DESDE EL ESTADO ACTUAL
git checkout -b feat/GH-12

# 2. Ahora development local y feat/GH-12 apuntan al mismo HEAD

# 3. Resetea development al remoto SOLO si está limpio
git checkout development
git status  # ¡VERIFICA QUE ESTÉ LIMPIO!
git reset --hard origin/development

# 4. Vuelve a la rama de trabajo: todo sigue intacto
git checkout feat/GH-12
```

Si los commits se hicieron por error en `main` y son un parche urgente, la rama
destino es `hotfix/<ticket>` y el reset se hace contra `origin/main`.

**Antipatrón**: hacer `git reset --hard origin/development` ANTES de crear la rama
de trabajo → se pierden los commits no publicados.

---

## Recuperación — si algo se rompió

### Recuperar commits "perdidos" con `git reflog`

`reflog` registra TODOS los movimientos de HEAD, incluidos los resets. Lo perdido
suele estar ahí.

```bash
git reflog                    # listar movimientos recientes
git reset --hard HEAD@{N}     # volver al estado de hace N movimientos
```

### Recuperar archivos staged perdidos por `reset --hard`

Si los archivos solo estaban en staging (nunca en un commit), `reflog` NO ayuda.
PERO los blobs siguen en `.git/objects`:

```bash
# 1. Listar blobs sueltos recientes (últimas 2 h)
find .git/objects -type f -mmin -120 ! -path "*/pack/*" 2>/dev/null

# 2. Ver el tipo de cada objeto
for f in $(find .git/objects -type f -mmin -120 ! -path "*/pack/*"); do
  hash="${f##*/}"; dir="${f%/*}"; dir="${dir##*/}"
  full="$dir$hash"
  echo "$full $(git cat-file -t $full)"
done

# 3. Para los blobs (no trees ni commits), ver las primeras líneas
git cat-file -p <hash> | head -3

# 4. Recuperar a un archivo
git cat-file -p <hash> > ruta/al/archivo.recuperado
```

**Identificación**: si los archivos tienen encabezados reconocibles (ej. el
docstring de un módulo Python o el front-matter de un markdown), se pueden
renombrar a partir de ese contenido.

### Recuperar con `git fsck`

```bash
git fsck --lost-found       # encuentra commits/blobs/trees colgantes
ls .git/lost-found/         # quedan aquí
```

### Si nada funciona

1. **NO ejecutes `git gc`** (borra los blobs sueltos para siempre).
2. **NO sigas trabajando en el repo** (puedes sobrescribir objetos recuperables).
3. Haz una copia completa de `.git/` antes de seguir.
4. Busca en otras fuentes: `git stash list`, copias locales, otras ramas, otros devs.

---

## Pre-commit hooks que abortan

**Síntoma**: un hook (formatter, linter como `ruff`, tests) falla y deja el index
en estado mixto (`AM`: archivos modificados por el hook pero commit no concretado).

**Reglas**:

1. NO hagas `git reset --hard` si el hook abortó: los cambios staged son válidos.
2. Corrige la causa del fallo (error de lint, config rota, etc.).
3. Haz `git add` de los archivos que el hook modificó.
4. Reintenta el commit (sin `--no-verify`).

---

## Antes de operar — checklist mental

- [ ] ¿`git status` muestra working tree clean?
- [ ] Si NO, ¿qué hay sin commitear? ¿Es importante?
- [ ] ¿Hice stash de lo importante?
- [ ] ¿La operación es reversible?
- [ ] Si NO es reversible, ¿creé una rama de backup (`git branch backup/X`)?
- [ ] ¿Estoy seguro de no estar reescribiendo `development`, `staging` o `main`?

---

## Referencias

- `.agents/rules/branch-naming.md` — nomenclatura y rama base (`development`; `main` para hotfix).
- `.agents/rules/commit-conventions.md` — formato de commits (Conventional Commits con gitmoji).
- `.agents/rules/pull-request.md` — rama destino y formato de PR.
- Skill `vitaly-branch-pr` — flujo de PR (no son operaciones destructivas, son cosas distintas).
