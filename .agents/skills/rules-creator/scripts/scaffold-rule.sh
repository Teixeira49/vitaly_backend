#!/bin/bash
# Scaffolds a Vitaly agent rule: <output-dir>/<name>.md (canonical file, YAML
# frontmatter + 5-section structure) plus <name>.mdc as a relative symlink to it,
# so Cursor (.mdc) and Claude/other agents (.md) read the same source.
set -euo pipefail

function show_help {
  cat <<HELP
Usage: $0 --name <rule-name> [OPTIONS]
Scaffolds a new standardized AI agent rule in .agents/rules/.

Creates:
  <output-dir>/<name>.md    canonical rule (frontmatter + 5 sections)
  <output-dir>/<name>.mdc   relative symlink -> <name>.md (Cursor discovery)

Options:
  -n, --name          Rule name in kebab-case, e.g. 'db-isolation' (required)
  -d, --description   When the rule applies (frontmatter 'description')
  -g, --globs         Comma-separated globs, e.g. 'app/api/**/*.py,app/services/**/*.py'
  -o, --output-dir    Destination directory (default: '.agents/rules')
      --always-apply  Set 'alwaysApply: true' (default: false)
      --no-mdc-link   Do not create the .mdc symlink
      --dry-run       Print what would be created without writing anything
  -h, --help          Show this help message

Note: .claude/rules and .cursor/rules are symlinks to .agents/rules, so the
default output directory is visible to every agent automatically.
HELP
  exit 0
}

RULE_NAME=""
RULE_DESC=""
RULE_GLOBS=""
OUTPUT_DIR=".agents/rules"
ALWAYS_APPLY="false"
CREATE_LINK="true"
DRY_RUN="false"

while [[ "$#" -gt 0 ]]; do
  case $1 in
    -n|--name) RULE_NAME="${2:-}"; shift 2 ;;
    -d|--description) RULE_DESC="${2:-}"; shift 2 ;;
    -g|--globs) RULE_GLOBS="${2:-}"; shift 2 ;;
    -o|--output-dir) OUTPUT_DIR="${2:-}"; shift 2 ;;
    --always-apply) ALWAYS_APPLY="true"; shift 1 ;;
    --no-mdc-link) CREATE_LINK="false"; shift 1 ;;
    --dry-run) DRY_RUN="true"; shift 1 ;;
    -h|--help) show_help ;;
    *) echo "Unknown parameter passed: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$RULE_NAME" ]]; then
  echo "Error: --name is required. Use --help for usage details." >&2
  exit 1
fi

if [[ ! "$RULE_NAME" =~ ^[a-z0-9]+([_-][a-z0-9]+)*$ ]]; then
  echo "Error: --name must be kebab-case (lowercase letters, digits, '-' or '_')." >&2
  exit 1
fi

if [[ -z "$RULE_DESC" ]]; then
  RULE_DESC="Estándares y restricciones para $RULE_NAME"
fi

MD_FILE="$RULE_NAME.md"
MDC_FILE="$RULE_NAME.mdc"
MD_PATH="$OUTPUT_DIR/$MD_FILE"
MDC_PATH="$OUTPUT_DIR/$MDC_FILE"

if [[ -e "$MD_PATH" || -L "$MD_PATH" ]]; then
  echo "Error: Rule file already exists at $MD_PATH" >&2
  exit 1
fi
if [[ "$CREATE_LINK" == "true" && ( -e "$MDC_PATH" || -L "$MDC_PATH" ) ]]; then
  echo "Error: $MDC_PATH already exists" >&2
  exit 1
fi

# Frontmatter: globs block only when globs were provided.
GLOBS_BLOCK=""
TARGET_AREA="Código general del repositorio"
if [[ -n "$RULE_GLOBS" ]]; then
  GLOBS_BLOCK="globs:"
  TARGET_AREA=""
  IFS=',' read -r -a GLOB_LIST <<< "$RULE_GLOBS"
  for glob in "${GLOB_LIST[@]}"; do
    glob="$(echo "$glob" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [[ -z "$glob" ]] && continue
    GLOBS_BLOCK+=$'\n'"  - \"$glob\""
    TARGET_AREA+="${TARGET_AREA:+, }\`$glob\`"
  done
  GLOBS_BLOCK+=$'\n'
fi

render_rule() {
  cat <<EOF
---
description: "$RULE_DESC"
${GLOBS_BLOCK}alwaysApply: $ALWAYS_APPLY
---

# $RULE_NAME

## 1. Scope & Context
- **Target Area:** $TARGET_AREA
- **Roles:** [Backend Architect | Security Sentinel | Database Specialist | Medical Domain Guardian]
- **Objetivo:** [1-2 frases: por qué existe la regla]

## 2. Hard Constraints (Reglas Infranqueables)
- ⛔ **NUNCA** ...
- 🔒 **MANDATORIO:** ...

## 3. Directivas Prescriptivas
1. **[Acción 1]:** Usa [patrón A] en lugar de [patrón B] cuando [escenario].
2. **[Acción 2]:** ...

## 4. Ejemplos Contrastados (Few-Shot)

### ❌ Anti-Patrón (DON'T)
\`\`\`python
# Mal: ...
\`\`\`

### ✅ Patrón Estándar (DO)
\`\`\`python
# Bien: ...
\`\`\`

## 5. Verificación & Auto-Corrección
- **Checklist:**
  - [ ] ...
- **Comando de Verificación:** \`pytest tests/...\`
EOF
}

if [[ "$DRY_RUN" == "true" ]]; then
  echo "[dry-run] Would create: $MD_PATH"
  [[ "$CREATE_LINK" == "true" ]] && echo "[dry-run] Would symlink: $MDC_PATH -> $MD_FILE"
  echo "[dry-run] Content:"
  render_rule
  exit 0
fi

mkdir -p "$OUTPUT_DIR"
render_rule > "$MD_PATH"
echo "Created rule: $MD_PATH"

if [[ "$CREATE_LINK" == "true" ]]; then
  # Relative target so the link survives clones and worktrees.
  (cd "$OUTPUT_DIR" && ln -s "$MD_FILE" "$MDC_FILE")
  echo "Linked: $MDC_PATH -> $MD_FILE"
fi
