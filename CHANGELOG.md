# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-04-11

### Added
- Integrated **Supabase Authentication** with custom Role-Based Access Control (RBAC).
- Initial set of administrative API endpoints:
    - `Catalogs`: For managing system-wide constants.
    - `Schools`: Basic school information management.
    - `Academic Years`: Handling school cycles and transitions.
    - `System Administration`: Platform-level management and monitoring.
    - `School Administration`: Tools for individual school administrators, including classroom and student management.
- **Parent/Representative features**:
    - Implementation of automatic student linking via `identity_number`.
    - Dedicated `Parent` service and endpoints.
- **Core Improvements**:
    - Custom **OpenAPI** configuration for branded documentation (Swagger/ReDoc).
    - Robust project structure following service/repository patterns.
    - Branded root landing page and health check utilities.

### Fixed
- Improved `.gitignore` configuration to exclude specific environment and local project files (`supabase/`, `test_users/`, `.cursorrules`, etc.).

### Changed
- Standardized API response format using internal `APIResponse` schema.
- Refactored authentication dependencies for more granular role verification (`admin_sistema`, `admin_escuela`, `representante`).
