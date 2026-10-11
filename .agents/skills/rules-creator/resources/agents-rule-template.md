# [Domain Name] Guidelines & Constraints

## Scope
Defines operating boundaries and implementation standards for [Domain/Module].

## Boundaries & Constraints
- **Multi-Tenancy / Security:** [Specific boundary, e.g., never trust user input for tenant scoping]
- **Prohibited Patterns:** [E.g., no raw queries, no circular imports, no untyped return values]

## Coding Conventions
- **Layering:** Route -> Service -> Repository / ORM.
- **Responses:** Standard envelope wrapper required.
- **Documentation:** Google-style docstrings with Args, Returns, and Raises.

## Examples
### ❌ Prohibited
```python
# Unsafe or non-standard implementation
```

### ✅ Approved
```python
# Standard compliant implementation
```

## Verification
- Validation commands or automated test suites to run before finalizing changes.
