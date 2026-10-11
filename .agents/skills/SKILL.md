# Skill Catalogue

This file catalogues all custom skills registered in the project.

## Available Skills

- **skill-manager**: Manage, create, and catalogue custom skills for this AI agent. Enforces structure, creates the folder template, and registers new skills in the main index. Use this skill when the user asks to "create a new skill". (dir: `.agents/skills/skill-manager/`)
- **fastapi-templates**: Create production-ready FastAPI projects with async patterns, dependency injection, and comprehensive error handling. (dir: `.agents/skills/fastapi-templates/`)
- **standard-api-responses**: Standardized API response patterns for FastAPI using a unified envelope (success, message, data, errors, meta) with Pydantic and global error handling. (dir: `.agents/skills/standard-api-responses/`)
- **rbac-manager**: Role-Based Access Control (RBAC) patterns for FastAPI. Implements role checks, dependency injection for authorization, and data isolation strategies. (dir: `.agents/skills/rbac-manager/`)
- **supabase-integration**: Complete Supabase setup including PostgreSQL schema, RLS policies, vector search with pgvector, and connection pooling for FastAPI projects. (dir: `.agents/skills/supabase-integration/`)
- **rules-creator**: Design, write, structure, and standardize operational rules for AI agents following modern industry standards (.mdc, AGENTS.md, role constraints, and few-shot examples). Use when creating or refining rules for AI agents. (dir: `.agents/skills/rules-creator/`)
- **find-skills**: Discover and install agent skills from repositories and registries. (dir: `.agents/skills/find-skills/`)
- **skill-creator**: Create new skills, modify and improve existing skills, and benchmark performance. (dir: `.agents/skills/skill-creator/`)
- **async-python-patterns**: Asynchronous Python patterns with asyncio, concurrency, timeouts, and non-blocking I/O. (dir: `.agents/skills/async-python-patterns/`)
- **clean-architecture**: Clean Architecture principles, layers, decoupling, and dependency rules. (dir: `.agents/skills/clean-architecture/`)
- **confiao-contracts-parity**: Reference parity guide between TypeScript/Zod and Python/Pydantic contracts. (dir: `.agents/skills/confiao-contracts-parity/`)
- **confiao-rbac**: Role and permission catalogue and gate patterns. (dir: `.agents/skills/confiao-rbac/`)
- **confiao-tenant-isolation**: Multi-tenant isolation doctrine and layer protections. (dir: `.agents/skills/confiao-tenant-isolation/`)
- **fastapi**: Official FastAPI best practices and patterns. (dir: `.agents/skills/fastapi/`)
- **fastapi-code-review**: Code review checklist for routing, dependencies, response models, and async handlers. (dir: `.agents/skills/fastapi-code-review/`)
- **pydantic**: Pydantic v2 validation, serializers, and performance optimization. (dir: `.agents/skills/pydantic/`)
- **sqlalchemy-code-review**: SQLAlchemy code review for sessions, N+1 detection, and 2.0 select syntax. (dir: `.agents/skills/sqlalchemy-code-review/`)
- **sqlalchemy-postgres**: PostgreSQL-specific SQLAlchemy practices, connection pools, and indices. (dir: `.agents/skills/sqlalchemy-postgres/`)
- **branch-pr**: GitHub PR creation with issue linkage and semantic labels. (dir: `.agents/skills/branch-pr/`)
- **chained-pr**: Split oversized PRs (>400 lines) into chained reviewable slices. (dir: `.agents/skills/chained-pr/`)
- **issue-creation**: Standardized GitHub issue creation with templates and triage status. (dir: `.agents/skills/issue-creation/`)
- **work-unit-commits**: Plan reviewable atomic work units and commit organization. (dir: `.agents/skills/work-unit-commits/`)
