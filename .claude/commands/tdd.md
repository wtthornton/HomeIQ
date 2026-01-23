# TDD Command (Simple Mode)

TDD workflow: Red-Green-Refactor with coverage ≥80%.

## Usage

```
@tdd "<description>"
@tdd <file>
```

Or: `@simple-mode *tdd "<description>"` or `*tdd {file}`

## What It Does

1. Define interfaces/contracts
2. Write failing tests (RED) via `@tester *generate-tests`
3. Implement minimal code (GREEN) via `@implementer *implement`
4. Refactor (IMPROVE) via `@implementer *refactor`
5. `@tester *test` and ensure coverage ≥80%

## Integration

- **Cursor**: `@simple-mode *tdd "<desc>"` or `*tdd {file}`
