# Skill Catalogue

This file catalogues all custom skills registered in the project.

## Available Skills

- **skill-manager**: Manage, create, and catalogue custom skills for this AI agent. Enforces structure, creates the folder template, and registers new skills in the main index. Use this skill when the user asks to "create a new skill". (dir: `.agents/skills/skill-manager/`)
- **fastapi-templates**: Create production-ready FastAPI projects with async patterns, dependency injection, and comprehensive error handling. (dir: `.agents/skills/fastapi-templates/`)
- **standard-api-responses**: Standardized API response patterns for FastAPI using a unified envelope (success, message, data, errors, meta) with Pydantic and global error handling. (dir: `.agents/skills/standard-api-responses/`)
- **rbac-manager**: Role-Based Access Control (RBAC) patterns for FastAPI. Implements role checks, dependency injection for authorization, and data isolation strategies. (dir: `.agents/skills/rbac-manager/`)
- **supabase-integration**: Complete Supabase setup including PostgreSQL schema, RLS policies, vector search with pgvector, and connection pooling for FastAPI projects. (dir: `.agents/skills/supabase-integration/`)
- **rules-creator**: Design, write, structure, and standardize operational rules for AI agents following modern industry standards (.mdc, AGENTS.md, role constraints, and few-shot examples). Use when creating or refining rules for AI agents. (dir: `.agents/skills/rules-creator/`)
