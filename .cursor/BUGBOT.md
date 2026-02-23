# TappsMCP Quality Standards for BugBot

This project uses TappsMCP (Code Quality MCP Server) for automated quality
analysis. The following standards are enforced during PR review.

## Code Quality Standards

All Python files must meet TappsMCP scoring thresholds:
- Overall score: >= 70 (development), >= 80 (staging), >= 90 (production)
- No individual category score below 50

### Scoring Categories

| Category | What BugBot Should Check |
|----------|-------------------------|
| Correctness | Logic errors, unchecked return values, unreachable code |
| Security | Hardcoded secrets, unsafe deserialization, injection vulns |
| Maintainability | Functions > 50 lines, cyclomatic complexity > 10 |
| Performance | Nested loops on large data, sync I/O in async context |
| Documentation | Missing docstrings on public API, outdated params |
| Testing | Functions without test coverage, real external service calls |
| Style | Inconsistent naming, bare `except`, missing type annotations |

## Security Requirements

Flag any of the following as blocking issues:
- Hardcoded passwords, API keys, tokens, or secrets
- Use of `eval()` or `exec()` with non-literal arguments
- `pickle.loads()` on data from external sources
- Raw SQL string concatenation (use parameterized queries)
- File path operations without validation against allowed base dir
- `subprocess` calls with `shell=True` and interpolated user input

## Python Style Rules

Flag the following as non-blocking warnings:
- Public functions and methods without type annotations
- Public classes and functions without docstrings
- Bare `except:` clauses (must specify exception type)
- Functions with cyclomatic complexity > 10
- Functions longer than 50 lines (excluding docstrings/blanks)
- Mutable default arguments in function signatures

## Testing Requirements

Flag the following as non-blocking warnings:
- New public functions without a corresponding test in `tests/`
- Tests that make real HTTP requests without mocking
- Tests that read from or write to production configuration files
- Tests that depend on environment variables without explicit fixtures

## Directory Hierarchy

This `BUGBOT.md` applies to all files in `.cursor/` and subdirectories.
Place a subdirectory `BUGBOT.md` to override these rules for specific
sub-packages with different thresholds.
