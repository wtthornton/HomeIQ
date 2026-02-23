# 🧪 Testing Quick Start Guide

## TL;DR - Run Tests Now

### Windows (PowerShell)
```powershell
cd services\health-dashboard
.\run-tests.ps1
```

### Linux/Mac
```bash
cd domains/core-platform/health-dashboard
./run-tests.sh
```

---

## Prerequisites Checklist

Before running tests, ensure:

- ✅ **Backend Services Running**
  ```bash
  docker-compose up -d
  ```

- ✅ **Dashboard Running**
  ```bash
  cd domains/core-platform/health-dashboard
  npm run dev
  ```
  Should be accessible at http://localhost:3000

- ✅ **Dependencies Installed**
  ```bash
  cd domains/core-platform/health-dashboard
  npm install
  npx playwright install
  ```

---

## Quick Commands

### Run Full Dashboard Tests (Recommended)
```bash
# Windows
.\run-tests.ps1 -Suite full

# Linux/Mac
./run-tests.sh --suite full
```

### Run in Interactive UI Mode
```bash
# Windows
.\run-tests.ps1 -UI

# Linux/Mac
./run-tests.sh --ui
```

### Run with Visible Browser (Watch Tests Run)
```bash
# Windows
.\run-tests.ps1 -Headed

# Linux/Mac
./run-tests.sh --headed
```

### Quick Smoke Test
```bash
# Windows
.\run-tests.ps1 -Suite quick

# Linux/Mac
./run-tests.sh --suite quick
```

### View Test Report
```bash
# Windows
.\run-tests.ps1 -Report

# Linux/Mac
./run-tests.sh --report
```

---

## Test Suites

### 1. **Full Dashboard Test** (`dashboard-full.spec.ts`)
**Comprehensive test suite covering everything**

Tests include:
- ✅ Real data verification (no mocks)
- ✅ All 7 tabs (Overview, Services, Dependencies, etc.)
- ✅ API endpoint validation
- ✅ Interactive features (dark mode, refresh, time range)
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Navigation and routing
- ✅ Performance checks

**Run this test:**
```bash
npm run test:e2e dashboard-full
```

### 2. **Services Tab Tests**
Phase-specific tests for Services tab functionality:

- `services-tab-phase1.spec.ts` - Service cards
- `services-tab-phase2.spec.ts` - Service details modal
- `services-tab-phase3.spec.ts` - Dependencies

**Run these tests:**
```bash
npm run test:e2e services-tab
```

---

## Real Data Verification

### ⚠️ IMPORTANT: Tests Use REAL Data (No Mocks)

The tests verify that your dashboard is:
1. ✅ Fetching real data from backend APIs
2. ✅ Displaying current timestamps (< 5 minutes old)
3. ✅ Not using mock/placeholder data
4. ✅ Connected to live services

**What gets verified:**
- `/api/health` - Recent health data with fresh timestamps
- `/api/statistics` - Real statistics from InfluxDB
- `/api/data-sources` - Actual data source configurations
- UI displays real values (not "Loading...", "N/A", "Mock")

**Example test output:**
```
✅ Real health data verified: healthy
✅ Health API timestamp is recent: 2025-10-12T14:32:15
✅ Statistics API returns real data
✅ Found 6 service cards with real data
✅ UI shows real timestamp: 2:32:15 PM
```

---

## Troubleshooting

### ❌ Error: "Navigation timeout exceeded"

**Problem:** Backend not running or dashboard not accessible

**Solution:**
```bash
# 1. Check if dashboard is running
curl http://localhost:3000

# 2. Start backend services
docker-compose up -d

# 3. Start dashboard
cd domains/core-platform/health-dashboard
npm run dev

# 4. Verify health endpoint
curl http://localhost:3000/api/health
```

---

### ❌ Error: "Playwright not found"

**Solution:**
```bash
cd domains/core-platform/health-dashboard
npm install @playwright/test
npx playwright install
```

---

### ❌ Tests fail with "expect(received).toBeTruthy() - received: undefined"

**Problem:** API endpoints not returning expected data

**Solution:**
1. Check backend logs: `docker-compose logs`
2. Verify API manually:
   ```bash
   curl http://localhost:3000/api/health | jq
   curl http://localhost:3000/api/statistics?time_range=1h | jq
   curl http://localhost:3000/api/data-sources | jq
   ```
