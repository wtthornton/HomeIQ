---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/*_test.py"
---
# Test Quality Rules (TappsMCP)

Run `tapps_quick_check(file_path)` after editing test files.

Use `tapps_lookup_docs(library, topic)` for test framework APIs and best practices.

## Testing Standards

- Use pytest fixtures for setup/teardown, not setUp/tearDown methods
- Mock external services and I/O — never make real HTTP requests in tests
- One logical assertion per test when practical
- Use descriptive test names: `test_<what>_<condition>_<expected>`
- Use `tmp_path` fixture for temporary files, not manual cleanup
- Reset module-level caches in autouse fixtures (see conftest.py)
- Tests that depend on environment variables must use explicit fixtures

## Coverage

- New public functions need a corresponding test
- Aim for 80%+ coverage on new code
- Use `--cov-report=term-missing` to identify gaps
