# Story 25.3: Test Runner Enhancement and Documentation

## Status
Draft

## Story

**As a** developer and QA engineer,
**I want** the E2E test runner enhanced to support AI Automation tests with comprehensive documentation,
**so that** anyone on the team can run, debug, and understand the AI automation E2E test suite easily.

## Acceptance Criteria

1. **Test Runner Updates:**
   - `run-docker-tests.sh` includes AI automation tests
   - Supports running tests by service (`--service ai-automation`)
   - Supports running specific test suites
   - Exit codes properly indicate test pass/fail
   - Works in both local and CI/CD environments

2. **CI/CD Integration:**
   - GitHub Actions workflow updated (if applicable)
   - Docker deployment validated before tests run
   - Service health checks pass before test execution
   - Test reports uploaded as artifacts
   - Parallel execution configured for speed

3. **Documentation:**
   - README updated with AI automation testing section
   - Quick start guide for running tests
   - Debugging guide with common issues
   - Examples for each test suite
   - Troubleshooting section

4. **Test Reporting:**
   - HTML report includes AI automation tests
   - Screenshots captured on failure
   - Videos captured on failure
   - Traces available for debugging
   - Coverage report generated

5. **Developer Experience:**
   - Clear console output with progress indicators
   - Helpful error messages when tests fail
   - Quick test execution (<5 minutes for all tests)
   - Easy to run individual tests for debugging
   - VS Code launch configurations (optional)

## Tasks / Subtasks

- [ ] **Task 1: Update Test Runner Script** (AC: 1)
  - [ ] Modify `tests/e2e/run-docker-tests.sh`
  - [ ] Add `--service` flag support
  - [ ] Add AI automation test execution
  - [ ] Implement proper exit codes
  - [ ] Test on Linux/macOS/Windows (WSL)

- [ ] **Task 2: CI/CD Integration** (AC: 2)
  - [ ] Update `.github/workflows/` (if exists)
  - [ ] Add service health check validation
  - [ ] Configure parallel test execution
  - [ ] Set up test report artifacts
  - [ ] Add test failure notifications

- [ ] **Task 3: Create Comprehensive Documentation** (AC: 3)
  - [ ] Update `tests/e2e/README.md`
  - [ ] Add AI automation testing section
  - [ ] Create quick start guide
  - [ ] Add debugging guide
  - [ ] Create troubleshooting section with common issues

- [ ] **Task 4: Configure Test Reporting** (AC: 4)
  - [ ] Ensure HTML report includes AI automation tests
  - [ ] Verify screenshot capture on failure
  - [ ] Verify video capture on failure
  - [ ] Enable trace collection
  - [ ] Generate coverage report

- [ ] **Task 5: Developer Experience Enhancements** (AC: 5)
  - [ ] Improve console output formatting
  - [ ] Add progress indicators
  - [ ] Create helpful error messages
  - [ ] Add VS Code launch configurations (optional)
  - [ ] Create quick reference cheat sheet

## Dev Notes

### Project Context

**Existing Test Runner:**
- Location: `tests/e2e/run-docker-tests.sh`
- Current functionality: Runs health dashboard E2E tests
- Configuration: Uses `docker-deployment.config.ts`
- Reporting: Playwright HTML reporter

**AI Automation Tests:**
- Test files: `ai-automation-*.spec.ts`
- Page Objects: `page-objects/*.ts`
- Utilities: `utils/mock-data-generators.ts`, `utils/custom-assertions.ts`
- Expected count: 30+ tests across 6 test suites

**CI/CD Environment:**
- GitHub Actions: `.github/workflows/` (check if exists)
- Docker Compose: Required for service orchestration
- Services: 17 microservices must be running

### Test Runner Enhancement