3. Check backend configuration in `.env` files
4. Ensure InfluxDB and other services are healthy

---

### ❌ Error: "Timeout waiting for element"

**Problem:** Dashboard loading slowly

**Solution:**
1. Increase test timeout (already set to 30s)
2. Check network performance
3. Check browser console for errors:
   ```bash
   # Run in headed mode to see console
   ./run-tests.sh --headed
   ```

---

## Advanced Usage

### Run Specific Test
```bash
npx playwright test --grep "should verify NO mock data"
```

### Run on Specific Browser
```bash
# Chromium
npm run test:e2e:chromium

# Firefox
npx playwright test --project=firefox

# WebKit (Safari)
npx playwright test --project=webkit

# All browsers
npx playwright test --project=all
```

### Debug Failed Test
```bash
# Windows
.\run-tests.ps1 -Debug

# Linux/Mac
./run-tests.sh --debug

# Or manually
npx playwright test --debug
```

### View Test Trace
```bash
npx playwright show-trace test-results/*/trace.zip
```

---

## Test Output

### Successful Run
```
✅ All tests passed!
   Duration: 42.5s

📊 To view detailed report:
   ./run-tests.sh --report
```

### Failed Run
```
❌ Some tests failed
   Duration: 38.2s

📊 To view test results:
   ./run-tests.sh --report

🐛 To debug:
   ./run-tests.sh --debug
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: |
          cd domains/core-platform/health-dashboard
          npm ci
      
      - name: Install Playwright
        run: |
          cd domains/core-platform/health-dashboard
          npx playwright install --with-deps
      
      - name: Start backend services
        run: docker-compose up -d
      
      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:3000/api/health; do sleep 2; done'
      
      - name: Run E2E tests
        run: |
          cd domains/core-platform/health-dashboard
          npm run test:e2e
      
      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: domains/core-platform/health-dashboard/playwright-report/
```

---

## Test Configuration

Located in `playwright.config.ts`:

```typescript
{
  baseURL: 'http://localhost:3000',
  timeout: 30000,                    // 30s per test
  retries: process.env.CI ? 2 : 0,   // Retry on CI
  workers: process.env.CI ? 1 : undefined,
  
  use: {
    actionTimeout: 10000,            // 10s for actions
    navigationTimeout: 30000,        // 30s for navigation
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  }
}
```

---

## Best Practices

1. **Run tests regularly** - After any dashboard changes
2. **Check reports** - View HTML report after failures
3. **Use UI mode** - For test development and debugging
4. **Monitor performance** - Tests should complete in ~30-60s
5. **Keep services running** - Leave backend running during development
6. **Update snapshots** - When UI changes are intentional

---

## Quick Reference

| Command | Windows | Linux/Mac |
|---------|---------|-----------|
| Run all tests | `.\run-tests.ps1` | `./run-tests.sh` |
| UI mode | `.\run-tests.ps1 -UI` | `./run-tests.sh --ui` |
| Debug | `.\run-tests.ps1 -Debug` | `./run-tests.sh --debug` |
| Report | `.\run-tests.ps1 -Report` | `./run-tests.sh --report` |
| Quick test | `.\run-tests.ps1 -Suite quick` | `./run-tests.sh --suite quick` |
| Services only | `.\run-tests.ps1 -Suite services` | `./run-tests.sh --suite services` |

---

## Getting Help

1. **View test results:** `./run-tests.sh --report`
2. **Check test logs:** Look in `test-results/` directory
3. **Debug interactively:** `./run-tests.sh --ui`
4. **Check backend:** `docker-compose logs`
5. **Read E2E README:** `tests/e2e/README.md`

---

## Resources

- 📖 [E2E Test README](tests/e2e/README.md) - Comprehensive testing guide
- 🎭 [Playwright Docs](https://playwright.dev/) - Official documentation
- 🐛 [Debugging Tests](https://playwright.dev/docs/debug) - Debugging guide
- 🎯 [Best Practices](https://playwright.dev/docs/best-practices) - Testing best practices

---

**Ready to test?**

```bash
# Windows
.\run-tests.ps1

# Linux/Mac
./run-tests.sh
```

Happy testing! 🎉

