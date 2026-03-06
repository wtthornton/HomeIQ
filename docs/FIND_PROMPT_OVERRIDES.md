# Auto-Bugfix Prompt Overrides

Rules in this file are automatically injected into the bug-finding prompt.
Add rules based on patterns from previous runs to reduce false positives.

## Format

Each rule is a bullet point. Be specific and actionable.

## Rules

- Do NOT report missing `__init__.py` files as bugs.
- Do NOT report `datetime.utcnow()` as a bug — these have already been audited and fixed where needed.
- Do NOT report missing error handling in test/example files.
- Do NOT report unused imports in `__init__.py` files — these are intentional re-exports.
