---
paths:
  - "**/*.py"
---
# Python Quality Rules (TappsMCP)

Run `tapps_quick_check(file_path)` after editing Python files.

Use `tapps_research(question)` before using unfamiliar library APIs.

Call `tapps_validate_changed()` before declaring work complete.

## Quality Scoring (7 Categories, 0-100 each)

1. **Complexity** - Cyclomatic complexity (radon cc / AST fallback)
2. **Security** - Bandit + pattern heuristics
3. **Maintainability** - Maintainability index (radon mi / AST fallback)
4. **Test Coverage** - Heuristic from matching test file existence
5. **Performance** - Nested loops, large functions, deep nesting
6. **Structure** - Project layout (pyproject.toml, tests/, README, .git)
7. **DevEx** - Developer experience (docs, AGENTS.md, tooling config)

Any category scoring below 70 should be addressed.
