# Issue #12: [P2] Setup CI/CD Test Pipeline

**Status:** 🟢 Open
**Priority:** 🟢 P2 - Medium
**Effort:** 4-6 hours
**Dependencies:** Issues #1-9

## Description

Configure GitHub Actions workflow to run all tests automatically on every push and pull request with coverage reporting.

## Acceptance Criteria

- [ ] GitHub Actions workflow configured
- [ ] Tests run on every push
- [ ] Tests run on every PR
- [ ] Coverage reports posted to PR
- [ ] Coverage threshold enforcement
- [ ] Parallel test execution
- [ ] Test results artifacts

## Code Template

```yaml
# .github/workflows/test.yml
name: Test Suite
on: [push, pull_request]

jobs:
  test-python:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt

      - name: Run tests with coverage
        run: |
          pytest tests/shared \
            --cov=shared \
            --cov-branch \
            --cov-report=xml \
            --cov-report=term \
            -n auto

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

      - name: Coverage threshold check
        run: |
          coverage report --fail-under=80

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run Vitest
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v4

  test-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Playwright
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npx playwright test

      - name: Upload Playwright Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
```
