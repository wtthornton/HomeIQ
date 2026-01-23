# Security Review Command (Simple Mode)

Structured security check: reviewer + ops + OWASP-style checklist.

## Usage

```
@security-review
@security-review <path>
```

Or: `@simple-mode *security-review [path]`

## What It Does

1. `@reviewer *review` (security score, bandit)
2. `@ops *audit-security`
3. Apply OWASP-style checklist; summarize and give remediation hints

## Integration

- **Cursor**: `@simple-mode *security-review [path]` or `@security-review`
