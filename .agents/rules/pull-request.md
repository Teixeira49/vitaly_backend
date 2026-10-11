---
description: Flujo, título y descripción para crear Pull Requests, integrando el issue de GitHub y los commits de la rama. Aplica cada vez que se vaya a preparar o disparar una PR en este repositorio.
---

# Pull Requests

Esta regla define cómo preparar y disparar Pull Requests. Cubre tres cosas: el **nivel de disparo** (cuánta autonomía tiene la IA para subir la PR), el **título** y la **descripción**. La descripción se construye a partir del **issue de GitHub** (Vitaly usa **GitHub Issues** como gestor de tareas, no Jira) y de los **commits de la rama**.

## Paso 0 — Leer la configuración

Antes de cualquier acción de PR, lee el archivo de configuración del repositorio:

```
.claude/pr-config.json
```

De ahí se obtienen:

- `triggerMode`: nivel de disparo (`"manual"` | `"ask"` | `"auto"`).
- `draftsDir`: carpeta donde se guardan los markdown de PR. Por defecto `docs/pull-requests/`.
- `reviewers`: lista de reviewers candidatos del equipo (puede estar vacía).
- `baseBranch`: rama destino por defecto de las PR (todo lo que no sea hotfix). Por defecto `development`.
- `productionBranch`: rama de producción, destino de los hotfixes. Por defecto `main`.

Si el archivo no existe, asume `triggerMode: "manual"`, `draftsDir: "docs/pull-requests/"`, `reviewers: []`, `baseBranch: "development"` y `productionBranch: "main"`, e informa al usuario de que conviene crearlo.

## Información requerida

Antes de ejecutar, verifica que tengas:

1. **Número del issue de GitHub** — ejemplo: `12` (issue `#12`, referenciado como `GH-12` en ramas y títulos).
2. **Nombre de la rama** — ejemplo: `fix/GH-12`. Si no se indica, usa la rama actual (`git branch --show-current`).

Si falta el número de issue, solicítalo antes de continuar. Si el usuario no tiene issue, propón crearlo primero con el skill `vitaly-issue`; si decide continuar sin issue, omite `GH-<n>` y `Closes #<n>` y usa la rama del caso sin issue (ver `branch-naming.md`).

## Paso 1 — Obtener el issue de GitHub

Ejecuta vía Bash con GitHub CLI:

```bash
gh issue view <n> --json title,body,labels,state
```

Extrae:

- Título (`title`)
- Descripción (`body`)
- Labels (`labels[].name`) — determinan el `type` del título de la PR (ver "Título de la PR")
- Estado (`state`) — si el issue está `CLOSED`, avisa al usuario antes de continuar

Si `gh` no está disponible o falla la consulta, informa al usuario y pídele que pegue manualmente el título y las labels del issue para poder continuar.

## Paso 2 — Obtener los commits de la rama

Ejecuta vía Bash:

```bash
git log <rama-destino>..<nombre_de_rama> --oneline --no-merges
```

Donde `<rama-destino>` es la base de la PR: `productionBranch` si la rama es `hotfix/`, o `baseBranch` en cualquier otro caso (ver "Rama destino (base) de la PR").

Usa los mensajes de commit para entender qué cambios se realizaron y redactar la descripción.

## Paso 3 — Resolver el template de descripción

Este repositorio **no** tiene `.github/pull_request_template.md`, por lo que se usa la plantilla embebida en la sección "Descripción de la PR" de esta regla. Si en el futuro se agrega ese archivo, **léelo y úsalo como base** (fuente única de verdad).

**Secciones obligatorias (siempre presentes).** Independientemente de la plantilla base que se use, la PR generada **debe incluir siempre** estas cuatro secciones, en este orden. Si el template base no las trae, **agrégalas** al final del cuerpo:

