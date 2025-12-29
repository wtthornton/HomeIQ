# Code Review Command

Review code files with objective quality metrics, security analysis, and actionable feedback.

## Usage

```
@review <file-path>
```

Or with natural language:
```
Review the code in src/api/auth.py
Check the quality of src/utils/helpers.py
```

## What It Does

1. **Calculates Objective Scores** (5 metrics):
   - Complexity Score (0-10)
   - Security Score (0-10)
   - Maintainability Score (0-10)
   - Test Coverage Score (0-100%)
   - Performance Score (0-10)

2. **Runs Quality Tools**:
   - Ruff linting (Python)
   - mypy type checking
   - Bandit security scanning
   - Code duplication detection
   - Dependency vulnerability audit

3. **Provides Actionable Feedback**:
   - Specific line numbers for issues
   - Code examples for fixes
   - Security recommendations
   - Best practice suggestions

## Examples

```
@review src/api/auth.py
@review src/utils/helpers.py
@review tests/test_auth.py
```

## Output Format

- Quality scores with pass/fail status
- Detailed issue list with line numbers
- Security vulnerabilities (if any)
- Actionable recommendations
- Code examples for fixes

## Quality Gates

- Overall score must be ≥ 70
- Security score must be ≥ 7.0
- Complexity should be ≤ 8.0

## Integration

This command works with:
- **Cursor**: Use `@reviewer *review <file>` (Cursor Skill)
- **Claude Desktop**: Use `@review <file>` (this command)
- **CLI**: Use `tapps-agents reviewer review <file>`

