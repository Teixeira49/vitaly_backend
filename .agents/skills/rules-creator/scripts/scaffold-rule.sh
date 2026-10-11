#!/bin/bash
set -e

function show_help {
  echo "Usage: $0 [OPTIONS]"
  echo "Scaffolds a new standardized AI agent rule file."
  echo ""
  echo "Options:"
  echo "  -n, --name          Name of the rule (e.g. 'db-isolation' or 'api-endpoints') (Required)"
  echo "  -d, --description   Brief summary of when the rule should be triggered (Required for .mdc)"
  echo "  -g, --globs         Glob pattern for matching files (e.g. 'app/api/**/*.py')"
  echo "  -t, --type          Rule format: 'mdc' (default) or 'md'"
  echo "  -o, --output-dir    Destination directory (default: '.cursor/rules' for mdc, '.agents/rules' for md)"
  echo "  --always-apply      Flag to set alwaysApply: true in frontmatter (mdc only)"
  echo "  -h, --help          Show this help message"
  exit 0
}

RULE_NAME=""
RULE_DESC=""
RULE_GLOBS=""
RULE_TYPE="mdc"
OUTPUT_DIR=""
ALWAYS_APPLY="false"

while [[ "$#" -gt 0 ]]; do
  case $1 in
    -n|--name) RULE_NAME="$2"; shift 2 ;;
    -d|--description) RULE_DESC="$2"; shift 2 ;;
    -g|--globs) RULE_GLOBS="$2"; shift 2 ;;
    -t|--type) RULE_TYPE="$2"; shift 2 ;;
    -o|--output-dir) OUTPUT_DIR="$2"; shift 2 ;;
    --always-apply) ALWAYS_APPLY="true"; shift 1 ;;
    -h|--help) show_help ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
done

if [[ -z "$RULE_NAME" ]]; then
  echo "Error: --name is required."
  echo "Use --help for usage details."
  exit 1
fi

if [[ "$RULE_TYPE" == "mdc" && -z "$RULE_DESC" ]]; then
  RULE_DESC="Enforces standards and constraints for $RULE_NAME"
fi

if [[ -z "$OUTPUT_DIR" ]]; then
  if [[ "$RULE_TYPE" == "mdc" ]]; then
    OUTPUT_DIR=".cursor/rules"
  else
    OUTPUT_DIR=".agents/rules"
  fi
fi

mkdir -p "$OUTPUT_DIR"
FILE_PATH="$OUTPUT_DIR/$RULE_NAME.$RULE_TYPE"

if [[ -f "$FILE_PATH" ]]; then
  echo "Error: Rule file already exists at $FILE_PATH"
  exit 1
fi

if [[ "$RULE_TYPE" == "mdc" ]]; then
  cat <<EOF > "$FILE_PATH"
---
description: "$RULE_DESC"
globs:
  - "${RULE_GLOBS:-**/*}"
alwaysApply: $ALWAYS_APPLY
---

# $RULE_NAME Rules

## 1. Scope & Context
- **Target Area:** ${RULE_GLOBS:-"General codebase"}
- **Objective:** Describe the objective of this rule.

## 2. Hard Constraints (Non-Negotiable)
- ⛔ **NEVER** ...
- 🔒 **MANDATORY:** ...

## 3. Prescriptive Directives
- **Direct Action 1:** ...
- **Direct Action 2:** ...

## 4. Concrete Examples (Few-Shot)

### ❌ Anti-Pattern (DON'T)
\`\`\`python
# Example of what to avoid
\`\`\`

### ✅ Standard Pattern (DO)
\`\`\`python
# Example of the approved pattern
\`\`\`

## 5. Verification & Self-Correction
- **Checklist:**
  - [ ] Constraint 1 satisfied
- **Verification Command:** \`pytest\` or relevant linter/test command
EOF
else
  cat <<EOF > "$FILE_PATH"
# $RULE_NAME Guidelines

## Scope
$RULE_DESC

## Hard Constraints
- ⛔ **NEVER** ...
- 🔒 **MANDATORY:** ...

## Coding Conventions
- ...

## Examples (Do vs Don't)
### ❌ Anti-Pattern
\`\`\`python
# Bad
\`\`\`

### ✅ Standard
\`\`\`python
# Good
\`\`\`

## Verification
- Verification steps...
EOF
fi

echo "Created rule successfully at: $FILE_PATH"