1. `## Descripción`
2. `## Tipo de cambio`
3. `## ¿Cómo se ha probado esto?` (incluyendo el bloque **Configuración de prueba**)
4. `## Lista de Verificación`

El contenido y los valores por defecto de cada sección están definidos en "Descripción de la PR" (plantilla embebida + "Pautas de llenado"). Nunca subas una PR sin las secciones 3 y 4.

## Paso 4 — Siempre: escribir el markdown de la PR

Independientemente del modo, **siempre** generas un archivo markdown con el contenido completo de la PR (título + descripción) y lo guardas en `draftsDir` con el nombre de la rama:

```
<draftsDir>/<nombre-de-la-rama>.md
```

Ejemplo: rama `fix/GH-12` → `docs/pull-requests/fix-GH-12.md` (sustituye `/` por `-` en el nombre del archivo).

## Paso 5 — Comportamiento según `triggerMode`

### `manual`
Te detienes después de escribir el archivo. No subes nada. Informa la ruta del archivo generado y termina. No crear commits, no hacer push, no abrir PRs.

### `ask`
1. Muestra en el chat el **contenido completo** del markdown generado.
2. Muestra además la **rama destino** de la PR, la lista de **reviewers candidatos** (de `pr-config.json`) y las **labels sugeridas** (ver "Otras configuraciones").
3. Espera a que el usuario **apruebe por escrito** (ej. "apruebo", "súbela", "adelante"). Sin aprobación explícita escrita, NO subes la PR.
4. Tras la aprobación, sube la PR usando el archivo como descripción (ver "Cómo subir la PR").

### `auto`
1. Toma el archivo generado y úsalo como descripción de la PR.
2. Asigna labels automáticamente según el sentido lógico de los cambios (ver "Otras configuraciones").
3. Deja los **reviewers vacíos**, salvo que apliquen los configurados (ver "Reviewers").
4. Sube la PR sin pedir confirmación (ver "Cómo subir la PR").

> Nota de seguridad: subir una PR es una acción que publica contenido. En modo `auto` está pre-autorizada por esta configuración; en `ask` requiere tu visto bueno explícito en el chat.

## Rama destino (base) de la PR

La rama destino se determina por el tipo de la rama de trabajo, en línea con la nomenclatura de ramas del repositorio:

- Si la rama es de tipo **`hotfix`** (prefijo `hotfix/`) → la PR apunta a **producción** (`productionBranch`, por defecto `main`).
- **Cualquier otro tipo** (`fix/`, `feat/`, etc.) → la PR apunta a **`baseBranch`** (por defecto `development`).

Al crear la PR, especifica explícitamente la base:

```
gh pr create --base <rama-destino> --head <rama-de-trabajo> ...
```

Donde `<rama-destino>` es `productionBranch` para hotfix o `baseBranch` en cualquier otro caso. Nunca abras una PR contra producción salvo que la rama sea un hotfix; ante la duda, usa `baseBranch` y avisa al usuario.

## Título de la PR

Formato:

```
[<icon> <type>: GH-<n>] - <titulo-del-issue>
```

Infiere `type` desde las **labels del issue** de GitHub usando este mapeo. Si el issue tiene varias labels de tipo, usa la primera fila que coincida (de arriba hacia abajo). Si ninguna coincide o no es claro, pregunta al usuario.

| Label(s) del issue | Type | Icon |
|--------------------|------|------|
| `breaking-change` | `Break` | ❌ |
| `hotfix` (emergencia en producción) | `Hotfix` | 🚨 |
| `security` | `Fix` | 🛠️ |
| `bug` | `Fix` | 🛠️ |
| `enhancement` | `Feat` | ✨ |
| `improvement` | `Improve` | 🚀 |
| `tech-debt` / `refactor` | `Refactor` | 🧹 |
| `documentation` | `Doc` | 📝 |
| `chore` | `Chore` | 🗑️ |
| `build` / `ci` | `Build` | ✅ |
| `test` | `Test` | 🧪 |
| `logs` | `Logs` | 🔇 |

