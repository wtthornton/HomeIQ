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

## Negative paths are not optional

**Every mock of a fallible dependency needs a failing counterpart.** A success-only
mock does not test integration — it tests that your happy path compiles.

When you write a test that mocks something which can fail, add:

- **The failure case.** The dependency returns an error, raises, or times out.
- **An assertion on what the caller reports.** Not just "it didn't crash" — assert
  the response marks itself `degraded`, or errors. A tool that swallows a
  dependency failure and still reports plain success is the bug.

When a function accepts caller-supplied structured input (a JSON array, a config
dict), add the **off-contract shape**: strings where objects were expected, nulls,
mixed arrays. The invariant is that every item is honoured or the call raises —
never silently shorter.

A suite that drives real tool handlers opts into the machine check rather than
writing that assertion by hand: `pytestmark = pytest.mark.usefixtures("envelope_guard")`.
The fixture records every envelope the test builds and fails at teardown if one
claims plain success over a nested failure. Where a payload legitimately embeds
failure-shaped records, name those keys with `@pytest.mark.envelope_allow(...)`
and say why in a comment above the mark — an unexplained `allow` is a silenced
test, not a documented exception.

## Coverage

- New public functions need a corresponding test
- Aim for 80%+ coverage on new code
- Use `--cov-report=term-missing` to identify gaps
