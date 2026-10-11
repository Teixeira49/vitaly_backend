---
name: git-safety
description: Define las reglas de seguridad para operaciones git que pueden destruir trabajo
  (reset, checkout, rebase, force push) y los procedimientos de recuperación cuando
  algo se rompe. Usar antes de cualquier operación git destructiva o cuando haya
  archivos staged/untracked en juego.
metadata:
  owner: estei-empresas
  format: agent-skills-v1
---

# Git safety

> **Lección dura aprendida**: en abril 2026 se perdieron 49 archivos por un
> `git reset --hard` con archivos staged untracked. Recuperación parcial via
> loose blobs en `.git/objects`. Este skill existe para que **no vuelva a pasar**.

## Cuándo usar este skill

- Antes de ejecutar `git reset --hard`, `git checkout` con cambios sin commitear, `git rebase` o `git push --force`
- Cuando hay archivos **staged pero no commiteados** y se va a cambiar de rama o resetear
- Cuando se pierde trabajo y hay que recuperarlo
- Al diseñar un flujo de "mover commits entre ramas"
- Cuando un pre-commit hook aborta y deja el index en estado mixto

## Regla de oro

> **Si hay algo en staging o working tree que no está commiteado, detenete antes
> de cualquier operación destructiva. Stash primero, opera después.**

`git status` debe mostrar **clean working tree** antes de:

- `git reset --hard <ref>`
- `git checkout <ref>` cuando el ref es lejano
- `git rebase` interactivo o no
- `git pull` con merge fast-forward sobre divergencia
- Cualquier `git clean -fd`

---

## Operaciones destructivas — reglas

### `git reset --hard`

**Riesgo**: borra del working tree e index TODO lo que no esté en el commit
target. Archivos staged que nunca llegaron a un commit **se pierden**.

**Reglas**:

1. Antes de ejecutar, correr `git status` y verificar working tree clean
2. Si hay cambios sin commitear, **stash primero**:
   ```bash
   git stash push -u -m "descripción del stash"
   git reset --hard <ref>
   git stash pop  # si querés recuperar después
   ```
3. NUNCA usar para "limpiar" cuando hay archivos untracked importantes
4. Para volver a `origin/<branch>` cuando hay trabajo pendiente:
   - **MAL**: `git reset --hard origin/develop` (con archivos staged)
   - **BIEN**: stash, reset, decidir si pop o descartar

### `git checkout <ref>`

**Riesgo**: si hay archivos modificados que existen en `<ref>` pero con contenido
distinto, git puede negarse o (peor) sobrescribir.

**Reglas**:

1. Working tree clean antes de checkout a rama lejana
2. Para mover trabajo a otra rama: usá `git stash` o `git switch -c <new-branch>`
3. NUNCA hacer checkout de un commit antiguo con `--force`

### `git rebase`

**Riesgo**: re-escribe historia. Si hay conflictos mal resueltos, se pierden cambios.

**Reglas**:

1. Trabajar siempre sobre rama feature, NUNCA rebase sobre `develop`/`staging`/`main`
2. Hacer backup antes: `git branch backup/<feature-name>`
3. Si rebase falla, `git rebase --abort` antes de seguir
4. NUNCA rebase commits ya pusheados a remoto compartido

### `git push --force`

**Riesgo**: pisa trabajo de otros sin aviso.

**Reglas**:

1. Usar `git push --force-with-lease` SIEMPRE en lugar de `--force`
2. NUNCA force push a `develop`, `staging` o `main` (branch protection debería bloquearlo, pero verificar)
3. Solo force push a tu propia rama feature

---

## Movimiento de commits entre ramas

**Caso típico**: hiciste commits en `develop` por error, querés moverlos a una rama feature.

**Procedimiento seguro**:

```bash
# 1. ESTANDO en develop con los commits a mover, crear la rama feature DESDE EL ESTADO ACTUAL
git checkout -b feat/mi-feature

# 2. Ahora develop local tiene los commits, feat/mi-feature también (mismo HEAD)

# 3. Resetear develop al origin SOLO si está clean
git checkout develop
git status  # ¡VERIFICAR LIMPIO!
git reset --hard origin/develop

# 4. Volver a la rama feature, todo intacto
git checkout feat/mi-feature
```

**Antipatrón**: hacer `git reset --hard origin/develop` ANTES de crear la rama
feature → se pierden los commits no pusheados.

---

## Recovery — si algo se rompió

### Recuperar commits "perdidos" con `git reflog`

`reflog` registra TODOS los movimientos de HEAD, incluyendo resets. Lo perdido
suele estar ahí.

```bash
git reflog                    # listar movimientos recientes
git reset --hard HEAD@{N}     # volver al estado N pasos atrás
```

### Recuperar archivos staged perdidos por `reset --hard`

Si los archivos solo estaban en staging (no en commit), `reflog` NO ayuda
porque nunca fueron commit. PERO los blobs siguen en `.git/objects`:

```bash
# 1. Listar loose blobs recientes (últimas 2h)
find .git/objects -type f -mmin -120 ! -path "*/pack/*" 2>/dev/null

# 2. Ver tipo de cada blob
for f in $(find .git/objects -type f -mmin -120 ! -path "*/pack/*"); do
  hash="${f##*/}"; dir="${f%/*}"; dir="${dir##*/}"
  full="$dir$hash"
  echo "$full $(git cat-file -t $full)"
done

# 3. Para blobs (no trees ni commits), ver primer línea
git cat-file -p <hash> | head -3

# 4. Recuperar a archivo
git cat-file -p <hash> > path/al/archivo.recuperado
```

**Identificación**: si los archivos tienen front-matter o headers identificables
(ej: markdown con `--- id: faq-X`), se pueden nombrar automáticamente.

### Recuperar con `git fsck`

```bash
git fsck --lost-found       # encuentra dangling commits/blobs/trees
ls .git/lost-found/         # los encuentra acá
```

### Si nada funciona

1. **NO ejecutar `git gc`** (limpia los blobs sueltos para siempre)
2. **NO seguir trabajando en el repo** (puede sobreescribir blobs en uso)
3. Hacer copia de `.git/` completa antes de seguir
4. Buscar en otra fuente: `git stash list`, copia local, otra rama, otro dev

---

## Pre-commit hooks que abortan

**Síntoma**: hook (Prettier, lint, GGA) falla, deja el index en estado mixto
(`AM`, archivos modificados por el hook pero commit no concretado).

**Reglas**:

1. NO hacer `git reset --hard` si el hook abortó — los cambios staged son válidos
2. Arreglar la causa del hook (typo, config rota, etc.)
3. `git add` los archivos que el hook modificó
4. Reintentar el commit

---

## Antes de operar — checklist mental

- [ ] ¿`git status` muestra working tree clean?
- [ ] Si NO, ¿qué hay sin commitear? ¿Es importante?
- [ ] ¿Hice stash de lo importante?
- [ ] ¿La operación que voy a hacer es reversible?
- [ ] Si NO es reversible, ¿hice backup branch (`git branch backup/X`)?

---

## Referencias

- Lección que originó este skill: `engram://gotcha/git-reset-hard-staged-untracked`
- AGENTS.md sección "Git branching" — política del repo (ramas desde develop, etc.)
- Skill `branch-pr` — convenciones de PR (no operaciones destructivas, son cosas distintas)
