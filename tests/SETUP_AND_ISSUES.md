# Test Suite Setup and Known Issues

## Setup Instructions

### 1. Install Dependencies

**AI Automation UI** needs Playwright installed:
```bash
cd services/ai-automation-ui
npm install
```

This will install `@playwright/test` which was added to `package.json`.

**Health Dashboard** already has Playwright installed.

### 2. Install Playwright Browsers

```bash
# From project root
npx playwright install

# Or install specific browsers
npx playwright install chromium
```

### 3. Verify Services Are Running

Before running tests, ensure the services are running:

```bash
# Health Dashboard (Port 3000)
cd services/health-dashboard
npm run dev

# AI Automation UI (Port 3001)  
cd services/ai-automation-ui
npm run dev
```

Or use Docker Compose to start all services.

## Running Tests

### Health Dashboard Tests

```bash
cd services/health-dashboard
npm run test:e2e                 # Run all tests
npm run test:e2e:smoke           # Run smoke tests only
npm run test:e2e:ui              # Run with UI mode
npm run test:e2e:debug           # Run in debug mode
```

### AI Automation UI Tests

```bash
cd services/ai-automation-ui
npm run test:e2e                 # Run all tests
npm run test:e2e:smoke           # Run smoke tests only
npm run test:e2e:ui              # Run with UI mode
npm run test:e2e:debug           # Run in debug mode
```

### All Tests (Root)

```bash
# From project root
npx playwright test              # Run all tests
npx playwright test --grep @smoke # Run smoke tests
npx playwright test --ui         # Run with UI mode
```

## Known Issues and Fixes

### 1. Playwright Not Installed in AI Automation UI

**Issue**: `@playwright/test` needs to be installed in `services/ai-automation-ui`

**Fix**: Run `npm install` in `services/ai-automation-ui`

### 2. WebServer Configuration

**Issue**: The `webServer` configuration in Playwright config files uses `cwd` option which might not work correctly in all environments.

**Status**: Fixed - Updated to use `cwd` option instead of `cd &&` commands for better cross-platform compatibility.

**Alternative**: If services are already running, Playwright will reuse them (`reuseExistingServer: !process.env.CI`).

### 3. Test Selectors May Need Adjustment

**Issue**: Tests use flexible selectors (multiple options) to handle different UI implementations. Some selectors might need adjustment based on actual DOM structure.

**Status**: Tests are written with fallback selectors. If tests fail, check the actual DOM structure and update selectors as needed.

**Example**: Tests look for `[data-testid="service-card"]` OR `[class*="ServiceCard"]` to handle both test IDs and class-based selectors.

### 4. API Mocking

**Issue**: Tests mock API responses. If actual API structure differs, mocks may need updating.

**Status**: Mock data is in `tests/e2e/{service}/fixtures/api-mocks.ts`. Update these files if API responses don't match.

### 5. Authentication

**Issue**: Tests use a default API key. If your environment requires different authentication, update `tests/shared/helpers/auth-helpers.ts`.

**Status**: Default API key is set in `auth-helpers.ts`. Modify `DEFAULT_API_KEY` constant if needed.

### 6. Chart Rendering Tests

**Issue**: Chart tests wait for canvas/SVG elements. Some charts might render differently.

**Status**: `waitForChartRender` helper has error handling for different chart implementations.

### 7. Responsive/Mobile Tests

**Issue**: Mobile viewport tests are configured but may need adjustment for actual mobile UI.

**Status**: Tests use standard mobile viewport sizes. Adjust if UI has specific breakpoints.

## Test Structure Verification

All test files have been created:

- ✅ 15 Health Dashboard tab tests
- ✅ 1 Health Dashboard dashboard test
- ✅ 4 Health Dashboard component tests
- ✅ 3 Health Dashboard interaction tests
- ✅ 1 Health Dashboard accessibility test
- ✅ 9 AI Automation UI page tests
- ✅ 4 AI Automation UI component tests
- ✅ 2 AI Automation UI workflow tests
- ✅ Shared utilities and helpers
- ✅ Test fixtures and mock data
- ✅ Configuration files
- ✅ Documentation

## Troubleshooting

### Tests Fail to Start

1. **Check Playwright installation**: `npx playwright --version`
2. **Check services are running**: `curl http://localhost:3000/health`
3. **Check dependencies**: `npm list @playwright/test` in both service directories

### Tests Timeout

1. **Increase timeouts** in `playwright.config.ts` if needed
2. **Check service startup time** - webServer timeout is 120 seconds
3. **Check network connectivity** to services

### Import Errors

1. **Verify file paths** - imports use relative paths from test files
2. **Check TypeScript compilation** - run `tsc --noEmit` in test directories
3. **Verify shared helpers exist** - check `tests/shared/helpers/` directory

### Selector Errors

1. **Inspect DOM** in browser DevTools
2. **Update selectors** in test files if UI structure differs
3. **Use Playwright Inspector** (`npm run test:e2e:debug`) to debug selectors

## Next Steps

1. **Install dependencies**: Run `npm install` in `services/ai-automation-ui`
2. **Install browsers**: Run `npx playwright install`
3. **Start services**: Start Health Dashboard and AI Automation UI
4. **Run smoke tests**: `npm run test:e2e:smoke` to verify setup
5. **Run full suite**: `npm run test:e2e` once smoke tests pass
6. **Adjust selectors**: Update selectors based on actual DOM structure
7. **Update mocks**: Adjust API mocks if API responses differ

## Success Indicators

- ✅ All test files compile without TypeScript errors
- ✅ Smoke tests pass
- ✅ Services start correctly
- ✅ Tests can connect to services
- ✅ Selectors find elements
- ✅ API mocks match actual API responses
