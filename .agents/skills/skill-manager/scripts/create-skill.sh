#!/bin/bash

# A script to create and register custom skills.

function show_help {
  echo "Usage: $0 [OPTIONS]"
  echo "Creates a new custom skill for the agent."
  echo ""
  echo "Options:"
  echo "  -n, --name         Name of the skill (e.g., my-new-skill)"
  echo "  -d, --description  Description of the skill (keep it clear and specific)"
  echo "  -h, --help         Show this help message"
  exit 0
}

SKILL_NAME=""
SKILL_DESC=""

while [[ "$#" -gt 0 ]]; do
  case $1 in
    -n|--name) SKILL_NAME="$2"; shift 2 ;;
    -d|--description) SKILL_DESC="$2"; shift 2 ;;
    -h|--help) show_help ;;
    *) echo "Unknown parameter passed: $1"; exit 1 ;;
  esac
done

if [[ -z "$SKILL_NAME" || -z "$SKILL_DESC" ]]; then
  echo "Error: Both --name and --description are required."
  echo "Use --help for usage."
  exit 1
fi

SKILL_DIR=".agents/skills/$SKILL_NAME"
INDEX_FILE=".agents/skills/SKILL.md"

if [ -d "$SKILL_DIR" ]; then
  echo "Error: Skill already exists at $SKILL_DIR"
  exit 1
fi

echo "Creating skill directory structure at $SKILL_DIR..."
mkdir -p "$SKILL_DIR"
mkdir -p "$SKILL_DIR/scripts"
mkdir -p "$SKILL_DIR/examples"
mkdir -p "$SKILL_DIR/resources"

echo "Generating SKILL.md for $SKILL_NAME..."

cat <<EOF > "$SKILL_DIR/SKILL.md"
---
name: $SKILL_NAME
description: $SKILL_DESC
---

# $SKILL_NAME

Detailed instructions for the agent go here.

## When to use this skill

- Use this when...
- This is helpful for...

## How to use it

Step-by-step guidance, conventions, and patterns the agent should follow.

## Best Practices

- **Keep skills focused:** Each skill should do one thing well. Instead of a "do everything" skill, create separate skills for distinct tasks.
- **Write clear descriptions:** The description is how the agent decides whether to use your skill. Make it specific about what the skill does and when it's useful.
- **Use scripts as black boxes:** If your skill includes scripts, encourage the agent to run them with \`--help\` first rather than reading the entire source code. This keeps the agent's context focused on the task.
- **Include decision trees:** For complex skills, add a section that helps the agent choose the right approach based on the situation.

## Decision Tree Example

Identify the right approach:
- If situation A, take approach X
- If situation B, take approach Y

EOF

echo "Registering skill in $INDEX_FILE..."

# Check if index file exists and is populated, create it if not
if [ ! -s "$INDEX_FILE" ]; then
    echo "# Skill Catalogue" > "$INDEX_FILE"
    echo "" >> "$INDEX_FILE"
    echo "This file catalogues all custom skills registered in the project." >> "$INDEX_FILE"
    echo "" >> "$INDEX_FILE"
    echo "## Available Skills" >> "$INDEX_FILE"
    echo "" >> "$INDEX_FILE"
fi

# Append to index file if it doesn't already contain the skill
if ! grep -q "\*\*${SKILL_NAME}\*\*" "$INDEX_FILE"; then
    echo "- **$SKILL_NAME**: $SKILL_DESC (dir: \`.agents/skills/$SKILL_NAME/\`)" >> "$INDEX_FILE"
    echo "Skill '$SKILL_NAME' registered in $INDEX_FILE."
else
    echo "Skill '$SKILL_NAME' is already registered in $INDEX_FILE."
fi

echo "Success! Skill structure implemented successfully."
