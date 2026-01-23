# Test Coverage Command (Simple Mode)

Coverage-driven test generation. Find gaps and generate tests for uncovered paths.

## Usage

```
@test-coverage <file> [--target 80]
```

Or: `@simple-mode *test-coverage <file> --target 80`

## What It Does

1. Use coverage.xml/coverage.json to find low/uncovered modules
2. `@tester *test` for those paths to improve coverage
3. Report coverage change

## Integration

- **Cursor**: `@simple-mode *test-coverage <file> --target 80`
