---
paths:
  - "**/*.py"
---
# Python Quality Rules (TappsMCP)

Run tools in this order when editing Python:

1. **`tapps_lookup_docs(library, topic)` before the first edit** that uses an external
   library API. Skipping triggers `lookup_docs_underused` in checklist `usage_gaps`.
2. **`tapps_quick_check(file_path)` after each edit**
3. **`tapps_validate_changed(file_paths="file1.py,file2.py")`** with explicit paths before declaring work complete. Never call without `file_paths`. Default is quick mode; only use `quick=false` as a last resort.

Do not guess API signatures from training data.

## Quality Scoring (7 Categories, 0-100 each)

1. **Complexity** - Cyclomatic complexity (radon cc / AST fallback)
2. **Security** - Bandit + pattern heuristics
3. **Maintainability** - Maintainability index (radon mi / AST fallback)
4. **Test Coverage** - Heuristic from matching test file existence
5. **Performance** - Halstead metrics, perflint anti-patterns, nested loops, large functions, deep nesting
6. **Structure** - Project layout (pyproject.toml, tests/, README, .git)
7. **DevEx** - Developer experience (docs, AGENTS.md, tooling config)

Any category scoring below 70 should be addressed.
