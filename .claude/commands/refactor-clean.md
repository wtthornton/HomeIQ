# Refactor Clean Command (Simple Mode)

Mechanical cleanup: unused imports, dead code, duplication. Use *refactor for larger design changes.

## Usage

```
@refactor-clean <file>
```

Or: `@simple-mode *refactor-clean {file}`

## What It Does

1. `@reviewer *duplication` and/or Ruff for unused-import/dead-code
2. `@implementer *refactor` for mechanical cleanup
3. Report changes

## Integration

- **Cursor**: `@simple-mode *refactor-clean {file}`
