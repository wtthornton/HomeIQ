# E2E Command (Simple Mode)

Generate and run E2E tests. Playwright MCP recommended for execution.

## Usage

```
@e2e
@e2e <path>
```

Or: `@simple-mode *e2e` or `@tester *generate-e2e-tests`

## What It Does

1. `@tester *generate-e2e-tests` for the project or path
2. If Playwright MCP is available, use it to run and validate
3. Report results

## Integration

- **Cursor**: `@simple-mode *e2e` or `@tester *generate-e2e-tests`