**Enhanced Script Structure:**
```bash
#!/bin/bash
# tests/e2e/run-docker-tests.sh

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🧪 HA Ingestor E2E Test Suite${NC}"
echo ""

# Parse arguments
SERVICE=""
TEST_SUITE=""
HEADED=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --service) SERVICE="$2"; shift ;;
    --suite) TEST_SUITE="$2"; shift ;;
    --headed) HEADED=true ;;
    --help) show_help; exit 0 ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

# Step 1: Verify Docker services
echo -e "${YELLOW}📦 Checking Docker services...${NC}"
if ! docker-compose ps | grep -q "Up"; then
  echo -e "${RED}❌ Docker services not running. Start with: docker-compose up -d${NC}"
  exit 1
fi

# Step 2: Health checks
echo -e "${YELLOW}🏥 Running health checks...${NC}"
./tests/e2e/check-services.sh

# Step 3: Install dependencies
echo -e "${YELLOW}📥 Installing test dependencies...${NC}"
cd tests/e2e
npm install

# Step 4: Run tests
echo -e "${YELLOW}🧪 Running E2E tests...${NC}"

if [ "$SERVICE" = "ai-automation" ]; then
  # Run only AI automation tests
  npx playwright test tests/e2e/ai-automation-*.spec.ts
elif [ "$SERVICE" = "health-dashboard" ]; then
  # Run only health dashboard tests
  npx playwright test tests/e2e/dashboard-*.spec.ts
elif [ -n "$TEST_SUITE" ]; then
  # Run specific test suite
  npx playwright test "tests/e2e/$TEST_SUITE"
else
  # Run all tests
  npx playwright test
fi

# Step 5: Generate report
echo -e "${GREEN}✅ Tests complete! Opening report...${NC}"
npx playwright show-report

exit 0
```

