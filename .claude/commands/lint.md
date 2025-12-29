# Lint Command

Run code linting with Ruff (10-100x faster than alternatives).

## Usage

```
@lint <file-path>
```

Or with natural language:
```
Lint src/api/auth.py
Check code style in src/utils/helpers.py
Run linting on the authentication module
```

## What It Does

1. **Runs Ruff**: Executes Ruff linting (Python's fastest linter)
2. **Finds Issues**: Identifies code style and quality issues
3. **Provides Fixes**: Suggests specific fixes for each issue
4. **Scores Code**: Calculates linting score (0-10)

## Examples

```
@lint src/api/auth.py
@lint src/utils/helpers.py
@lint src/ --fix
```

## Features

- **Fast**: Ruff is 10-100x faster than alternatives
- **Comprehensive**: Checks style, quality, and best practices
- **Auto-Fix**: Can automatically fix many issues (with --fix flag)
- **Scoring**: Provides linting score for quality gates

## Output

- Linting report with issues
- Line numbers and error codes
- Fix recommendations
- Linting score

## Integration

- **Cursor**: Use `@reviewer *lint <file>` (Cursor Skill)
- **Claude Desktop**: Use `@lint <file>` (this command)
- **CLI**: Use `tapps-agents reviewer lint <file>`