Las labels de prioridad (`P0`..`P3`) y de área (`api`, `services`, `schemas`, `agents`) no determinan el `type`.

Reglas:
- La referencia `GH-<n>` (ej. `GH-12`) **siempre** se incluye en el título; el enlace real con el issue lo hace `Closes #<n>` en la descripción.
- Usa el título del issue tal cual cuando sea claro (sin el prefijo `[<icon> <Tipo>]` del issue), o acórtalo si es muy largo. Mantén la descripción breve por debajo de ~60 caracteres y en el mismo idioma que el título del issue.
- Mantén el título completo por debajo de **72 caracteres** cuando sea posible.
- `Hotfix` se reserva para parches de emergencia; los bug fixes normales usan `Fix`.

Antes de guardar el archivo, **muestra la sugerencia de título por chat**:

```
💡 Título sugerido para la PR:
[<icon> <type>: GH-<n>] - <descripción-breve>
```

Si el usuario desea modificarlo, aplica los cambios antes de continuar.

Ejemplos:
```
[✨ Feat: GH-12] - Registro de métricas de salud por año académico
[🛠️ Fix: GH-13] - Listado de estudiantes devuelve 404 con salón vacío
[📝 Doc: GH-14] - Documentar endpoints de administración de escuela
```

## Descripción de la PR

Plantilla base (embebida; si en el futuro existe `.github/pull_request_template.md`, úsalo como base):

```markdown
## Descripción

Incluye un resumen de los cambios y el problema relacionado (en caso de que hubiera uno). Enumere las dependencias necesarias para este cambio.

Closes #<n>

## Tipo de cambio

Marque con una x dentro de los `[]` los que apliquen

- [ ] ✨ Nueva funcionalidad (cambio no-breaking que agrega funcionalidad)
- [ ] 🛠️ Corrección de errores (cambio no-breaking que arregla un error)
- [ ] ❌ Cambio importante (arreglo o característica que haría que la funcionalidad existente no funcionara como se esperaba)
- [ ] 📝 Actualización de la documentación
- [ ] 🧹 Code refactoring (modificación de la estructura interna del código sin modificar las APIs)
- [ ] ✅ Build configuration change (modificación de los archivos para hacer deploy)
- [ ] 🗑️ Chore (actividades que no modifican la interacción con la app, por ejemplo, modificar la configuración del linter)

## ¿Cómo se ha probado esto?

Prueba manual: ejercita los endpoints afectados (desde Swagger `/docs` o un cliente HTTP) y verifica el resultado. **Adjunta los endpoints/flujos que debe ejercitar quien quiera probar el cambio** (un ítem de checklist por endpoint/flujo, indicando método + ruta, rol con el que se autentica y resultado esperado).

- [ ] **<MÉTODO> <ruta 1>** (rol: `<rol>`) → <resultado esperado: status + contenido de `data`>
- [ ] **<MÉTODO> <ruta 2>** (rol: `<rol>`) → <resultado esperado: status + contenido de `data`>

**Configuración de prueba:**

- Servidor local: `uvicorn app.main:app --reload`
- Documentación interactiva: `http://localhost:8000/docs`
- Pruebas automatizadas: `pytest`

## Lista de Verificación