### CI/CD GitHub Actions Workflow

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  push:
    branches: [master, main]
  pull_request:
    branches: [master, main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    timeout-minutes: 30

    steps:
      - name: Checkout code
        uses: actions/checkout@v3

      - name: Set up Docker Compose
        run: |
          docker-compose -f docker-compose.yml up -d
          sleep 30  # Wait for services to start

      - name: Verify service health
        run: |
          ./scripts/validate-deployment.sh

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '20'

      - name: Install dependencies
        run: |
          cd tests/e2e
          npm ci

      - name: Install Playwright browsers
        run: |
          cd tests/e2e
          npx playwright install --with-deps chromium

      - name: Run Health Dashboard E2E tests
        run: ./tests/e2e/run-docker-tests.sh --service health-dashboard

      - name: Run AI Automation E2E tests
        run: ./tests/e2e/run-docker-tests.sh --service ai-automation

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: tests/e2e/test-results/
          retention-days: 30

      - name: Upload HTML report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: html-report
          path: tests/e2e/playwright-report/
          retention-days: 30

      - name: Comment PR with results
        if: github.event_name == 'pull_request'
        uses: daun/playwright-report-comment@v3
        with:
          report-path: tests/e2e/playwright-report
```

### README Documentation Structure

```markdown
# tests/e2e/README.md

# HA Ingestor E2E Test Suite

## Overview

Comprehensive end-to-end tests for the HA Ingestor system using Playwright.

**Services Covered:**
- Health Dashboard (localhost:3000) - 17 test files
- AI Automation UI (localhost:3001) - 7 test files ✨ NEW

## Quick Start

### Prerequisites
1. Docker and Docker Compose installed
2. Node.js 20+ installed
3. All services running (`docker-compose up -d`)

### Run All Tests
```bash
./tests/e2e/run-docker-tests.sh
```

### Run Specific Service Tests
```bash
# Health Dashboard only
./tests/e2e/run-docker-tests.sh --service health-dashboard

# AI Automation only
./tests/e2e/run-docker-tests.sh --service ai-automation
```

### Run Individual Test File
```bash
cd tests/e2e
npx playwright test ai-automation-approval-workflow.spec.ts
```

### Debug Mode
```bash
cd tests/e2e
npx playwright test --debug --headed
```

## AI Automation Testing (NEW)

### Test Suites

1. **Smoke Tests** (`ai-automation-smoke.spec.ts`)
   - UI loads successfully
   - Navigation works

2. **Approval Workflow** (`ai-automation-approval-workflow.spec.ts`)
   - Browse suggestions
   - Filter and search
   - Approve and deploy
   - Error handling

3. **Rejection Workflow** (`ai-automation-rejection-workflow.spec.ts`)
   - Reject suggestions
   - Provide feedback
   - Verify hiding behavior

4. **Pattern Visualization** (`ai-automation-patterns.spec.ts`)
   - View patterns
   - Filter patterns
   - Chart interactions

5. **Manual Analysis** (`ai-automation-analysis.spec.ts`)
   - Trigger analysis
   - Monitor progress
   - Real-time updates

6. **Device Intelligence** (`ai-automation-device-intelligence.spec.ts`)
   - Utilization metrics
   - Feature suggestions
   - Capability discovery

7. **Settings** (`ai-automation-settings.spec.ts`)
   - Configuration management
   - API key validation
   - Persistence

### Architecture

**Page Object Models:**
- `DashboardPage` - Main suggestion interface
- `PatternsPage` - Pattern visualization
- `DeployedPage` - Deployed automations
- `SettingsPage` - Configuration

**Test Utilities:**
- `mock-data-generators.ts` - Generate test data
- `custom-assertions.ts` - AI-specific assertions
- `api-mocks.ts` - Mock backend endpoints

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { mockSuggestionsEndpoint } from './utils/api-mocks';

test('approve and deploy suggestion', async ({ page }) => {
  const dashboardPage = new DashboardPage(page);
  
  // Mock API
  await mockSuggestionsEndpoint(page);
  
  // Navigate
  await dashboardPage.goto();
  
  // Approve
  await dashboardPage.approveSuggestion(0);
  
  // Deploy
  await dashboardPage.deploySuggestion('sug-1');
  
  // Verify
  await expect(page.getByTestId('toast-success')).toBeVisible();
});
```

## Debugging

### Common Issues

**1. Tests fail with "Service not ready"**
```bash
# Ensure all services are running
docker-compose ps

# Check service health
curl http://localhost:3001
curl http://localhost:8018/health
```

**2. Timeout errors**
```bash
# Increase timeout in playwright.config.ts
timeout: 30000  // 30 seconds
```

**3. Element not found**
- Use Playwright Inspector: `npx playwright test --debug`
- Check data-testid attributes in components
- Verify element visibility with browser DevTools

**4. Flaky tests**
- Use web-first assertions (auto-wait)
- Avoid fixed waits (`setTimeout`)
- Mock external dependencies

### Debug Tools

**Playwright Inspector:**
```bash
npx playwright test --debug
```

**Trace Viewer:**
```bash
npx playwright show-trace test-results/trace.zip
```

**Headed Mode:**
```bash
npx playwright test --headed --slow-mo=1000
```

## Test Reports

### HTML Report
```bash
npx playwright show-report
```

Location: `test-results/html-report/index.html`

### Screenshots
Location: `test-results/*.png` (on failure)

### Videos
Location: `test-results/*.webm` (on failure)

## Best Practices

1. **Use Page Object Models** - Reusable components
2. **Web-First Assertions** - Auto-wait for elements
3. **Mock External APIs** - Deterministic tests
4. **Test Isolation** - Independent tests
5. **Descriptive Names** - Clear test intent
6. **Error Scenarios** - Test failure paths

## Contributing

When adding new tests:
1. Follow Page Object Model pattern
2. Use web-first assertions
3. Add to appropriate test suite
4. Update this README
5. Ensure tests pass locally before PR
```

### VS Code Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "E2E: Debug Current Test",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/tests/e2e/node_modules/.bin/playwright",
      "args": [
        "test",
        "${file}",
        "--debug"
      ],
      "console": "integratedTerminal",
      "internalConsoleOptions": "neverOpen"
    },
    {
      "name": "E2E: Debug AI Automation Tests",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/tests/e2e/node_modules/.bin/playwright",
      "args": [
        "test",
        "ai-automation-*.spec.ts",
        "--debug"
      ],
      "console": "integratedTerminal"
    },
    {
      "name": "E2E: Run All Tests",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/tests/e2e/node_modules/.bin/playwright",
      "args": ["test"],
      "console": "integratedTerminal"
    }
  ]
}
```

### Testing

**Test File Location:** `tests/e2e/run-docker-tests.sh` (modified)

**Test Standards:**
- Shell script follows bash best practices
- Proper error handling (set -e)
- Clear console output with colors
- Works on Linux, macOS, Windows (WSL)

**Validation:**
- Script runs successfully
- Can run all tests
- Can run AI automation tests only
- Can run health dashboard tests only
- Proper exit codes (0 = success, 1 = failure)

**Testing Framework:** Bash shell scripting

**Test Execution:**
```bash
# Test the runner itself
./tests/e2e/run-docker-tests.sh --help
./tests/e2e/run-docker-tests.sh --service ai-automation
./tests/e2e/run-docker-tests.sh --service health-dashboard
```

## Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record

### Agent Model Used
(To be filled by dev agent)

### Debug Log References
(To be filled by dev agent)

### Completion Notes List
(To be filled by dev agent)

### File List
**Expected Files Created/Modified:**

**Modified Files:**
- `tests/e2e/run-docker-tests.sh` (enhanced with AI automation support)
- `tests/e2e/README.md` (comprehensive AI automation section)
- `.github/workflows/e2e-tests.yml` (if applicable - CI/CD integration)

**New Files:**
- `.vscode/launch.json` (optional - VS Code debug configurations)
- `tests/e2e/check-services.sh` (optional - health check script)

**No Changes:**
- Existing test files
- Page Object Models
- Test utilities

## QA Results
(To be filled by QA agent)

