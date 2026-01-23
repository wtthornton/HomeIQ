# Build Fix Command (Simple Mode)

Fix build/compile errors (Python, npm, tsc, cargo). Distinct from *fix (runtime) and *fix-tests.

## Usage

```
@build-fix "<build-output or description>"
```

Or: `@simple-mode *build-fix "<description>"`

## What It Does

1. Parse build/compile errors
2. `@debugger *debug` with error and file/line
3. `@implementer *refactor` to apply fix
4. Re-run build to verify

## Integration

- **Cursor**: `@simple-mode *build-fix "<description or build output>"`
