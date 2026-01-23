# Security Review (Simple Mode)

## Overview

Structured security check: @simple-mode *security-review [path]. Reviewer + ops + OWASP-style checklist.

## Steps

1. If the user gave a path, use it; otherwise use project root or main source dir.
2. Run: @simple-mode *security-review [path]
3. Execute: @reviewer *review (security, bandit) → @ops *audit-security; apply OWASP-style checklist. Summarize and give remediation hints.
