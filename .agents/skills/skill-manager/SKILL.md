---
name: skill-manager
description: Manage, create, and catalogue custom skills for this AI agent. Enforces structure, creates the folder template, and registers new skills in the main index. Use this skill when the user asks to "create a new skill".
---

# Skill Manager

This skill allows the agent to easily create, catalogue, and manage custom skills for the current project.

## When to use this skill

- Use this whenever the user requests to **create a new custom skill**, **add a new skill**, or **teach you a new capability by making a skill**.
- Use this to correctly scaffold the folder structure (`scripts/`, `examples/`, `resources/`) for new skills.
- Use this to automatically register skills centrally in `.agents/skills/SKILL.md`.

## How to use it

1. Ensure you understand what the user wants the new skill to do. Give it an appropriate `kebab-case` name and a short description.
2. Run the provided helper script as a black box:
   ```bash
   ./.agents/skills/skill-manager/scripts/create-skill.sh --name "my-skill" --description "Helps with a specific task. Use when you need to do X or Y."
   ```
   *(You can also run it with `--help` if you need to double-check parameters)*
3. After scaffolding the structure, fill out the newly created `SKILL.md` for the new skill (located at `.agents/skills/my-skill/SKILL.md`) with detailed instructions using code modification tools (e.g. `multi_replace_file_content`).
4. If the skill requires complex actions, consider adding helper scripts to `.agents/skills/my-skill/scripts/` and reference them in the new `SKILL.md`.

## Enforcing Best Practices

When generating the detailed instructions inside the newly created skill's `SKILL.md`, you **MUST** ensure the following best practices:

- **Keep skills focused:** Each skill should do one thing well. Instead of a "do everything" skill, create separate skills for distinct tasks.
- **Write clear descriptions:** The description is how the agent decides whether to use your skill. Make it specific about what the skill does and when it's useful.
- **Use scripts as black boxes:** If your skill includes scripts, instruct the agent to run them with `--help` first rather than reading the entire source code. This keeps the agent's context focused on the task.
- **Include decision trees:** For complex skills, add a section that helps the agent choose the right approach based on the situation.

## Decision Tree

**Do I need to create a skill?**
- **Yes:** Is it a focused, single-purpose skill?
   - **Yes:** Run `scripts/create-skill.sh` and populate the resulting `SKILL.md`.
   - **No:** Break the task down and create multiple, focused skills instead.
- **No:** If you are just modifying an existing skill, use standard file editing tools on that skill's `SKILL.md`.
