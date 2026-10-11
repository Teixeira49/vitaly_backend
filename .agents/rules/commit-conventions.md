---
description: Formato obligatorio de mensajes de commit (Conventional Commits + gitmoji, estilo extensión vivaxy de VSCode). Aplica a TODOS los commits del repositorio.
---

# Formato de Commits

Al crear cualquier commit, usa **Conventional Commits con gitmoji**, replicando exactamente el formato de la extensión de VSCode "Conventional Commits" (vivaxy) con su configuración por defecto (`gitmoji: true`, `emojiFormat: "code"`).

## Estructura de la cabecera

```
<emoji> type(scope): subject
```

- El **gitmoji va primero**, como carácter Unicode (`✨`). GitHub y la mayoría de clientes Git lo renderizan directamente.
- Luego el `type` en minúsculas, seguido del `scope` opcional entre paréntesis.
- Dos puntos y un espacio, luego el `subject`.
- El `subject` va en imperativo y presente ("add", "fix", no "added"/"adds"), sin punto final, en minúscula inicial.
- Un espacio entre el emoji y el `type`.

Ejemplos:

```
✨ feat(auth): add C2P payment flow
🐛 fix(api): handle 500 error on scraping endpoint
📝 docs: update CI/CD pipeline setup guide
♻️ refactor(state): migrate global store to Zustand
```

## Mapeo obligatorio type → gitmoji

Usa SIEMPRE este emoji por tipo (no elijas otros):

| type       | emoji | descripción                                                              |
|------------|-------|--------------------------------------------------------------------------|
| `feat`     | ✨    | Una nueva funcionalidad                                                  |
| `fix`      | 🐛    | Corrección de un bug                                                     |
| `docs`     | 📝    | Cambios solo en documentación                                            |
| `style`    | 💄    | Cambios que no afectan el significado del código (formato, espacios)     |
| `refactor` | ♻️    | Cambio de código que no corrige bug ni añade funcionalidad               |
| `perf`     | ⚡    | Cambio de código que mejora el rendimiento                               |
| `test`     | ✅    | Añadir o corregir tests                                                  |
| `build`    | 👷    | Cambios en el sistema de build o dependencias externas (npm, gulp, etc.) |
| `ci`       | 💚    | Cambios en archivos y scripts de configuración de CI                     |
| `chore`    | 🔧    | Otros cambios que no modifican src ni archivos de test                   |
| `revert`   | ⏪    | Revierte un commit anterior                                              |

## Reglas adicionales

- **Breaking changes**: añade `!` después del type/scope y, si aplica, un footer `BREAKING CHANGE: <descripción>`.
  ```
  ✨ feat(api)!: change auth response schema

  BREAKING CHANGE: the `token` field is now nested under `data`
  ```
- **Body** (opcional): déjalo separado de la cabecera por una línea en blanco.
- **Footer** (opcional): referencias a issues (`Closes #123`), breaking changes, etc.
- Mantén la cabecera por debajo de ~72 caracteres cuando sea posible.
- Un commit = un cambio lógico coherente. No mezcles features y fixes no relacionados.
- Escribe el `subject` en inglés salvo que el repositorio use otra convención.

## Antes de hacer commit

- Verifica con `git status` y `git diff --staged` que solo estás incluyendo lo que pertenece a este commit.
- Elige el `type` por el cambio predominante; si dudas entre `feat` y `fix`, recuerda: `feat` = nueva capacidad, `fix` = corregir comportamiento existente.