- [ ] He agregado las nuevas dependencias en la descripción
- [ ] He agregado las nuevas variables de entorno (solo los nombres y rutas) a la descripción
- [x] Mi código sigue las pautas de estilo de este proyecto
- [x] He realizado una auto-revisión de mi código
- [x] He comentado mi código, particularmente en áreas difíciles de entender
- [ ] He realizado los cambios correspondientes a la documentación.
- [x] Mis cambios no generan nuevas advertencias
- [ ] Mis cambios pasan el build y lint del proyecto localmente
- [ ] He agregado pruebas que prueban que mi solución es efectiva o que mi función funciona
- [ ] Las pruebas unitarias nuevas y existentes pasan localmente con mis cambios
```

Pautas de llenado (usa la info del issue de GitHub + los commits):
- **Descripción**: resumen claro de los cambios basado en el issue de GitHub y los commits. Cuando aplique, una lista numerada de cambios concretos (qué se corrigió/eliminó/añadió y por qué). Incluye **siempre** la línea `Closes #<n>` (ej. `Closes #12`) para que GitHub cierre el issue al fusionar la PR. Nota: GitHub solo cierra automáticamente el issue cuando la PR se fusiona en la rama por defecto del repositorio; si la base es `baseBranch` y no es la rama por defecto, el issue se cerrará al llegar el cambio a ella o deberá cerrarse manualmente.
- **Tipo de cambio**: marca con `x` solo el/los tipo(s) que correspondan según las labels del issue y los cambios reales.
- **¿Cómo se ha probado esto?**: por defecto es **prueba manual**. Enumera como checklist los **endpoints/flujos concretos** que debe ejercitar quien pruebe el cambio (método + ruta + rol + resultado esperado); **deriva los endpoints de los cambios reales de la rama** y sustituye los placeholders `<...>`. No dejes los ejemplos.
- **Configuración de prueba**: por defecto **servidor local `uvicorn app.main:app --reload`**, **Swagger en `/docs`** y **`pytest`**. Ajusta solo si el cambio lo requiere (variables de entorno, migraciones previas, etc.).
- **Lista de Verificación**: incluye **todos** los ítems. Vienen **marcados por defecto** los cuatro que este proyecto cumple siempre —*pautas de estilo*, *auto-revisión*, *código comentado* y *sin nuevas advertencias*—; desmárcalos solo si en el caso concreto no se cumplen. Los demás (dependencias, variables de entorno, documentación, build/lint, pruebas) márcalos con honestidad solo si realmente aplican y se cumplieron; si no aplican, déjalos sin marcar (opcionalmente con la nota *(no aplica)*).

## Otras configuraciones

### Labels
- En modo `auto`: asigna las labels que tengan más sentido lógico con la naturaleza de los cambios (ej. cambios solo en docs → label de documentación; corrección de bug → label de bug). Infiere a partir de los archivos editados, las labels del issue de GitHub y los commits.
- En modo `ask`: **propón** esas labels en el chat para que el usuario las apruebe junto con la PR.

### Reviewers
- Los reviewers candidatos del equipo viven en `.claude/pr-config.json`, en la clave `reviewers` (un array que puede contener varios nombres/usuarios de GitHub).
- En modo `ask`: muestra esa lista de candidatos para que el usuario elija.
- En modo `auto`: deja los reviewers **vacíos por defecto**. Solo añade un reviewer si su nombre/usuario coincide con alguno de la lista `reviewers` configurada y tiene sentido para el cambio. Si la lista está vacía o no hay coincidencia, no asignes reviewers.

## Cómo subir la PR (modos `ask` aprobado y `auto`)

Usa la herramienta disponible, priorizando **GitHub CLI**:

1. Si `gh` está disponible, usa:
   ```
   gh pr create --base <rama-destino> --head <rama-de-trabajo> --title "<título>" --body-file "<ruta-del-md>" [--label "<label>" ...] [--reviewer "<reviewer>" ...]
   ```
   El cuerpo de la PR debe ser el archivo markdown generado (`--body-file`), no texto reescrito. La `<rama-destino>` se determina según la sección "Rama destino (base) de la PR".
2. Si `gh` no está disponible pero hay un conector MCP de GitHub configurado, úsalo para crear la PR con el mismo título, cuerpo, labels y reviewers.
3. Si no hay ninguna de las dos, deja el archivo escrito (como en modo `manual`) e informa al usuario que no fue posible subir automáticamente.

Tras subir, devuelve la URL de la PR creada.